#!/usr/bin/env python3
"""Passo 2: solta uma tropa num pixel escolhido, re-le a memoria, acha a
tropa nova (nao estava no baseline) e resolve origin_x/origin_y da camera de
ataque (tile_w fixo em 46.0 - mesmo zoom da vila, confirmado por overlay).

Uso: python3 -m utils.calib_attack_deploy <target_x> <target_y> [out_dir]
"""
import json
import sys

from utils.adb_actuator import ADBInput
from utils import attack_flow
from utils.telemetry_capture import read_telemetry, take_screenshot

TILE_W = 46.0  # mesmo valor da vila (utils/cam_calib.json) - zoom nao muda em ataque


def solve_origin(sx: float, sy: float, tx: float, ty: float, tw: float = TILE_W):
    ox = sx - (tx - ty) * (tw / 2.0)
    oy = sy - (tx + ty) * (tw / 4.0)
    return ox, oy


def main():
    target_x, target_y = int(sys.argv[1]), int(sys.argv[2])
    out_dir = sys.argv[3] if len(sys.argv) > 3 else "/tmp/coc_calib"

    with open(f"{out_dir}/baseline_telem.json") as f:
        baseline = json.load(f)
    baseline_eids = {e["eid"] for e in baseline["entities"] if e["classe"] == "Troop"}

    inp = ADBInput()
    attack_flow.deploy_troop(inp, attack_flow.TROOP_SLOT_1, (target_x, target_y))

    import time
    time.sleep(0.4)  # so o minimo p/ a entidade aparecer na heap - tropa (esp.
    # voadora) comeca a se mover/pathing quase instantaneamente apos o spawn

    take_screenshot(f"{out_dir}/after_deploy_shot.png")
    telem = read_telemetry()
    with open(f"{out_dir}/after_deploy_telem.json", "w") as f:
        json.dump(telem, f)

    new_troops = [e for e in telem["entities"]
                  if e["classe"] == "Troop" and e["eid"] not in baseline_eids]
    if not new_troops:
        print("[!] nenhuma tropa nova encontrada - deploy falhou ou memoria nao atualizou")
        sys.exit(1)

    spawn = max(new_troops, key=lambda e: e["eid"])
    tx, ty = spawn["tx"], spawn["ty"]
    ox, oy = solve_origin(target_x, target_y, tx, ty)

    print(f"[+] tropa nova eid={spawn['eid']} did={spawn['did']} tile=({tx},{ty})")
    print(f"[+] tap alvo era pixel ({target_x},{target_y})")
    print(f"[+] origin resolvido: origin_x={ox:.1f} origin_y={oy:.1f} tile_w={TILE_W}")

    calib = {
        "resolution": [1366, 739], "density": 180,
        "origin_x": ox, "origin_y": oy, "tile_w": TILE_W,
        "note": "calibrado em ATAQUE (multiplayer) via deploy real -> leitura de "
                "memoria do tile de spawn. tile_w reaproveitado da vila (mesmo zoom, "
                "confirmado por overlay). origin muda a cada partida (pan novo) - "
                "recalibrar por ataque.",
    }
    with open("utils/cam_calib_attack.json", "w") as f:
        json.dump(calib, f, indent=2)
    print("[+] salvo em utils/cam_calib_attack.json")


if __name__ == "__main__":
    main()
