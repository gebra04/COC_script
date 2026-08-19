"""Referência de stats das tropas do Clash of Clans (consulta programática).

Fonte: `utils/troop_data.json`, gerado do `characters.csv` dos gamefiles.
data-id = 4000000 + índice da tropa (confirmado por RE — ver `pesquisa/02`).
Unidades: alcance/splash em TILES, velocidade de movimento em unidades do jogo,
AttackSpeed em ms. HP/DPS por nível.

Uso (pelo agente de RL / atuador — ex.: montar exército, escolher onde soltar,
saber se a tropa voa e o que ela mira):

    from utils.troop_stats import stats_at_level, is_troop

    s = stats_at_level(4000003, 5)   # Gigante nível 5
    # s['hitpoints'], s['dps'], s['housing_space'], s['is_flying'],
    # s['preferred_target_class'], s['targets_air'], s['range'], ...

Ver também `pesquisa/08_tropas.md`.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).with_name("troop_data.json")
_TROOPS: dict[int, dict] = {}

# nome interno (CSV) → nome PT-BR (o jogo/wiki). Só as tropas principais;
# o resto cai no nome interno.
NAME_PT = {
    "Barbarian": "Bárbaro", "Archer": "Arqueira", "Goblin": "Goblin",
    "Giant": "Gigante", "Wall Breaker": "Quebra-Muro", "Balloon": "Balão",
    "Wizard": "Mago", "Healer": "Curandeira", "Dragon": "Dragão",
    "PEKKA": "P.E.K.K.A", "Gargoyle": "Servo (Minion)",
    "Boar Rider": "Gigante-Porco (Hog Rider)", "Warrior Girl": "Valquíria",
    "Golem": "Golem", "Warlock": "Bruxa (Witch)", "Bowler": "Boliche (Bowler)",
    "BabyDragon": "Bebê Dragão", "Miner": "Mineiro", "Yeti": "Yeti",
    "Giant Skeleton": "Esqueleto Gigante", "Ice Golem": "Golem de Gelo",
    "Electro Dragon": "Dragão Elétrico", "InfernoDragon": "Dragão Infernal",
    "Dragon Rider": "Cavaleiro Dragão", "Headhunter": "Caçadora",
    "Royal_Ghost": "Fantasma Real", "BattleRam": "Aríete de Batalha",
    "Siege Machine Ram": "Destruidor de Muralha", "Siege Machine Flyer": "Aeronave de Batalha",
    "Super Wizard": "Super Mago", "Super Minion": "Super Servo",
    "Super Bowler": "Super Boliche",
}


def _load() -> dict[int, dict]:
    global _TROOPS
    if not _TROOPS:
        raw = json.loads(_DATA_PATH.read_text())
        _TROOPS = {int(k): v for k, v in raw.items()}
    return _TROOPS


def is_troop(data_id: int) -> bool:
    return int(data_id) in _load()


def get_troop(data_id: int) -> dict | None:
    return _load().get(int(data_id))


def name_pt(data_id: int) -> str | None:
    d = get_troop(data_id)
    return NAME_PT.get(d["name"], d["name"]) if d else None


def max_level(data_id: int) -> int | None:
    d = get_troop(data_id)
    return max((l["level"] for l in d["levels"]), default=None) if d else None


def stats_at_level(data_id: int, level: int) -> dict | None:
    """Stats de uma tropa num nível (1-indexed, clamp ao disponível)."""
    d = get_troop(data_id)
    if not d:
        return None
    lvls = d["levels"]
    lv = max(1, min(int(level), max(l["level"] for l in lvls)))
    row = next((l for l in lvls if l["level"] == lv), lvls[-1])
    return {
        "data_id": d["data_id"],
        "name": d["name"],
        "name_pt": NAME_PT.get(d["name"], d["name"]),
        "village": d["village"],
        "level": row["level"],
        "hitpoints": row["hitpoints"],
        "dps": row["dps"],
        "housing_space": d["housing_space"],
        "movement_speed": d["movement_speed"],
        "is_flying": d["is_flying"],
        "range": d["attack_range_tiles"],
        "splash": d["splash_radius_tiles"],
        "attack_speed_ms": d["attack_speed_ms"],
        "targets_air": d["targets_air"],
        "targets_ground": d["targets_ground"],
        "preferred_target_class": d["preferred_target_class"],
        "preferred_target_damage_mod": d.get("preferred_target_damage_mod"),
        "production_building": d["production_building"],
    }


def all_troop_ids(village: str | None = "home") -> list[int]:
    return [i for i, d in _load().items() if village is None or d["village"] == village]


def is_flying(data_id: int) -> bool:
    d = get_troop(data_id)
    return bool(d and d["is_flying"])


def is_ranged(data_id: int) -> bool:
    """True se ataca à distância (range > ~1 tile); False = corpo-a-corpo."""
    d = get_troop(data_id)
    return bool(d and (d["attack_range_tiles"] or 0) > 1.0)
