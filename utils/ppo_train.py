"""Treino PPO do Gêmeo Digital (Passo 5 do planejamento — ver PROXIMOS_PASSOS.md).

PPO em PyTorch puro, sem stable-baselines3 (o `action_space` híbrido Dict
discreto+contínuo não é first-class no SB3 sem um wrapper que anularia a
vantagem de usar a lib pronta). Rollout vetorizado MANUALMENTE: um loop
Python sobre N instâncias de `ClashDigitalTwinEnv` (não `gymnasium.vector.
SyncVectorEnv`, que tem fricção com espaços `Dict`) — cada `step()` de cada
env roda sequencialmente, mas o forward da rede é batched (N observações de
uma vez), que é onde o custo de verdade estaria.

Cada env ataca uma base sorteada do `utils.base_dataset.BaseDataset` a cada
episódio (`base_provider=dataset.sample`), então o "lote" de N ataques
paralelos por iteração ("geração", no vocabulário do usuário) já cobre
variedade de bases, não só variedade de ação.

Padrão de coleta com auto-reset (CleanRL): rollout de T passos fixos por
env; quando um episódio termina (`terminated` OU `truncated`) no meio do
rollout, aquele env é resetado NA HORA e o próximo passo já usa a nova
observação — o valor de bootstrap pro cálculo de vantagem daquele passo
específico usa `V(s_t)` calculado ANTES de agir (já guardado no buffer),
nunca `V(observação pós-reset)`; a máscara `(1-done)` no GAE cuida de não
propagar valor através da fronteira do episódio (ver `compute_gae`).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical, Normal

from utils.army import ArmyComposition, dragon_attack_army
from utils.base_dataset import BaseDataset
from utils.battle_grid import GRID_SIZE
from utils.clash_env import ClashDigitalTwinEnv
from utils.game_constants import ATTACK_LENGTH_SEC
from utils.hppo_network import ActorCriticHybridNetwork, observation_to_tensors


@dataclass
class PPOConfig:
    n_envs: int = 8
    n_steps: int = 48              # T por env por iteracao (>= 2-3x duracao media de episodio)
    n_epochs: int = 4
    minibatches: int = 4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_eps: float = 0.2
    lr: float = 3e-4
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    grid_size: int = GRID_SIZE
    sim_max_time: float = ATTACK_LENGTH_SEC
    max_steps_per_episode: int = 50
    checkpoint_every: int = 10
    checkpoint_dir: Path = field(default_factory=lambda: Path("training_runs"))
    device: str = "cpu"


@dataclass
class RolloutData:
    """Buffer de UMA iteracao de coleta: shape (T, N, ...) pra tudo, exceto
    `battle_logs` (por env, o log da ULTIMA batalha COMPLETA vista no
    rollout -- material bruto do video de populacao, ver `population_viz`)."""
    grid_obs: torch.Tensor          # (T, N, C, H, W)
    global_obs: torch.Tensor        # (T, N, G)
    discrete_actions: torch.Tensor  # (T, N)
    continuous_actions: torch.Tensor  # (T, N, 2)
    logprobs: torch.Tensor          # (T, N)
    values: torch.Tensor            # (T, N)
    rewards: torch.Tensor           # (T, N)
    dones: torch.Tensor             # (T, N)
    next_grid_obs: torch.Tensor     # (N, C, H, W) -- estado apos o ultimo passo
    next_global_obs: torch.Tensor   # (N, G)
    next_done: torch.Tensor         # (N,)
    battle_logs: list               # len N, BattleLog | None
    episode_destructions: list      # %destruicao de cada episodio COMPLETO no rollout
    episode_rewards: list           # recompensa acumulada de cada episodio COMPLETO


def make_envs(cfg: PPOConfig, dataset: BaseDataset, army_template: ArmyComposition) -> list[ClashDigitalTwinEnv]:
    return [
        ClashDigitalTwinEnv(
            base_provider=dataset.sample,
            army=army_template.clone(),
            grid_size=cfg.grid_size,
            sim_max_time=cfg.sim_max_time,
            max_steps=cfg.max_steps_per_episode,
        )
        for _ in range(cfg.n_envs)
    ]


def _sample_batched_action(net: ActorCriticHybridNetwork, grid_t: torch.Tensor, global_t: torch.Tensor):
    """Forward + amostragem pra um BATCH de N observações. Diferente de
    `net.sample_action` (que assume N=1 e usa `.item()`), devolve tensores
    de shape (N,) / (N,2) e os componentes de log-prob JÁ SOMADOS
    (discreta + contínua), como o PPO precisa pra formar a razão de
    importância de uma ação PAMDP híbrida."""
    discrete_logits, mean, std, value = net.forward(grid_t, global_t)
    discrete_dist = Categorical(logits=discrete_logits)
    discrete_action = discrete_dist.sample()

    continuous_dist = Normal(mean, std)
    continuous_action = torch.clamp(continuous_dist.sample(), 0.0, 1.0)

    logprob = discrete_dist.log_prob(discrete_action) + continuous_dist.log_prob(continuous_action).sum(-1)
    return discrete_action, continuous_action, logprob, value.squeeze(-1)


def _evaluate_batched_action(net: ActorCriticHybridNetwork, grid_t: torch.Tensor, global_t: torch.Tensor,
                              discrete_action: torch.Tensor, continuous_action: torch.Tensor):
    """Mesma coisa que `_sample_batched_action`, mas AVALIA ações já
    tomadas (do buffer) sob a política ATUAL, pra recalcular log-prob/
    entropia/valor durante o update PPO (as ações em si não mudam)."""
    discrete_logits, mean, std, value = net.forward(grid_t, global_t)
    discrete_dist = Categorical(logits=discrete_logits)
    continuous_dist = Normal(mean, std)

    logprob = discrete_dist.log_prob(discrete_action) + continuous_dist.log_prob(continuous_action).sum(-1)
    entropy = discrete_dist.entropy() + continuous_dist.entropy().sum(-1)
    return logprob, entropy, value.squeeze(-1)


def collect_rollout(envs: list[ClashDigitalTwinEnv], net: ActorCriticHybridNetwork, cfg: PPOConfig,
                     next_obs: list[dict] | None = None, next_done: np.ndarray | None = None
                     ) -> tuple[RolloutData, list[dict], np.ndarray]:
    """Roda T passos em N envs (auto-reset no meio do rollout). Devolve o
    buffer da iteração + o (next_obs, next_done) pra continuar a próxima
    iteração de onde parou (não precisa resetar tudo a cada chamada)."""
    n = cfg.n_envs
    if next_obs is None:
        next_obs = [env.reset()[0] for env in envs]
    if next_done is None:
        next_done = np.zeros(n, dtype=bool)

    grid_buf, global_buf = [], []
    disc_buf, cont_buf, logprob_buf, value_buf = [], [], [], []
    reward_buf, done_buf = [], []

    battle_logs: list = [None] * n
    episode_destructions: list = []
    episode_rewards: list = []
    ep_reward_acc = np.zeros(n, dtype=np.float64)

    for _t in range(cfg.n_steps):
        grid_t, global_t = observation_to_tensors(next_obs)
        with torch.no_grad():
            discrete_action, continuous_action, logprob, value = _sample_batched_action(net, grid_t, global_t)

        grid_buf.append(grid_t)
        global_buf.append(global_t)
        disc_buf.append(discrete_action)
        cont_buf.append(continuous_action)
        logprob_buf.append(logprob)
        value_buf.append(value)
        done_buf.append(torch.as_tensor(next_done, dtype=torch.float32))

        rewards_t = np.zeros(n, dtype=np.float32)
        dones_t = np.zeros(n, dtype=bool)
        obs_after = [None] * n
        for i, env in enumerate(envs):
            action = {
                "type": int(discrete_action[i].item()),
                "coords": continuous_action[i].detach().cpu().numpy(),
            }
            obs_i, reward_i, terminated_i, truncated_i, info_i = env.step(action)
            done_i = terminated_i or truncated_i
            rewards_t[i] = reward_i
            dones_t[i] = done_i
            ep_reward_acc[i] += reward_i

            battle_result = info_i.get("battle_result")
            if battle_result is not None and battle_result.battle_log is not None:
                battle_logs[i] = battle_result.battle_log

            if done_i:
                episode_destructions.append(env.last_destruction * 100.0)
                episode_rewards.append(float(ep_reward_acc[i]))
                ep_reward_acc[i] = 0.0
                obs_i, _ = env.reset()

            obs_after[i] = obs_i

        reward_buf.append(torch.as_tensor(rewards_t))
        next_obs = obs_after
        next_done = dones_t

    grid_next_t, global_next_t = observation_to_tensors(next_obs)

    data = RolloutData(
        grid_obs=torch.stack(grid_buf),
        global_obs=torch.stack(global_buf),
        discrete_actions=torch.stack(disc_buf),
        continuous_actions=torch.stack(cont_buf),
        logprobs=torch.stack(logprob_buf),
        values=torch.stack(value_buf),
        rewards=torch.stack(reward_buf).float(),
        dones=torch.stack(done_buf),
        next_grid_obs=grid_next_t,
        next_global_obs=global_next_t,
        next_done=torch.as_tensor(next_done, dtype=torch.float32),
        battle_logs=battle_logs,
        episode_destructions=episode_destructions,
        episode_rewards=episode_rewards,
    )
    return data, next_obs, next_done


def compute_gae(net: ActorCriticHybridNetwork, data: RolloutData, cfg: PPOConfig) -> tuple[torch.Tensor, torch.Tensor]:
    """GAE(lambda). `(1-done)` corta a propagação de valor E do acumulador
    lambda nas DUAS fronteiras de episódio -- ver docstring do módulo."""
    with torch.no_grad():
        _, _, _, next_value = net.forward(data.next_grid_obs, data.next_global_obs)
        next_value = next_value.squeeze(-1)

    T, N = data.rewards.shape
    advantages = torch.zeros_like(data.rewards)
    last_gae = torch.zeros(N)
    for t in reversed(range(T)):
        if t == T - 1:
            next_nonterminal = 1.0 - data.next_done
            next_val = next_value
        else:
            next_nonterminal = 1.0 - data.dones[t + 1]
            next_val = data.values[t + 1]
        delta = data.rewards[t] + cfg.gamma * next_val * next_nonterminal - data.values[t]
        last_gae = delta + cfg.gamma * cfg.gae_lambda * next_nonterminal * last_gae
        advantages[t] = last_gae
    returns = advantages + data.values
    return advantages, returns


def ppo_update(net: ActorCriticHybridNetwork, optimizer: optim.Optimizer,
                data: RolloutData, advantages: torch.Tensor, returns: torch.Tensor,
                cfg: PPOConfig) -> dict:
    T, N = data.rewards.shape
    b_grid = data.grid_obs.reshape(T * N, *data.grid_obs.shape[2:])
    b_global = data.global_obs.reshape(T * N, *data.global_obs.shape[2:])
    b_disc = data.discrete_actions.reshape(T * N)
    b_cont = data.continuous_actions.reshape(T * N, 2)
    b_logprobs = data.logprobs.reshape(T * N)
    b_advantages = advantages.reshape(T * N)
    b_returns = returns.reshape(T * N)

    b_advantages = (b_advantages - b_advantages.mean()) / (b_advantages.std() + 1e-8)

    batch_size = T * N
    minibatch_size = max(1, batch_size // cfg.minibatches)
    idxs = np.arange(batch_size)

    last_metrics = {}
    for _epoch in range(cfg.n_epochs):
        np.random.shuffle(idxs)
        for start in range(0, batch_size, minibatch_size):
            mb = idxs[start:start + minibatch_size]
            mb_t = torch.as_tensor(mb, dtype=torch.long)

            new_logprob, entropy, new_value = _evaluate_batched_action(
                net, b_grid[mb_t], b_global[mb_t], b_disc[mb_t], b_cont[mb_t])

            ratio = torch.exp(new_logprob - b_logprobs[mb_t])
            mb_adv = b_advantages[mb_t]
            surr1 = ratio * mb_adv
            surr2 = torch.clamp(ratio, 1.0 - cfg.clip_eps, 1.0 + cfg.clip_eps) * mb_adv
            policy_loss = -torch.min(surr1, surr2).mean()

            value_loss = 0.5 * ((new_value - b_returns[mb_t]) ** 2).mean()
            entropy_loss = entropy.mean()

            loss = policy_loss + cfg.value_coef * value_loss - cfg.entropy_coef * entropy_loss

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), cfg.max_grad_norm)
            optimizer.step()

            last_metrics = {
                "policy_loss": float(policy_loss.item()),
                "value_loss": float(value_loss.item()),
                "entropy": float(entropy_loss.item()),
                "loss": float(loss.item()),
            }
    return last_metrics


def save_checkpoint(net: ActorCriticHybridNetwork, optimizer: optim.Optimizer,
                     iteration: int, run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"checkpoint_{iteration:05d}.pt"
    torch.save({
        "iteration": iteration,
        "model_state_dict": net.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
    }, path)
    return path


def train(cfg: PPOConfig, n_iterations: int, dataset: BaseDataset | None = None,
          army_template: ArmyComposition | None = None,
          on_iteration=None) -> ActorCriticHybridNetwork:
    """Laço de treino completo. `on_iteration(iteration, data, metrics, run_dir)`
    é um callback opcional (ex.: gerar o vídeo de população — ver
    `utils/population_viz.py`) chamado ao fim de cada iteração, com o
    `RolloutData` bruto (que já carrega os `battle_logs` por env) e o
    diretório desta sessão de treino (mesmo onde os checkpoints são salvos)."""
    dataset = dataset or BaseDataset()
    army_template = army_template or dragon_attack_army()

    envs = make_envs(cfg, dataset, army_template)
    action_dim = envs[0].action_space["type"].n
    net = ActorCriticHybridNetwork(action_dim=action_dim, grid_size=cfg.grid_size)
    optimizer = optim.Adam(net.parameters(), lr=cfg.lr)

    run_dir = Path(cfg.checkpoint_dir) / time.strftime("%Y%m%d_%H%M%S")

    next_obs, next_done = None, None
    for it in range(1, n_iterations + 1):
        data, next_obs, next_done = collect_rollout(envs, net, cfg, next_obs, next_done)
        advantages, returns = compute_gae(net, data, cfg)
        metrics = ppo_update(net, optimizer, data, advantages, returns, cfg)

        mean_reward = float(np.mean(data.episode_rewards)) if data.episode_rewards else float("nan")
        mean_dest = float(np.mean(data.episode_destructions)) if data.episode_destructions else float("nan")
        print(f"[ppo] iter {it}/{n_iterations} | episódios completos={len(data.episode_rewards)} "
              f"| reward médio={mean_reward:.2f} | destruição média={mean_dest:.1f}% | {metrics}")

        if on_iteration is not None:
            on_iteration(it, data, metrics, run_dir)

        if it % cfg.checkpoint_every == 0 or it == n_iterations:
            path = save_checkpoint(net, optimizer, it, run_dir)
            print(f"[ppo] checkpoint salvo em {path}")

    return net
