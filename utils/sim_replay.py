"""Reconstroi o estado de uma batalha simulada em QUALQUER instante `t`, a
partir do `BattleLog` gravado pelo `utils.combat_sim.CombatSim`.

Não grava frames: como o motor é event-driven com movimento em linha reta
a velocidade constante entre eventos, e HP variando a taxa constante dentro
de cada trecho, a trajetória inteira é reconstruível por interpolação exata
entre os `TroopKeyframe`/`BuildingKeyframe` do log (ver docstring de
`TroopKeyframe` em `combat_sim.py` pra semântica do campo `phase`).

`state_at(t)` devolve o MESMO formato de dict que a telemetria real do
`mem_reader.py --json` (chaves `classe`/`did`/`eid`/`tx`/`ty`/`hp`/`lvl`) —
de propósito, pra permitir que `utils.sim_render` desenhe simulação e
telemetria real com a mesma função (ver PLANO_SIMULACAO.md, Etapa 1/4).
"""

from __future__ import annotations

from bisect import bisect_right

from utils.combat_sim import BattleLog


def _lerp(a: float, b: float, frac: float) -> float:
    return a + (b - a) * frac


class BattleReplay:
    """Envolve um `BattleLog` e responde `state_at(t)`."""

    def __init__(self, log: BattleLog):
        self.log = log
        self._troop_kfs: dict[int, list] = {}
        for kf in log.troop_keyframes:
            self._troop_kfs.setdefault(kf.troop_id, []).append(kf)
        for kfs in self._troop_kfs.values():
            kfs.sort(key=lambda k: k.t)
        self._building_kfs: dict[int, list] = {}
        for kf in log.building_keyframes:
            self._building_kfs.setdefault(kf.eid, []).append(kf)
        for kfs in self._building_kfs.values():
            kfs.sort(key=lambda k: k.t)
        self._troop_did: dict[int, int] = {}
        for entry in log.deploy_log:
            self._troop_did[entry.troop_id] = entry.did

    # ---------------------------------------------------------- prédios
    def _building_hp_at(self, eid: int, t: float) -> float:
        kfs = self._building_kfs.get(eid)
        if not kfs:
            return 0.0
        ts = [k.t for k in kfs]
        i = bisect_right(ts, t) - 1
        i = max(0, min(i, len(kfs) - 1))
        if i == len(kfs) - 1 or t <= kfs[i].t:
            return kfs[i].hp
        k0, k1 = kfs[i], kfs[i + 1]
        if k1.t <= k0.t:
            return k1.hp
        frac = (t - k0.t) / (k1.t - k0.t)
        return _lerp(k0.hp, k1.hp, frac)

    # ---------------------------------------------------------- tropas
    def _troop_state_at(self, troop_id: int, t: float) -> dict | None:
        kfs = self._troop_kfs.get(troop_id)
        if not kfs or t < kfs[0].t:
            return None
        ts = [k.t for k in kfs]
        i = bisect_right(ts, t) - 1
        i = max(0, min(i, len(kfs) - 1))
        kf = kfs[i]
        if i == len(kfs) - 1 or kf.phase in ("DEAD", "IDLE"):
            x, y, hp = kf.x, kf.y, kf.hp
        else:
            nxt = kfs[i + 1]
            frac = 0.0 if nxt.t <= kf.t else (t - kf.t) / (nxt.t - kf.t)
            hp = _lerp(kf.hp, nxt.hp, frac)
            if kf.phase == "TRAVEL":
                x, y = _lerp(kf.x, nxt.x, frac), _lerp(kf.y, nxt.y, frac)
            else:  # ENGAGE: posicao fixa, so o hp muda
                x, y = kf.x, kf.y
        return {"x": x, "y": y, "hp": hp, "alive": kf.phase != "DEAD" and hp > 0}

    # -------------------------------------------------------------- API
    def state_at(self, t: float) -> dict:
        """Estado da batalha no instante `t`: mesma forma da telemetria real
        (`{"entities": [...], ...}` com dicts classe/did/eid/tx/ty/hp/lvl)."""
        t = max(0.0, min(t, self.log.duration))
        entities = []
        for eid, inst in self.log.buildings.items():
            hp = self._building_hp_at(eid, t)
            entities.append({
                "eid": eid, "did": inst.did,
                "classe": "Wall" if inst.is_wall else "Building",
                "tx": inst.tx, "ty": inst.ty, "hp": hp, "lvl": inst.level,
                "alive": hp > 0,
            })
        n_troops_alive = 0
        for troop_id, did in self._troop_did.items():
            st = self._troop_state_at(troop_id, t)
            if st is None:
                continue
            entities.append({
                "eid": f"troop_{troop_id}", "did": did, "classe": "Troop",
                "tx": st["x"], "ty": st["y"], "hp": st["hp"], "lvl": 0,
                "alive": st["alive"],
            })
            if st["alive"]:
                n_troops_alive += 1

        total = sum(1 for inst in self.log.buildings.values()
                    if not inst.is_wall)
        dead = sum(1 for eid, inst in self.log.buildings.items()
                   if not inst.is_wall and self._building_hp_at(eid, t) <= 0)
        destruction_pct = 100.0 * dead / total if total else 0.0

        return {
            "t": t,
            "entities": entities,
            "destruction_pct": destruction_pct,
            "troops_alive": n_troops_alive,
            "troops_total": len(self._troop_did),
        }

    def duration(self) -> float:
        return self.log.duration
