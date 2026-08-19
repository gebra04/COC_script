"""Footprint (width/height em tiles) de QUALQUER prédio por data-id.

Fonte: `buildings.csv` (mesmo arquivo/indexacao de `gen_defense_data.py`:
data_id = 1000000 + indice da linha) — cobre TODOS os prédios, não só defesas
(defense_data.json filtra BuildingClass=='Defense'). Usado por `battle_grid.py`
pra marcar obstáculos sólidos no grid (qualquer prédio, mesmo não-defensivo,
bloqueia passagem e é alvo em potencial).
"""

from __future__ import annotations

import csv
from pathlib import Path

_SRC = Path(__file__).with_name("buildings.csv")
_FOOTPRINTS: dict[int, tuple[int, int, str, str]] = {}  # did -> (w, h, name, building_class)


def _load() -> dict[int, tuple[int, int, str, str]]:
    global _FOOTPRINTS
    if _FOOTPRINTS:
        return _FOOTPRINTS
    rows = list(csv.reader(open(_SRC)))
    cols = rows[0]
    C = {c: i for i, c in enumerate(cols)}
    bidx = -1
    for row in rows[2:]:
        name = row[C["Name"]].strip()
        if not name:
            continue
        bidx += 1
        did = 1000000 + bidx
        try:
            w = int(row[C["Width"]] or 0)
            h = int(row[C["Height"]] or 0)
        except ValueError:
            w = h = 0
        _FOOTPRINTS[did] = (w, h, name, row[C["BuildingClass"]].strip())
    return _FOOTPRINTS


def footprint(data_id: int) -> tuple[int, int]:
    """(width, height) em tiles. Fallback (3,3) se data-id desconhecido."""
    d = _load().get(int(data_id))
    return (d[0], d[1]) if d else (3, 3)


def is_wall(data_id: int) -> bool:
    d = _load().get(int(data_id))
    return bool(d and d[3] == "Wall")


def building_name(data_id: int) -> str:
    d = _load().get(int(data_id))
    return d[2] if d else f"data{data_id}"
