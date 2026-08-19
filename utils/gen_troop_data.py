#!/usr/bin/env python3
"""Gera utils/troop_data.json a partir do characters.csv dos gamefiles do CoC.

Filtra tropas REAIS (com ProductionBuilding — exclui traps/NPCs/secundárias).
data-id = 4000000 + índice. Unidades: alcance/splash em TILES; velocidade de
movimento em unidades do jogo; AttackSpeed em ms. HP/DPS por nível.
"""
import csv, json
from pathlib import Path

SRC = Path(__file__).with_name("characters.csv")
OUT = Path("/home/gebra/COC_script/utils/troop_data.json")

rows = list(csv.reader(open(SRC)))
cols = rows[0]
C = {c: i for i, c in enumerate(cols)}
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


troops = {}
bidx = -1
cur = None
carry = {}

for row in data:
    name = row[C["Name"]].strip()
    if name:
        bidx += 1
        cur = None
        carry = {}
        prod = row[C["ProductionBuilding"]].strip()
        disabled = boolean(row[C["DisableProduction"]])
        # tropa real: tem prédio de produção e não é desabilitada/secundária
        is_secondary = boolean(row[C["IsSecondaryTroop"]]) if "IsSecondaryTroop" in C else False
        if prod and not disabled and not is_secondary:
            data_id = 4000000 + bidx
            cur = {
                "data_id": data_id,
                "name": name,
                "village": "home" if row[C["VillageType"]].strip() in ("", "0") else "builder",
                "housing_space": num(row[C["HousingSpace"]], typ=int),
                "movement_speed": num(row[C["Speed"]], typ=int),
                "is_flying": boolean(row[C["IsFlying"]]),
                "attack_range_tiles": num(row[C["AttackRange"]], div=100),
                "splash_radius_tiles": num(row[C["DamageRadius"]], div=100),
                "attack_speed_ms": num(row[C["AttackSpeed"]], typ=int),
                "targets_air": boolean(row[C["AirTargets"]]),
                "targets_ground": boolean(row[C["GroundTargets"]]),
                "preferred_target_class": (row[C["PreferedTargetBuildingClass"]].strip() or None),
                "preferred_target_no_targeting": boolean(row[C["PreferredTargetNoTargeting"]]),
                # Multiplicador puro (nao percentual): Barbarian=1, Goblin=2,
                # Wall Breaker=40. NAO dividir por 100 (bug antigo fazia Wall
                # Breaker ler 0.4x em vez de 40x contra muralha).
                "preferred_target_damage_mod": num(row[C["PreferedTargetDamageMod"]]),
                "production_building": prod,
                # --- mecanica de agro/retarget (ver pesquisa/10_mecanica_combate.md) ---
                "defensive_troop": boolean(row[C["DefensiveTroop"]]) if "DefensiveTroop" in C else False,
                "prefer_heroes": boolean(row[C["PreferHeroes"]]) if "PreferHeroes" in C else False,
                "retarget_after_hit": boolean(row[C["RetargetAfterHit"]]) if "RetargetAfterHit" in C else False,
                "pick_new_target_after_pushback": boolean(row[C["PickNewTargetAfterPushback"]]) if "PickNewTargetAfterPushback" in C else False,
                "new_target_attack_delay_ms": num(row[C["NewTargetAttackDelay"]], typ=int) if "NewTargetAttackDelay" in C else None,
                "is_jumper": boolean(row[C["IsJumper"]]) if "IsJumper" in C else False,
                "wall_movement_cost": num(row[C["WallMovementCost"]], typ=int) if "WallMovementCost" in C else None,
                # --- multi-alvo / chain / burst ---
                "attack_multiple_buildings": boolean(row[C["AttackMultipleBuildings"]]) if "AttackMultipleBuildings" in C else False,
                "burst_count": num(row[C["BurstCount"]], typ=int) if "BurstCount" in C else None,
                "burst_delay_ms": num(row[C["BurstDelay"]], typ=int) if "BurstDelay" in C else None,
                "chain_attack_distance_tiles": num(row[C["ChainAttackDistance"]], div=100) if "ChainAttackDistance" in C else None,
                "chain_attack_max_targets": num(row[C["ChainAttackMaxTargets"]], typ=int) if "ChainAttackMaxTargets" in C else None,
                # --- multiplicadores de dano contextual ---
                "damage_multiplier_target": (row[C["DamageMultiplierTarget"]].strip() or None) if "DamageMultiplierTarget" in C else None,
                "damage_multiplier_percent": num(row[C["DamageMultiplierPercent"]], typ=int) if "DamageMultiplierPercent" in C else None,
                "hero_damage_multiplier": num(row[C["HeroDamageMultiplier"]], div=100) if "HeroDamageMultiplier" in C else None,
                # --- pesos usados na escolha de alvo/rota pela IA do motor ---
                "enemy_group_weight": num(row[C["EnemyGroupWeight"]], typ=int) if "EnemyGroupWeight" in C else None,
                "friendly_group_weight": num(row[C["FriendlyGroupWeight"]], typ=int) if "FriendlyGroupWeight" in C else None,
                "strength_weight": num(row[C["StrengthWeight"]], typ=int) if "StrengthWeight" in C else None,
                "levels": [],
            }
            troops[str(data_id)] = cur
    if cur is None:
        continue

    def cf(colname):
        v = row[C[colname]].strip()
        if v != "":
            carry[colname] = v
        return carry.get(colname, "")

    # Nivel implicito: os gamefiles atuais nao tem mais a coluna TroopLevel --
    # cada linha do grupo (a do Name + as seguintes com Name vazio) e o proximo
    # nivel, 1-indexed. A versao antiga do characters.csv trazia TroopLevel
    # explicito; aceitamos as duas.
    if "TroopLevel" in C:
        lvl = num(cf("TroopLevel"), typ=int)
        if lvl is None:
            continue
    else:
        lvl = len(cur["levels"]) + 1

    cur["levels"].append({
        "level": lvl,
        "hitpoints": num(cf("Hitpoints"), typ=int),
        "dps": num(cf("DPS"), typ=int),
    })

OUT.write_text(json.dumps(troops, indent=2, ensure_ascii=False))
home = [v for v in troops.values() if v["village"] == "home"]
print(f"{len(troops)} tropas ({len(home)} vila principal, {len(troops)-len(home)} construtor) → {OUT}")
for v in sorted(home, key=lambda x: x["data_id"]):
    if v["is_flying"] or v["attack_range_tiles"]:
        tt = "ar+terra" if v["targets_air"] and v["targets_ground"] else ("ar" if v["targets_air"] else "terra")
        fly = "VOA" if v["is_flying"] else "terra"
        print(f"  {v['data_id']} {v['name'][:20]:20s} house={v['housing_space']:>2} {fly:5s} "
              f"rng={v['attack_range_tiles']} atk={tt} alvo={v['preferred_target_class'] or '-'} nv={len(v['levels'])}")
