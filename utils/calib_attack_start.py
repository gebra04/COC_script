#!/usr/bin/env python3
"""Passo 1 da calibração de câmera de ataque: entra em Multiplayer, aguarda a
base carregar (câmera parada) e captura o par screenshot+telemetria baseline.

Uso: python3 -m utils.calib_attack_start [out_dir]
"""
import sys

from utils.adb_actuator import ADBInput
from utils import attack_flow
from utils.telemetry_capture import capture_pair


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/coc_calib"
    import os
    os.makedirs(out_dir, exist_ok=True)

    inp = ADBInput()
    attack_flow.start_multiplayer_search(inp)
    attack_flow.confirm_army_and_attack(inp)
    attack_flow.wait_for_battle_start(6.0)

    telem = capture_pair(f"{out_dir}/baseline_shot.png")
    with open(f"{out_dir}/baseline_telem.json", "w") as f:
        import json
        json.dump(telem, f)

    n = len(telem["entities"])
    troops = [e for e in telem["entities"] if e["classe"] == "Troop"]
    print(f"[+] baseline capturado: {n} entidades ({len(troops)} tropas ja em campo)")
    print(f"[+] screenshot: {out_dir}/baseline_shot.png")
    print(f"[+] telemetria: {out_dir}/baseline_telem.json")


if __name__ == "__main__":
    main()
