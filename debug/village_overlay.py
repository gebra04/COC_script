"""Overlay visual de depuracao: desenha, por cima de um screenshot real, onde o
projeto ACHA que cada predio/muralha esta (projecao tile->pixel via
`CameraState`/`utils/cam_calib.json`).

Existe pra responder uma pergunta simples de fora: "voces esta enxergando a
vila no lugar certo?" -- se os contornos desenhados baterem com os predios de
verdade no screenshot, a calibracao (origin_x/origin_y/tile_w) esta correta
para aquele frame.

Uso:
    .venv/bin/python3 debug/village_overlay.py
        (captura screenshot + telemetria AO VIVO via adb/mem_reader.py)

    .venv/bin/python3 debug/village_overlay.py --screenshot foo.png --telemetry foo.json
        (usa arquivos ja capturados -- util quando o dispositivo esta instavel)

    .venv/bin/python3 debug/village_overlay.py --calib utils/cam_calib_attack.json
        (troca a calibracao usada na projecao -- p/ comparar vila vs ataque)

Import contract com o resto do projeto: NENHUM modulo de `utils/` foi
modificado para isto -- so consome `CameraState.from_calib` (adb_actuator.py)
e `building_footprints` (footprint/is_wall/building_name), do jeito que
`battle_grid.py`/`compartment_graph.py` ja fazem.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.adb_actuator import CameraState
from utils import building_footprints as bf

ADB_SERIAL = "192.168.240.112:5555"
MEM_READER = str(Path.home() / ".local/share/coc-digital-twin/mem_reader.py")

CLASS_COLOR = {
    "Wall": (200, 200, 60),
    "Building": (60, 200, 255),
    "Defense": (255, 90, 90),
    "Obstacle": (140, 140, 140),
    "Trap": (255, 140, 0),
    "Resource": (255, 215, 0),
}


def _capture_live() -> tuple[bytes, list[dict]]:
    """Screenshot + telemetria ao vivo (adb exec-out + mem_reader --json)."""
    shot = subprocess.run(
        ["adb", "-s", ADB_SERIAL, "exec-out", "screencap", "-p"],
        capture_output=True, timeout=20,
    ).stdout
    telem = subprocess.run(
        ["sudo", "-n", "/usr/bin/python3", MEM_READER, "auto", "--json"],
        capture_output=True, text=True, timeout=20,
    ).stdout
    # a ultima linha e o JSON (mem_reader imprime um log "[+] PID..." antes)
    line = [l for l in telem.splitlines() if l.strip().startswith("{")][-1]
    data = json.loads(line)
    return shot, data["entities"]


def _tile_corners(tx: float, ty: float, w: float, h: float, cam: CameraState):
    """4 cantos do footprint (em tile-space) projetados pra pixel, formando o
    'diamante' isometrico do predio no chao."""
    corners_tile = [(tx, ty), (tx + w, ty), (tx + w, ty + h), (tx, ty + h)]
    return [cam.tile_to_screen(x, y) for x, y in corners_tile]


def _draw_iso_grid(draw: ImageDraw.ImageDraw, cam: CameraState, size: int,
                    img_w: int, img_h: int, step: int = 5):
    """Grade isometrica de referencia (linhas a cada `step` tiles) + labels de
    coordenada, pra dar escala visual ao overlay."""
    grid_color = (255, 255, 255, 60)
    for tx in range(0, size + 1, step):
        p0 = cam.tile_to_screen(tx, 0)
        p1 = cam.tile_to_screen(tx, size)
        draw.line([p0, p1], fill=(0, 255, 0), width=1)
    for ty in range(0, size + 1, step):
        p0 = cam.tile_to_screen(0, ty)
        p1 = cam.tile_to_screen(size, ty)
        draw.line([p0, p1], fill=(0, 255, 0), width=1)
    for tx in range(0, size + 1, step):
        for ty in range(0, size + 1, step):
            x, y = cam.tile_to_screen(tx, ty)
            if -20 <= x <= img_w + 20 and -20 <= y <= img_h + 20:
                draw.text((x + 2, y - 8), f"{tx},{ty}", fill=(0, 255, 0))


def render_overlay(screenshot_bytes: bytes, entities: list[dict], cam: CameraState,
                    calib_path: str, out_path: Path) -> Path:
    img = Image.open(__import__("io").BytesIO(screenshot_bytes)).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    _draw_iso_grid(draw, cam, size=44, img_w=img.size[0], img_h=img.size[1])

    drawn, skipped = 0, 0
    for ent in entities:
        did = ent["did"]
        tx, ty = ent["tx"], ent["ty"]
        classe = ent.get("classe", "?")
        w, h = bf.footprint(did)
        name = bf.building_name(did)
        color = CLASS_COLOR.get(classe, (255, 255, 255))

        pts = _tile_corners(tx, ty, w, h, cam)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if max(xs) < -50 or min(xs) > img.size[0] + 50 or max(ys) < -50 or min(ys) > img.size[1] + 50:
            skipped += 1
            continue
        drawn += 1
        width = 1 if classe in ("Wall", "Obstacle") else 2
        draw.polygon(pts, outline=color, width=width)
        if classe not in ("Wall", "Obstacle"):
            cx, cy = cam.tile_to_screen(tx + w / 2.0, ty + h / 2.0)
            label = name if not name.startswith("data") else classe
            draw.text((cx - len(label) * 3, cy - 5), label, fill=color)

    composited = Image.alpha_composite(img, overlay).convert("RGB")
    draw2 = ImageDraw.Draw(composited)
    legend = [
        f"calib: {calib_path}  origin=({cam.origin_x:.1f},{cam.origin_y:.1f}) tile_w={cam.tile_w:.1f}",
        f"entidades: {drawn} desenhadas / {skipped} fora da tela / {len(entities)} total",
        "verde = grade isometrica (tiles do mundo) | ciano = Building | amarelo = Wall | laranja = Trap | cinza = Obstacle",
    ]
    for i, line in enumerate(legend):
        y = 4 + i * 14
        draw2.rectangle([2, y - 1, 6 + len(line) * 6, y + 12], fill=(0, 0, 0))
        draw2.text((4, y), line, fill=(255, 255, 255))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    composited.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--screenshot", help="PNG ja capturado (senao, captura ao vivo via adb)")
    ap.add_argument("--telemetry", help="JSON ja capturado (mesmo formato do mem_reader --json)")
    ap.add_argument("--calib", default="utils/cam_calib.json", help="calibracao de camera a usar")
    ap.add_argument("--out", default=None, help="caminho de saida (default: debug/output/overlay_<ts>.png)")
    args = ap.parse_args()

    cam = CameraState.from_calib(args.calib)

    if args.screenshot and args.telemetry:
        shot_bytes = Path(args.screenshot).read_bytes()
        entities = json.loads(Path(args.telemetry).read_text())["entities"]
    else:
        print("[*] capturando screenshot + telemetria ao vivo...")
        shot_bytes, entities = _capture_live()

    out_path = Path(args.out) if args.out else Path(__file__).parent / "output" / f"overlay_{int(time.time())}.png"
    saved = render_overlay(shot_bytes, entities, cam, args.calib, out_path)
    print(f"[+] overlay salvo em: {saved}")


if __name__ == "__main__":
    main()
