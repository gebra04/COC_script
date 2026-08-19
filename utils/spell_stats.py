"""Referência de stats dos feitiços do Clash of Clans (consulta programática).

Fonte: `utils/spell_data.json`, gerado do `spells.csv` dos gamefiles reais
(extraídos do diretório de dados do jogo rodando no Waydroid — ver
`pesquisa/03`). data-id vem da coluna **GlobalID** (26000000+), que NÃO é
posicional: Freeze é a 5ª entrada do CSV mas tem id 26000005.

Unidades: raio em TILES, tempos em ms, `damage` é dano por acerto (negativo =
cura, caso do Healing), `damage_boost_percent`/`speed_boost` são percentuais do
motor. HP/efeito por nível em `levels`.

**Confirmado (2026-08-19): AMBOS os campos da Fúria escalam por nível, não só
o dano.** `speed_boost` sobe junto com `damage_boost_percent`
(nível 1: dano+130%/vel+20 → nível 7: dano+190%/vel+32) — `stats_at_level`
já lê os dois pelo `level` pedido (não fixo no nível 1), então
`combat_sim._cast_spell`/`_apply_troop_buff` já aplicam o valor certo por
nível automaticamente, sem precisar de nenhum ajuste adicional.

Uso (pelo agente de RL — escolher qual feitiço soltar e onde):

    from utils.spell_stats import stats_at_level, is_spell, STANDARD_SPELL_IDS

    s = stats_at_level(26000002, 5)   # Fúria (Rage) nível 5
    # s['radius_tiles'], s['damage_boost_percent'], s['speed_boost'],
    # s['boost_time_ms'], s['housing_space'], s['is_dark'], ...

Ver também `utils/troop_stats.py` (mesmo padrão) e `utils/defense_stats.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).with_name("spell_data.json")
_SPELLS: dict[int, dict] = {}

# nome interno (CSV) → nome PT-BR do jogo.
NAME_PT = {
    "Lightning": "Relâmpago", "Healing": "Cura", "Rage": "Fúria",
    "Jump": "Salto", "Freeze": "Congelamento", "Clone": "Clone",
    "Invisibility": "Invisibilidade", "Recall": "Retorno",
    "Poison": "Veneno", "Earthquake": "Terremoto", "Haste": "Aceleração",
    "Skeleton Spell": "Esqueletos", "Bat Spell": "Morcegos",
    "Overgrowth": "Crescimento", "Ice Block": "Bloco de Gelo",
}

# Os 14 feitiços permanentes da vila principal. O `spell_data.json` também traz
# sazonais/evento (Santas Surprise, Birthday2017, Yellow Card, Totem, ...) que
# passam pelo filtro de ProductionBuilding mas não estão sempre disponíveis —
# use este conjunto quando quiser só o que dá pra contar num exército normal.
STANDARD_SPELL_IDS = {
    26000000,  # Lightning / Relâmpago
    26000001,  # Healing / Cura
    26000002,  # Rage / Fúria
    26000003,  # Jump / Salto
    26000005,  # Freeze / Congelamento
    26000009,  # Poison / Veneno          (escuro)
    26000010,  # Earthquake / Terremoto   (escuro)
    26000011,  # Haste / Aceleração       (escuro)
    26000016,  # Clone
    26000017,  # Skeleton / Esqueletos    (escuro)
    26000028,  # Bat / Morcegos           (escuro)
    26000035,  # Invisibility
    26000053,  # Recall / Retorno
    26000070,  # Overgrowth               (escuro)
}


def _load() -> dict[int, dict]:
    global _SPELLS
    if not _SPELLS:
        raw = json.loads(_DATA_PATH.read_text())
        _SPELLS = {int(k): v for k, v in raw.items()}
    return _SPELLS


def is_spell(data_id: int) -> bool:
    return int(data_id) in _load()


def get_spell(data_id: int) -> dict | None:
    return _load().get(int(data_id))


def name_pt(data_id: int) -> str | None:
    d = get_spell(data_id)
    return NAME_PT.get(d["name"], d["name"]) if d else None


def max_level(data_id: int) -> int | None:
    d = get_spell(data_id)
    return max((l["level"] for l in d["levels"]), default=None) if d else None


def stats_at_level(data_id: int, level: int) -> dict | None:
    """Stats de um feitiço num nível (1-indexed, clamp ao disponível)."""
    d = get_spell(data_id)
    if not d:
        return None
    lvls = d["levels"]
    if not lvls:
        return None
    lv = max(1, min(int(level), max(l["level"] for l in lvls)))
    row = next((l for l in lvls if l["level"] == lv), lvls[-1])
    out = {
        "data_id": d["data_id"],
        "name": d["name"],
        "name_pt": NAME_PT.get(d["name"], d["name"]),
        "village": d["village"],
        "housing_space": d["housing_space"],
        "is_dark": d["is_dark"],
        "production_building": d["production_building"],
        "deploy_time_ms": d["deploy_time_ms"],
        "hit_time_ms": d["hit_time_ms"],
        "time_between_hits_ms": d["time_between_hits_ms"],
        "min_radius_tiles": d["min_radius_tiles"],
        "summon_troop": d["summon_troop"],
    }
    out.update({k: v for k, v in row.items()})
    return out


def all_spell_ids(village: str | None = "home", standard_only: bool = False) -> list[int]:
    ids = [i for i, d in _load().items() if village is None or d["village"] == village]
    if standard_only:
        ids = [i for i in ids if i in STANDARD_SPELL_IDS]
    return sorted(ids)


def is_dark(data_id: int) -> bool:
    d = get_spell(data_id)
    return bool(d and d["is_dark"])


def housing_space(data_id: int) -> int | None:
    d = get_spell(data_id)
    return d["housing_space"] if d else None
