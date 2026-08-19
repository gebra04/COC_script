#!/usr/bin/env python3
"""Gera utils/spell_data.json a partir do spells.csv dos gamefiles do CoC.

Filtra feiticos REAIS do jogador (com ProductionBuilding = Spell Factory /
Dark Spell Factory), excluindo as ~135 entradas internas do motor que tambem
vivem no spells.csv (auras de heroi, efeitos de morte, spells de defesa,
projeteis sazonais etc.).

data-id: lido da coluna **GlobalID** (26000000+). NAO e derivado do indice da
linha -- Freeze e a 5a entrada mas tem id 26000005 -- por isso usamos a coluna
explicita, diferente de characters.csv/buildings.csv onde o id e posicional.

Unidades: Radius/MinRadius em centesimos de tile (500 -> 5.0 tiles); tempos em
ms; Damage e dano por acerto; DamageBoostPercent/SpeedBoost sao percentuais do
motor. Campos por nivel: o CSV atual nao tem coluna de nivel -- cada linha do
grupo e o proximo nivel (1-indexed), mesmo esquema do characters.csv novo.
"""
import csv, json
from pathlib import Path

SRC = Path(__file__).with_name("spells.csv")
OUT = Path(__file__).with_name("spell_data.json")

rows = list(csv.reader(open(SRC)))
C = {c: i for i, c in enumerate(rows[0])}
data = rows[2:]


def num(v, div=1, typ=float):
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return typ(float(v) / div)
    except ValueError:
        return None


def boolean(v):
    return (v or "").strip().lower() == "true"


def col(row, name, default=""):
    return row[C[name]].strip() if name in C else default


# Campos que variam por nivel (lidos linha a linha, com carry do ultimo valor
# nao-vazio, que e como os CSVs da Supercell representam "igual ao nivel anterior").
LEVEL_FIELDS = {
    "damage": ("Damage", 1, float),
    "boost_time_ms": ("BoostTimeMS", 1, int),
    "freeze_time_ms": ("FreezeTimeMS", 1, int),
    "speed_boost": ("SpeedBoost", 1, int),
    "damage_boost_percent": ("DamageBoostPercent", 1, int),
    "building_damage_boost_percent": ("BuildingDamageBoostPercent", 1, int),
    "troop_damage_permil": ("TroopDamagePermil", 1, int),
    "building_damage_permil": ("BuildingDamagePermil", 1, int),
    "radius_tiles": ("Radius", 100, float),
    "jump_boost_ms": ("JumpBoostMS", 1, int),
    "invisibility_time_ms": ("InvisibilityTime", 1, int),
    "spawn_duration_ms": ("SpawnDuration", 1, int),
    "damage_th_percent": ("DamageTHPercent", 1, int),
}

spells = {}
cur = None
carry = {}

for row in data:
    name = col(row, "Name")
    if name:
        cur = None
        carry = {}
        prod = col(row, "ProductionBuilding")
        disabled = boolean(col(row, "DisableProduction"))
        gid = num(col(row, "GlobalID"), typ=int)
        # feitico real do jogador: produzido numa fabrica e nao desabilitado
        if prod and not disabled and gid:
            cur = {
                "data_id": gid,
                "name": name,
                "village": "home" if col(row, "VillageType") in ("", "0") else "builder",
                "housing_space": num(col(row, "HousingSpace"), typ=int),
                "production_building": prod,
                "is_dark": "Dark" in prod,
                # constantes (nao variam por nivel)
                "deploy_time_ms": num(col(row, "DeployTimeMS"), typ=int),
                "hit_time_ms": num(col(row, "HitTimeMS"), typ=int),
                "time_between_hits_ms": num(col(row, "TimeBetweenHitsMS"), typ=int),
                "min_radius_tiles": num(col(row, "MinRadius"), div=100),
                "random_radius_tiles": num(col(row, "RandomRadius"), div=100),
                "summon_troop": col(row, "SummonTroop") or None,
                "preferred_target_damage_mod": num(col(row, "PreferredTargetDamageMod")),
                "boost_defenders": boolean(col(row, "BoostDefenders")),
                "levels": [],
            }
            spells[str(gid)] = cur
    if cur is None:
        continue

    def cf(colname):
        v = col(row, colname)
        if v != "":
            carry[colname] = v
        return carry.get(colname, "")

    lvl = {"level": len(cur["levels"]) + 1}
    for key, (csvcol, div, typ) in LEVEL_FIELDS.items():
        lvl[key] = num(cf(csvcol), div=div, typ=typ) if csvcol in C else None
    cur["levels"].append(lvl)

OUT.write_text(json.dumps(spells, indent=2, ensure_ascii=False))
home = [v for v in spells.values() if v["village"] == "home"]
print(f"{len(spells)} feiticos ({len(home)} vila principal) → {OUT}")
for v in sorted(home, key=lambda x: x["data_id"]):
    l1 = v["levels"][0] if v["levels"] else {}
    kind = "escuro" if v["is_dark"] else "normal"
    print(f"  {v['data_id']} {v['name'][:18]:18s} house={v['housing_space']:>2} {kind:6s} "
          f"raio={l1.get('radius_tiles')} dano={l1.get('damage')} "
          f"boost={l1.get('damage_boost_percent')}% freeze={l1.get('freeze_time_ms')}ms nv={len(v['levels'])}")
