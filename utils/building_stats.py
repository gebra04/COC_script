"""Referência de HP de QUALQUER prédio (não só defesa) do Clash of Clans.

Fonte: `utils/building_data.json`, gerado a partir do `buildings.csv` pelo
`utils/gen_building_data.py`. Cobre Town Hall, depósitos, acampamentos,
muralha, prédios de exército, Npc — o que `utils/defense_stats.py` não tem
porque filtra só `BuildingClass == 'Defense'`.

Uso típico (`utils/combat_sim.py`, no lugar do fallback `hp = 100.0`):

    from utils.building_stats import stats_at_level, is_building

    if is_building(ent_data_id):
        s = stats_at_level(ent_data_id, ent_level)
        # s['hitpoints']
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).with_name("building_data.json")
_BUILDINGS: dict[int, dict] = {}


def _load() -> dict[int, dict]:
    global _BUILDINGS
    if not _BUILDINGS:
        raw = json.loads(_DATA_PATH.read_text())
        _BUILDINGS = {int(k): v for k, v in raw.items()}
    return _BUILDINGS


def is_building(data_id: int) -> bool:
    return int(data_id) in _load()


def get_building(data_id: int) -> dict | None:
    return _load().get(int(data_id))


def max_level(data_id: int) -> int | None:
    d = get_building(data_id)
    return max((l["level"] for l in d["levels"]), default=None) if d else None


def stats_at_level(data_id: int, level: int) -> dict | None:
    """HP de um prédio num nível (1-indexed, clamp ao disponível).
    Retorna None se o data-id não está no dataset (ex.: obstáculos/decoração)."""
    d = get_building(data_id)
    if not d:
        return None
    lvls = d["levels"]
    lv = max(1, min(int(level), max(l["level"] for l in lvls)))
    row = next((l for l in lvls if l["level"] == lv), lvls[-1])
    return {
        "data_id": d["data_id"],
        "name": d["name"],
        "building_class": d["building_class"],
        "village": d["village"],
        "level": row["level"],
        "th_required": row["th_required"],
        "hitpoints": row["hitpoints"],
        "width": d["width"],
        "height": d["height"],
    }


def all_building_ids(village: str | None = "home") -> list[int]:
    return [i for i, d in _load().items() if village is None or d["village"] == village]
