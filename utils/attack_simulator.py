"""Fachada do simulador: `(base_telemetria, plano_de_deploy) -> BattleResult`.

So encanamento por cima do `combat_sim.CombatSim` — nao tem fisica nova aqui.
`DeployStep` usa o mesmo espirito de `attacks/deploy_policy.DeployAction`
(tropa + posicao + tempo de espera), pra nao inventar um formato paralelo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from utils.combat_sim import BattleLog, CombatSim
from utils.game_constants import ATTACK_LENGTH_SEC


@dataclass(frozen=True)
class DeployStep:
    did: int
    level: int
    tx: float
    ty: float
    t: float = 0.0


@dataclass
class BattleResult:
    destruction_pct: float
    time_elapsed: float
    surviving_troops: int
    total_troops: int
    log: list[dict] = field(default_factory=list)
    battle_log: BattleLog | None = None


def simulate(entities: list[dict], deploy_plan: list[DeployStep],
             max_time: float = ATTACK_LENGTH_SEC) -> BattleResult:
    """Roda uma batalha inteira headless (sem ADB/memoria) e devolve o
    resultado. `entities` no mesmo formato do `mem_reader.py --json`
    (`{"classe":, "did":, "eid":, "tx":, "ty":, "hp":, "lvl":}`)."""
    sim = CombatSim(entities)
    for step in sorted(deploy_plan, key=lambda d: d.t):
        sim.deploy(step.did, step.level, step.tx, step.ty, t=step.t)
    sim.run(max_time=max_time)
    alive = sum(1 for tr in sim.troops.values() if tr.alive)
    return BattleResult(
        destruction_pct=sim.destruction_pct(),
        time_elapsed=sim.t,
        surviving_troops=alive,
        total_troops=len(sim.troops),
        log=sim.log,
        battle_log=sim.get_log(),
    )
