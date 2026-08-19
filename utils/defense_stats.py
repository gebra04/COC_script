"""Referência de stats das defesas do Clash of Clans (consulta programática).

Fonte: `utils/defense_data.json`, gerado a partir do `buildings.csv` dos
gamefiles do CoC. data-id = 1000000 + índice do prédio (confirmado por RE em
memória — ver `pesquisa/02`). Unidades: alcance/splash em TILES, velocidade em
ms. HP/DPS por nível.

Uso típico (pelo atuador / agente de RL, cruzando com a telemetria do
`ExternalMemoryReceiver`, que dá `data_id`/`level` de cada entidade):

    from utils.defense_stats import get_defense, stats_at_level, is_defense

    if is_defense(ent_data_id):
        s = stats_at_level(ent_data_id, ent_level)
        # s['dps'], s['hitpoints'], s['range'], s['splash'], s['targets_air'], ...

Ver também `pesquisa/07_defesas.md` para a tabela legível.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).with_name("defense_data.json")
_DEFENSES: dict[int, dict] = {}

# nome interno (CSV) → nome em PT-BR (o que o jogo/wiki mostra)
NAME_PT = {
    "Cannon": "Canhão",
    "Archer Tower": "Torre Arqueira",
    "Wizard Tower": "Torre de Mago",
    "Air Defense": "Defesa Aérea",
    "Mortar": "Morteiro",
    "Tesla Tower": "Tesla Oculta",
    "Bow": "Besta (X-Bow)",
    "Dark Tower": "Torre Infernal",
    "Air Blaster": "Varredor Aéreo (Air Sweeper)",
    "Ancient Artillery": "Artilharia Águia (Eagle)",
    "Bomb Tower": "Torre Bomba",
    "Scattershot": "Scattershot",
}


def _load() -> dict[int, dict]:
    global _DEFENSES
    if not _DEFENSES:
        raw = json.loads(_DATA_PATH.read_text())
        _DEFENSES = {int(k): v for k, v in raw.items()}
    return _DEFENSES


def is_defense(data_id: int) -> bool:
    """True se o data-id é uma defesa (atira em tropas)."""
    return int(data_id) in _load()


def get_defense(data_id: int) -> dict | None:
    """Dict completo da defesa (todos os níveis + campos gerais), ou None."""
    return _load().get(int(data_id))


def name_pt(data_id: int) -> str | None:
    d = get_defense(data_id)
    return NAME_PT.get(d["name"], d["name"]) if d else None


def max_level(data_id: int) -> int | None:
    d = get_defense(data_id)
    return max((l["level"] for l in d["levels"]), default=None) if d else None


def stats_at_level(data_id: int, level: int) -> dict | None:
    """Stats consolidados de uma defesa num nível: HP, DPS, alcance, splash,
    alvos, velocidade, footprint. `level` é 1-indexed (como o jogo mostra);
    é limitado (clamp) ao intervalo disponível. Retorna None se não for defesa."""
    d = get_defense(data_id)
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
        # dps efetivo p/ simulacao: igual a "dps" nas defesas normais; nas de
        # tiro-unico (Eagle Artillery, Multi Mortar — "dps" vem 0/vazio na
        # planilha) e damage_per_shot / intervalo-entre-tiros.
        "effective_dps": row.get("effective_dps") or row["dps"] or 0,
        "damage_per_shot": row.get("damage_per_shot"),
        "ammo_count": row.get("ammo_count"),
        "dps_lv2": row.get("dps_lv2"),
        "dps_lv3": row.get("dps_lv3"),
        "range": d["attack_range_tiles"],
        "min_range": d["min_attack_range_tiles"],
        "splash": d["splash_radius_tiles"],
        "attack_speed_ms": d["attack_speed_ms"],
        "targets_air": d["air_targets"],
        "targets_ground": d["ground_targets"],
        "width": d["width"],
        "height": d["height"],
        "preferred_target": d["preferred_target"],
        "increasing_damage": d.get("increasing_damage", False),
        "lv2_switch_time_ms": d.get("lv2_switch_time_ms"),
        "lv3_switch_time_ms": d.get("lv3_switch_time_ms"),
        "alt_attack_mode": d.get("alt_attack_mode", False),
        "alt_air_targets": d.get("alt_air_targets", False),
        "alt_ground_targets": d.get("alt_ground_targets", False),
        "alt_attack_range_tiles": d.get("alt_attack_range_tiles"),
    }


def all_defense_ids(village: str | None = "home") -> list[int]:
    """IDs de todas as defesas; filtra por 'home'/'builder' se dado."""
    return [i for i, d in _load().items() if village is None or d["village"] == village]


def targets_air(data_id: int) -> bool:
    d = get_defense(data_id)
    return bool(d and d["air_targets"])


def is_splash(data_id: int) -> bool:
    """True se a defesa causa dano em área (splash)."""
    d = get_defense(data_id)
    return bool(d and d["splash_radius_tiles"])
