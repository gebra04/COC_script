"""Rede neural Ator-Crítico Híbrida (H-PPO) da Camada 4 do digital_twin.md.

`ActorCriticHybridNetwork` processa o tensor de observação (`grid` multicanal +
`global_state`) produzido por `utils.clash_env.ClashDigitalTwinEnv` e amostra
uma ação PAMDP híbrida: um componente discreto (tipo de tropa, `Discrete(10)`)
e um componente contínuo (coordenadas normalizadas `(X, Y)` em `[0.0, 1.0]`),
junto com o valor estimado do estado `V(s)` para o crítico.

Este módulo depende de `torch`; a importação é isolada aqui (em vez de em
`utils.clash_env`) para que o ambiente Gymnasium continue utilizável em
contextos que só precisem de observação/telemetria, sem exigir PyTorch.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
from torch.distributions import Categorical, Normal

from utils.clash_env import GLOBAL_STATE_DIM, GRID_CHANNELS


class ActorCriticHybridNetwork(nn.Module):
    """Extrator CNN compartilhado + cabeças discreta/contínua/crítico (PAMDP)."""

    def __init__(self, action_dim: int = 10, grid_size: int = 50):
        super().__init__()

        self.cnn = nn.Sequential(
            nn.Conv2d(GRID_CHANNELS, 16, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.Flatten(),
        )

        conv_out_size = 32 * (grid_size // 2) * (grid_size // 2)

        self.fc_shared = nn.Sequential(
            nn.Linear(conv_out_size + GLOBAL_STATE_DIM, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
        )

        self.discrete_actor = nn.Linear(128, action_dim)
        self.continuous_mean = nn.Linear(128, 2)
        self.continuous_log_std = nn.Parameter(torch.zeros(2))
        self.critic = nn.Linear(128, 1)

    def forward(self, grid_obs: torch.Tensor, global_obs: torch.Tensor):
        cnn_features = self.cnn(grid_obs)
        combined = torch.cat([cnn_features, global_obs], dim=1)
        shared_repr = self.fc_shared(combined)

        discrete_logits = self.discrete_actor(shared_repr)
        mean = torch.sigmoid(self.continuous_mean(shared_repr))
        std = torch.exp(self.continuous_log_std)
        value = self.critic(shared_repr)

        return discrete_logits, mean, std, value

    def sample_action(self, grid_obs: torch.Tensor, global_obs: torch.Tensor):
        discrete_logits, mean, std, value = self.forward(grid_obs, global_obs)

        discrete_dist = Categorical(logits=discrete_logits)
        discrete_action = discrete_dist.sample()

        continuous_dist = Normal(mean, std)
        continuous_action = continuous_dist.sample()
        # `coords` é declarado como spaces.Box(0.0, 1.0) em ClashDigitalTwinEnv;
        # a amostra de uma Normal não-truncada centrada em `mean` (sigmoid, já em
        # [0,1]) pode cair fora desses limites, especialmente com o
        # continuous_log_std ainda não treinado (std inicial = 1.0). Sem este
        # clamp, action_space.contains(action) falha e a coordenada não faz
        # sentido como posição normalizada no mapa.
        continuous_action = torch.clamp(continuous_action, 0.0, 1.0)

        action = {
            "type": int(discrete_action.item()),
            "coords": continuous_action.detach().cpu().numpy()[0],
        }
        return action, value


def observation_to_tensors(obs: dict | list[dict] | tuple[dict, ...]) -> tuple[torch.Tensor, torch.Tensor]:
    """Converte observação(ões) do Gymnasium (numpy) em tensores `torch`.

    Aceita uma única observação (dict — inferência passo a passo, ex.
    `main.py::iniciar_gemeo_digital`, devolve batch dim 1 via `unsqueeze`) OU
    uma lista/tupla de N observações (rollout vetorizado do treino PPO — uma
    por env paralelo, empilhadas com `np.stack` num único forward em batch)."""
    if isinstance(obs, dict):
        grid_tensor = torch.as_tensor(obs["grid"], dtype=torch.float32).unsqueeze(0)
        global_tensor = torch.as_tensor(obs["global_state"], dtype=torch.float32).unsqueeze(0)
        return grid_tensor, global_tensor

    grids = np.stack([o["grid"] for o in obs])
    globals_ = np.stack([o["global_state"] for o in obs])
    grid_tensor = torch.as_tensor(grids, dtype=torch.float32)
    global_tensor = torch.as_tensor(globals_, dtype=torch.float32)
    return grid_tensor, global_tensor
