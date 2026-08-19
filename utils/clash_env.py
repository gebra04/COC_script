"""Ambiente Gymnasium do Gêmeo Digital (Camada 4 do digital_twin.md).

Arquitetura B (ver `pesquisa/06`): a base inimiga é escaneada UMA VEZ (via
`utils.base_loader`, leitor externo passivo) e o combate é inteiramente
SIMULADO por `utils.combat_sim`/`utils.attack_simulator` — o ambiente não lê
tropas nem HP ao vivo da memória do jogo durante a batalha (decisão de escopo
do usuário, ver `PROXIMOS_PASSOS.md`, Fase 1.5). O agente decide o plano de
deploy (tropa/feitiço + posição); a cada passo o motor reroda o combate
inteiro (barato, é event-driven) e a recompensa é o ganho de %destruição
previsto — não recebe nenhuma pista de COMO atacar (sem posições/sequência
fixas), só a composição do exército disponível (`utils.army`) e a base a
atacar.
"""

from __future__ import annotations

from typing import Callable

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from utils import building_stats, defense_stats
from utils.army import ArmyComposition, dragon_attack_army
from utils.attack_simulator import DeployStep, simulate as sim_attack
from utils.battle_grid import GRID_SIZE
from utils.building_footprints import _load as _bf_load
from utils.compartment_graph import CompartmentGraph
from utils.game_constants import ATTACK_LENGTH_SEC
from utils.sim_replay import BattleReplay

GRID_CHANNELS = 6  # [0]=HP das defesas, [2]=presença de tropa, [3]=HP dos
                   # recursos, [4]=ameaça por compartimento (sector_dps
                   # normalizado), [5]=1.0 no compartimento externo mais fraco
                   # (ver utils.compartment_graph). [1] reservado (não usado).
GLOBAL_STATE_DIM = 10  # [0]=tempo decorrido/max, [1]=%destruição atual,
                       # [2]=fração de tropa restante, [3]=fração de feitiço
                       # restante. [4..9] reservados (recursos/fase de prep —
                       # ainda não lidos, ver PLANO_SIMULACAO.md Etapa 6).

# Penalidade por tentar deployar um slot sem munição (não gasta tempo de
# simulação — o agente só "perde a vez"). Pequena o bastante pra não dominar
# o sinal de %destruição, grande o bastante pra desencorajar ação aleatória.
INVALID_DEPLOY_PENALTY = 1.0
# Recompensa por feitiço cobrir prédios inimigos vivos — não diz ONDE atacar,
# só que um feitiço jogado em terreno vazio não faz nada (mecânica do jogo,
# não tática): mais prédios sob o raio de efeito = mais dano/efeito real.
SPELL_COVERAGE_WEIGHT = 0.3
SPELL_COVERAGE_CAP = 5
# Teto de passos (válidos ou não) por episódio -- ver docstring de max_steps
# no construtor. Bem acima do uso normal de exército (dezenas de slots
# válidos, no máximo), mas finito: garante que todo episódio termina dentro
# de um rollout PPO de N passos fixos, mesmo com uma política ainda
# aleatória emitindo ações inválidas repetidamente.
MAX_STEPS_PER_EPISODE = 50


def _building_class(did: int) -> str:
    d = _bf_load().get(int(did))
    return d[3] if d else "Unknown"


def _hp_ratio(did: int, lvl: int, hp: float, alive: bool) -> float:
    if not alive:
        return 0.0
    s = defense_stats.stats_at_level(did, lvl + 1) or building_stats.stats_at_level(did, lvl + 1)
    max_hp = s["hitpoints"] if s and s.get("hitpoints") else None
    if not max_hp:
        return 1.0
    return max(0.0, min(1.0, float(hp) / max_hp))


