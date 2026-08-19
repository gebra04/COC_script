#!/usr/bin/env python3
"""Gera utils/defense_data.json a partir do buildings.csv dos gamefiles do CoC.

Extrai todas as defesas (BuildingClass == 'Defense'), com stats por nível
(HP, DPS) e por prédio (alcance, splash, alvos, velocidade, footprint).
data-id = 1000000 + índice do prédio no arquivo (confirmado por RE em memória).
Unidades: alcance/splash em TILES (CSV guarda ×100); velocidade em ms.
"""
import csv, json
from pathlib import Path

SRC = Path(__file__).with_name("buildings.csv")
OUT = Path("/home/gebra/COC_script/utils/defense_data.json")

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


def boolean(v):
    return (v or "").strip().upper() == "TRUE"


defenses = {}
bidx = -1
cur = None            # dict do prédio atual
carry = {}            # último valor não-vazio por coluna (carry-forward)

for row in data:
    name = row[C["Name"]].strip()
    if name:
        bidx += 1
        cur = None
        carry = {}
        if row[C["BuildingClass"]].strip() == "Defense":
            data_id = 1000000 + bidx
            cur = {
                "data_id": data_id,
                "name": name,
                "village": "home" if (row[C["VillageType"]].strip() in ("", "0")) else "builder",
                "width": num(row[C["Width"]], typ=int),
                "height": num(row[C["Height"]], typ=int),
                "air_targets": boolean(row[C["AirTargets"]]),
                "ground_targets": boolean(row[C["GroundTargets"]]),
                "attack_range_tiles": num(row[C["AttackRange"]], div=100),
                "min_attack_range_tiles": num(row[C["MinAttackRange"]], div=100),
                "splash_radius_tiles": num(row[C["DamageRadius"]], div=100),
                "attack_speed_ms": num(row[C["AttackSpeed"]], typ=int),
                "preferred_target": (row[C["PreferredTarget"]].strip() or None),
                "preferred_target_damage_mod": num(row[C["PreferredTargetDamageMod"]], div=100),
                # --- ativacao/gatilho (defesas escondidas, castelo do cla) ---
                "trigger_radius_tiles": num(row[C["TriggerRadius"]], div=100) if "TriggerRadius" in C else None,
                "wake_up_speed_ms": num(row[C["WakeUpSpeed"]], typ=int) if "WakeUpSpeed" in C else None,
                # --- mira/giro do canhao (afeta DPS efetivo contra alvo em movimento) ---
                "prepare_speed_ms": num(row[C["PrepareSpeed"]], typ=int) if "PrepareSpeed" in C else None,
                "needs_aim": boolean(row[C["NeedsAim"]]) if "NeedsAim" in C else False,
                "turn_speed": num(row[C["TurnSpeed"]], typ=int) if "TurnSpeed" in C else None,
                "targeting_cone_angle": num(row[C["TargetingConeAngle"]], typ=int) if "TargetingConeAngle" in C else None,
                # --- efeitos de impacto / multi-alvo ---
                "push_back": num(row[C["PushBack"]], typ=int) if "PushBack" in C else None,
                "chain_attack_distance_tiles": num(row[C["ChainAttackDistance"]], div=100) if "ChainAttackDistance" in C else None,
                "chain_attack_max_targets": num(row[C["ChainAttackMaxTargets"]], typ=int) if "ChainAttackMaxTargets" in C else None,
                "target_groups_radius_tiles": num(row[C["TargetGroupsRadius"]], div=100) if "TargetGroupsRadius" in C else None,
                # --- modo alternativo (ex.: X-Bow pode mirar ar, alcance/velocidade diferentes) ---
                "alt_attack_mode": boolean(row[C["AltAttackMode"]]) if "AltAttackMode" in C else False,
                "alt_air_targets": boolean(row[C["AltAirTargets"]]) if "AltAirTargets" in C else False,
                "alt_ground_targets": boolean(row[C["AltGroundTargets"]]) if "AltGroundTargets" in C else False,
                "alt_attack_range_tiles": num(row[C["AltAttackRange"]], div=100) if "AltAttackRange" in C else None,
                # --- rampa de dano (ex.: Torre Infernal single-target) ---
                "increasing_damage": boolean(row[C["IncreasingDamage"]]) if "IncreasingDamage" in C else False,
                "lv2_switch_time_ms": num(row[C["Lv2SwitchTime"]], typ=int) if "Lv2SwitchTime" in C else None,
                "lv3_switch_time_ms": num(row[C["Lv3SwitchTime"]], typ=int) if "Lv3SwitchTime" in C else None,
                "levels": [],
            }
            defenses[str(data_id)] = cur
    if cur is None:
        continue
    # por nível: level, TH requerido, HP, DPS (carry-forward do que estiver vazio)
    def cf(colname):
        v = row[C[colname]].strip()
        if v != "":
            carry[colname] = v
        return carry.get(colname, "")
    lvl = num(cf("BuildingLevel"), typ=int)
    if lvl is None:
        continue
    dps = num(cf("DPS"), typ=int)
    damage = num(cf("Damage"), typ=int) if "Damage" in C else None
    ammo_count = num(cf("AmmoCount"), typ=int) if "AmmoCount" in C else None
    atk_speed_ms = num(cf("AttackSpeed"), typ=int)
    # defesas de tiro-unico (Eagle Artillery, Multi Mortar): DPS=0/vazio na
    # planilha, o dano real esta em Damage (por tiro) + AttackSpeed (cadencia).
    # dps efetivo = dano-por-tiro / intervalo-entre-tiros, p/ o motor (que so
    # entende taxa continua) simular a mesma media de dano ao longo do tempo.
    effective_dps = dps
    if (not effective_dps) and damage and atk_speed_ms:
        effective_dps = damage / (atk_speed_ms / 1000.0)
    cur["levels"].append({
        "level": lvl,
        "th_required": num(cf("TownHallLevel"), typ=int),
        "hitpoints": num(cf("Hitpoints"), typ=int),
        "dps": dps,
        "damage_per_shot": damage,
        "ammo_count": ammo_count,
        "effective_dps": effective_dps,
        "dps_lv2": num(cf("DPSLv2"), typ=int) if "DPSLv2" in C else None,
        "dps_lv3": num(cf("DPSLv3"), typ=int) if "DPSLv3" in C else None,
    })

# remove entradas sem stats de combate (altares de herói etc. marcados Defense)
defenses = {k: v for k, v in defenses.items()
            if any(l["dps"] for l in v["levels"]) or v["attack_range_tiles"]}

OUT.write_text(json.dumps(defenses, indent=2, ensure_ascii=False))
home = [v for v in defenses.values() if v["village"] == "home"]
print(f"{len(defenses)} defesas ({len(home)} vila principal, "
      f"{len(defenses)-len(home)} base construtor) → {OUT}")
for v in sorted(home, key=lambda x: x["data_id"]):
    tgt = "ar+terra" if v["air_targets"] and v["ground_targets"] else \
          ("ar" if v["air_targets"] else "terra")
    print(f"  {v['data_id']} {v['name']:20s} {len(v['levels']):2d}nv  "
          f"rng={v['attack_range_tiles']} splash={v['splash_radius_tiles']} alvo={tgt}")
