"""Screenshot/tap via adb, compartilhado entre hud_ocr, upgrade_picker,
live_ui_actions e session_loop — evita 3 cópias quase-idênticas da mesma
chamada de subprocess (cada módulo tinha a sua, achado na revisão de
2026-08-19 antes de juntar tudo)."""
from __future__ import annotations

import io
import subprocess

from PIL import Image


def screenshot() -> Image.Image:
    proc = subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True, check=True)
    return Image.open(io.BytesIO(proc.stdout))


def tap(x: int, y: int) -> None:
    subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], check=True)


def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 200) -> None:
    subprocess.run(["adb", "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
                    check=True)