class ClashDigitalTwinEnv(gym.Env):
    """Ambiente Gymnasium: base escaneada (estática) + exército configurável
    (`utils.army.ArmyComposition`) -> plano de deploy -> combate simulado."""

    metadata = {"render_modes": ["human"]}

    def __init__(self, base_entities: list[dict] | None = None,
                 base_provider: Callable[[], list[dict]] | None = None,
                 army: ArmyComposition | None = None,
                 grid_size: int = GRID_SIZE,
                 sim_max_time: float = ATTACK_LENGTH_SEC,
                 max_steps: int = MAX_STEPS_PER_EPISODE):
        """
        `base_entities`: base fixa pra toda a vida do ambiente (um único
            cenário — bom pra depurar/overfit num caso conhecido).
        `base_provider`: callback chamado a cada `reset()` pra obter uma nova
            base (`utils.base_loader.read_enemy_base` pra escoutar ao vivo, ou
            um gerador que sorteia entre capturas salvas — treino variado).
            Se ambos forem None, o episódio começa sem base (grid vazio).
        `army`: composição "cheia" de referência (`utils.army.dragon_attack_army()`
            por padrão); cada `reset()` restaura as contagens a partir dela.
        `max_steps`: teto de chamadas a `step()` por episódio, VÁLIDAS ou não
            (truncated=True ao atingir). Uma ação inválida não avança
            `_episode_time` nem consome munição -- sem este teto, uma política
            ruim (comum na exploração aleatória do início do treino) pode
            ficar emitindo ações inválidas indefinidamente e o episódio nunca
            termina dentro de um rollout PPO de N passos fixos.
        """
        super().__init__()

        self.grid_size = grid_size
        self.base_entities_fixed = base_entities
        self.base_provider = base_provider
        self.army_template = army or dragon_attack_army()
        self.army = self.army_template.clone()
        self.sim_max_time = sim_max_time
        self.max_steps = max_steps

        self._base_entities: list[dict] = base_entities or []
        self._deploy_log: list[DeployStep] = []
        self._episode_time = 0.0
        self._step_count = 0
        self._last_state: dict | None = None
        self.last_destruction = 0.0

        self.observation_space = spaces.Dict(
            {
                "grid": spaces.Box(
                    low=0.0, high=1.0, shape=(GRID_CHANNELS, grid_size, grid_size), dtype=np.float32
                ),
                "global_state": spaces.Box(low=0.0, high=1.0, shape=(GLOBAL_STATE_DIM,), dtype=np.float32),
            }
        )

        # Espaço de ação PAMDP (Camada 4): slot discreto (tropa OU feitiço,
        # ver `ArmyComposition.action_slots()`) + coordenadas contínuas
        # normalizadas. Tamanho derivado da composição real do exército —
        # nada de posição/sequência fixa entra aqui, só QUAIS unidades existem.
        n_slots = max(1, self.army.n_action_slots)
        self.action_space = spaces.Dict(
            {
                "type": spaces.Discrete(n_slots),
                "coords": spaces.Box(low=0.0, high=1.0, shape=(2,), dtype=np.float32),
            }
        )

    # ------------------------------------------------------------ base/army
    def _fetch_base(self) -> list[dict]:
        if self.base_entities_fixed is not None:
            return self.base_entities_fixed
        if self.base_provider is not None:
            return self.base_provider()
        return []

    # ------------------------------------------------------------- gym API
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._base_entities = self._fetch_base()
        self.army = self.army_template.clone()
        self._deploy_log = []
        self._episode_time = 0.0
        self._step_count = 0
        self._last_state = None
        self.last_destruction = 0.0
        return self._get_observation(), {}

    def step(self, action):
        self._step_count += 1
        step_limit_hit = self._step_count >= self.max_steps

        slots = self.army.action_slots()
        slot_idx = int(np.clip(int(action["type"]), 0, max(0, len(slots) - 1)))
        slot = slots.get(slot_idx)
        tx = float(np.clip(action["coords"][0], 0.0, 1.0)) * self.grid_size
        ty = float(np.clip(action["coords"][1], 0.0, 1.0)) * self.grid_size

        if slot is None:
            truncated = step_limit_hit or self.army.is_exhausted()
            return self._get_observation(), -INVALID_DEPLOY_PENALTY, False, truncated, {}
        did, level, is_spell = slot

        if not self.army.try_deploy(did, is_spell):
            truncated = step_limit_hit or self.army.is_exhausted()
            return self._get_observation(), -INVALID_DEPLOY_PENALTY, False, truncated, {"reason": "sem_municao"}

        self._deploy_log.append(DeployStep(did=did, level=level, tx=tx, ty=ty, t=self._episode_time))
        self._episode_time += 1.0  # espaçamento simples entre deploys (placeholder, ver PLANO_SIMULACAO Etapa 6)

        reward, terminated, info = self._step_simulated(did, level, is_spell, tx, ty)
        truncated = (not terminated) and (
            step_limit_hit or self.army.is_exhausted() or self._episode_time >= self.sim_max_time
        )
        return self._get_observation(), reward, terminated, truncated, info

    # ---------------------------------------------------------- simulação
    def _step_simulated(self, did: int, level: int, is_spell: bool, tx: float, ty: float):
        """Reward = Δ da %destruição PREVISTA (recompensa principal) + bônus
        de cobertura de feitiço (mecânica do jogo: feitiço em área vazia não
        faz nada). Reroda o combate inteiro do zero a cada passo — o motor é
        event-driven (não tick), então isso é barato mesmo com dezenas de
        tropas."""
        result = sim_attack(self._base_entities, self._deploy_log, max_time=self.sim_max_time)
        replay = BattleReplay(result.battle_log) if result.battle_log else None
        self._last_state = replay.state_at(min(self._episode_time, result.time_elapsed)) if replay else None

        current_destruction = result.destruction_pct / 100.0
        reward = (current_destruction - self.last_destruction) * 100.0
        self.last_destruction = current_destruction

        if is_spell:
            reward += self._spell_coverage_bonus(did, level, tx, ty)

        terminated = current_destruction >= 1.0
        return reward, terminated, {"battle_result": result}

    def _spell_coverage_bonus(self, did: int, level: int, tx: float, ty: float) -> float:
        from utils.spell_stats import stats_at_level
        s = stats_at_level(did, level)
        radius = (s or {}).get("radius_tiles") or 0.0
        if radius <= 0:
            return 0.0
        alive_map = {}
        if self._last_state:
            alive_map = {e["eid"]: e.get("alive", True) for e in self._last_state["entities"]}
        n = 0
        for e in self._base_entities:
            if e.get("classe") in ("Wall", "Obstacle", "Trap"):
                continue
            if not alive_map.get(e["eid"], True):
                continue
            d = ((e["tx"] - tx) ** 2 + (e["ty"] - ty) ** 2) ** 0.5
            if d <= radius:
                n += 1
        return min(n, SPELL_COVERAGE_CAP) * SPELL_COVERAGE_WEIGHT

    # -------------------------------------------------------------- observação
    def _get_observation(self) -> dict:
        grid = np.zeros((GRID_CHANNELS, self.grid_size, self.grid_size), dtype=np.float32)
        global_state = np.zeros((GLOBAL_STATE_DIM,), dtype=np.float32)

        entities = self._last_state["entities"] if self._last_state else self._base_entities
        for e in entities:
            tx, ty = e.get("tx"), e.get("ty")
            if tx is None or ty is None:
                continue
            gx = int(np.clip(tx, 0, self.grid_size - 1))
            gy = int(np.clip(ty, 0, self.grid_size - 1))
            classe = e.get("classe")
            did = e.get("did")

            if classe == "Troop":
                if e.get("alive", True):
                    grid[2, gx, gy] = min(1.0, grid[2, gx, gy] + 0.2)
                continue
            if classe in ("Wall", "Obstacle", "Trap"):
                continue

            lvl = int(e.get("lvl", 0) or 0)
            alive = e.get("alive", True)
            hp = e.get("hp") or 0
            ratio = _hp_ratio(did, lvl, hp, alive) if (hp or not alive) else 1.0
            bcls = _building_class(did)
            if bcls == "Defense":
                grid[0, gx, gy] = ratio
            elif bcls == "Resource":
                grid[3, gx, gy] = ratio

        if self._base_entities:
            self._fill_tactical_channels(grid, self._base_entities)

        elapsed_frac = min(1.0, self._episode_time / self.sim_max_time) if self.sim_max_time else 0.0
        troop_total = sum(s.count for s in self.army_template.troops) or 1
        troop_left = sum(s.count for s in self.army.troops)
        spell_total = sum(s.count for s in self.army_template.spells) or 1
        spell_left = sum(s.count for s in self.army.spells)
        global_state[0] = elapsed_frac
        global_state[1] = self.last_destruction
        global_state[2] = troop_left / troop_total
        global_state[3] = spell_left / spell_total

        return {"grid": grid, "global_state": global_state}

    def _fill_tactical_channels(self, grid: np.ndarray, entities: list[dict]) -> None:
        """Preenche os canais 4/5 (ameaça por compartimento + lado fraco) a
        partir do `compartment_graph`, sobre o layout ESTÁTICO da base
        (compartimentos não mudam durante o combate). Silencioso se a base
        não tiver compartimentos calculáveis — canais ficam 0."""
        try:
            cg = CompartmentGraph(entities)
        except Exception:
            return
        if not cg.compartments:
            return
        weak_id, _ = cg.weakest_exterior()
        dps_by_comp = {cid: cg.sector_dps(cid) for cid in cg.compartments}
        max_dps = max(dps_by_comp.values(), default=0.0) or 1.0
        for cid, cells in cg.compartments.items():
            dps_norm = dps_by_comp[cid] / max_dps
            is_weak = 1.0 if cid == weak_id else 0.0
            for x, y in cells:
                if x < self.grid_size and y < self.grid_size:
                    grid[4, x, y] = dps_norm
                    grid[5, x, y] = is_weak
