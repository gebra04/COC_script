#!/usr/bin/env python3
"""Gera utils/building_data.json a partir do buildings.csv dos gamefiles do CoC.

Cobre TODOS os prédios (qualquer BuildingClass — Defense/Resource/Army/
Wall/Town Hall/Npc/Worker/...), não só defesas (`defense_data.json` filtra
BuildingClass=='Defense'). Extrai só o que existe universalmente: HP por
nível + footprint + classe. Serve pra tapar o fallback `hp = 100.0` do
`utils/combat_sim.py` para prédios sem stats de combate (TH, depósitos,
acampamentos, muralha).
data-id = 1000000 + índice do prédio no arquivo (mesma indexação de
`gen_defense_data.py`/`building_footprints.py`, confirmado por RE em memória).
"""
import csv, json
from pathlib import Path

SRC = Path(__file__).with_name("buildings.csv")
OUT = Path("/home/gebra/COC_script/utils/building_data.json")

rows = list(csv.reader(open(SRC)))
cols = rows[0]
C = {c: i for i, c in enumerate(cols)}
data = rows[2:]  # pula linha de nomes e de tipos


def num(v, div=1, typ=float):
    v = (v or "").strip()
    if v == "":
        return None
    try:
        return typ(float(v) / div)
    except ValueError:
        return None


buildings = {}
bidx = -1
cur = None
carry = {}

for row in data:
    name = row[C["Name"]].strip()
    if name:
        bidx += 1
        data_id = 1000000 + bidx
        cur = {
            "data_id": data_id,
            "name": name,
            "building_class": row[C["BuildingClass"]].strip(),
            "village": "home" if (row[C["VillageType"]].strip() in ("", "0")) else "builder",
            "width": num(row[C["Width"]], typ=int),
            "height": num(row[C["Height"]], typ=int),
            "levels": [],
        }
        buildings[str(data_id)] = cur
        carry = {}

    def cf(colname):
        v = row[C[colname]].strip()
        if v != "":
            carry[colname] = v
        return carry.get(colname, "")

    lvl = num(cf("BuildingLevel"), typ=int)
    if lvl is None:
        continue
    cur["levels"].append({
        "level": lvl,
        "th_required": num(cf("TownHallLevel"), typ=int),
        "hitpoints": num(cf("Hitpoints"), typ=int),
    })

# remove entradas sem nenhum HP (ex.: decoração/placeholder sem stats reais)
buildings = {k: v for k, v in buildings.items() if any(l["hitpoints"] for l in v["levels"])}

OUT.write_text(json.dumps(buildings, indent=2, ensure_ascii=False))
home = [v for v in buildings.values() if v["village"] == "home"]
print(f"{len(buildings)} prédios ({len(home)} vila principal, "
      f"{len(buildings)-len(home)} base construtor) → {OUT}")
by_class = {}
for v in home:
    by_class.setdefault(v["building_class"], 0)
    by_class[v["building_class"]] += 1
for cls, n in sorted(by_class.items()):
    print(f"  {cls:20s} {n}")
