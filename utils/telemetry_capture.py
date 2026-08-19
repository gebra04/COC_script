"""Captura pontual de telemetria (memória) e screenshot, pareadas no tempo.

Usado pela calibração da câmera de ataque: precisamos de um par
(screenshot, telemetria) tirado o mais próximo possível no tempo, com a
câmera ainda parada.
"""

from __future__ import annotations

import json
import os
import subprocess

DEFAULT_READER = os.path.expanduser("~/.local/share/coc-digital-twin/mem_reader.py")


def read_telemetry(serial: str = "192.168.240.112:5555",
                    reader_path: str = DEFAULT_READER,
                    python_bin: str = "/usr/bin/python3") -> dict:
    """`sudo mem_reader.py auto --json` -> dict {"pid":..., "entities":[...]}."""
    cmd = ["sudo", "-n", python_bin, reader_path, "auto", "--json"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if out.returncode != 0:
        raise RuntimeError(f"mem_reader --json falhou: {out.stderr.strip()}")
    return json.loads(out.stdout)


def take_screenshot(path: str, serial: str = "192.168.240.112:5555") -> str:
    with open(path, "wb") as f:
        subprocess.run(["adb", "-s", serial, "exec-out", "screencap", "-p"],
                        stdout=f, check=True, timeout=15)
    return path


def capture_pair(shot_path: str, serial: str = "192.168.240.112:5555") -> dict:
    """Tira o screenshot e lê a telemetria em sequência rápida; retorna a
    telemetria (o screenshot já fica salvo em `shot_path`)."""
    take_screenshot(shot_path, serial=serial)
    return read_telemetry(serial=serial)
