"""Ferramenta interativa de anotacao manual: abre um screenshot e deixa VOCE
tracar, a olho, retas simples sobre as linhas de tile que enxerga na imagem, e
selecionar/rotular cada predio -- pra comparar contra o que `village_overlay.py`
acha que esta desenhando (e, se voce marcar pontos com coordenada de tile
conhecida, a ferramenta ja resolve o `origin_x/origin_y/tile_w` que melhor
encaixa nas suas marcacoes).

Uso:
    .venv/bin/python3 debug/tile_tracer.py <screenshot.png>
    .venv/bin/python3 debug/tile_tracer.py            # usa a ultima captura
                                                        # em debug/output/ ou
                                                        # /tmp/coc_calib se achar

Controles (janela Tkinter):
    clique esquerdo         -> conforme o modo atual:
                                 [reta]: 1o clique = ponto A, 2o clique = ponto B
                                 [predio]: 1 clique = marca + pede rotulo/tile
    L                       -> muda pro modo RETA (traçar linha de grade)
    P                       -> muda pro modo PREDIO (marcar/rotular construcao)
    U / Ctrl+Z              -> desfaz a ultima marcacao
    S                       -> salva (JSON + PNG anotado) em debug/output/
    F                       -> tenta ajustar origin_x/origin_y/tile_w pelos
                                pontos de predio que tiverem rotulo "tx,ty"
    Q / Esc                 -> sai (pergunta se quer salvar antes)

O rotulo de um ponto de predio pode ser:
    - um nome livre (ex.: "Canhao", "Torre de Arqueiras") -> so anotacao visual
    - "tx,ty" (ex.: "18,22") -> tile do MUNDO conhecido (de telemetria real);
      esses pontos entram no ajuste de calibracao (`F`).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageTk
import tkinter as tk
from tkinter import simpledialog, messagebox

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "output"

LINE_COLOR = "#00e0ff"
POINT_COLOR = "#ff4040"
POINT_COLOR_TILE = "#ffd000"  # ponto com "tx,ty" conhecido (entra no fit)


def _find_default_screenshot() -> Path | None:
    candidates = sorted(OUT_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0]
    fallback = Path("/tmp/coc_calib/baseline_shot.png")
    return fallback if fallback.exists() else None


class TileTracer:
    def __init__(self, root: tk.Tk, image_path: Path):
        self.root = root
        self.image_path = image_path
        self.img = Image.open(image_path).convert("RGB")
        self.tk_img = ImageTk.PhotoImage(self.img)

        self.mode = "line"  # "line" | "point"
        self.lines: list[tuple[int, int, int, int]] = []
        self.points: list[dict] = []  # {"x":, "y":, "label":}
        self._pending_line_start: tuple[int, int] | None = None
        self._undo_stack: list[str] = []  # "line" ou "point", na ordem de criacao

        root.title(f"Tile Tracer — {image_path.name} — modo: RETA (L=reta P=predio S=salvar F=fit U=desfazer)")

        self.canvas = tk.Canvas(root, width=self.img.width, height=self.img.height, cursor="crosshair")
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.status = tk.Label(root, text=self._status_text(), anchor="w", font=("monospace", 10))
        self.status.pack(fill="x")

        self.canvas.bind("<Button-1>", self._on_click)
        root.bind("<Key>", self._on_key)

    # ------------------------------------------------------------- status
    def _status_text(self) -> str:
        return (f"modo={self.mode.upper()}  retas={len(self.lines)}  "
                f"pontos={len(self.points)}  "
                f"(L=reta P=predio U=desfazer S=salvar F=fit-calib Q=sair)")

    def _refresh_status(self):
        self.status.config(text=self._status_text())
        self.root.title(f"Tile Tracer — {self.image_path.name} — modo: {self.mode.upper()}")

    # --------------------------------------------------------------- input
    def _on_key(self, ev: tk.Event):
        key = ev.keysym.lower()
        if key == "l":
            self.mode = "line"
            self._pending_line_start = None
            self._refresh_status()
        elif key == "p":
            self.mode = "point"
            self._pending_line_start = None
            self._refresh_status()
        elif key in ("u", "z"):
            self._undo()
        elif key == "s":
            self._save()
        elif key == "f":
            self._fit_calibration()
        elif key in ("q", "escape"):
            self._quit()

    def _on_click(self, ev: tk.Event):
        x, y = ev.x, ev.y
        if self.mode == "line":
            if self._pending_line_start is None:
                self._pending_line_start = (x, y)
                self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, outline=LINE_COLOR, width=2, tags="tmp_pt")
            else:
                x0, y0 = self._pending_line_start
                self.canvas.delete("tmp_pt")
                self.canvas.create_line(x0, y0, x, y, fill=LINE_COLOR, width=2)
                self.lines.append((x0, y0, x, y))
                self._undo_stack.append("line")
                self._pending_line_start = None
                self._refresh_status()
        else:  # point
            label = simpledialog.askstring(
                "Rotular predio",
                "Nome do predio, OU tile conhecido no formato tx,ty (ex.: 18,22):",
                parent=self.root,
            )
            if label is None:
                return
            self.points.append({"x": x, "y": y, "label": label.strip()})
            self._undo_stack.append("point")
            is_tile = self._parse_tile_label(label.strip()) is not None
            color = POINT_COLOR_TILE if is_tile else POINT_COLOR
            r = 4
            self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=color, width=2)
            self.canvas.create_text(x + r + 2, y - r - 6, text=label.strip(), fill=color, anchor="w",
                                     font=("monospace", 9, "bold"))
            self._refresh_status()

    @staticmethod
    def _parse_tile_label(label: str) -> tuple[float, float] | None:
        parts = label.replace(" ", "").split(",")
        if len(parts) != 2:
            return None
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return None

    def _undo(self):
        if not self._undo_stack:
            return
        kind = self._undo_stack.pop()
        if kind == "line" and self.lines:
            self.lines.pop()
        elif kind == "point" and self.points:
            self.points.pop()
        self._redraw()

    def _redraw(self):
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        for x0, y0, x1, y1 in self.lines:
            self.canvas.create_line(x0, y0, x1, y1, fill=LINE_COLOR, width=2)
        for pt in self.points:
            is_tile = self._parse_tile_label(pt["label"]) is not None
            color = POINT_COLOR_TILE if is_tile else POINT_COLOR
            x, y, r = pt["x"], pt["y"], 4
            self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=color, width=2)
            self.canvas.create_text(x + r + 2, y - r - 6, text=pt["label"], fill=color, anchor="w",
                                     font=("monospace", 9, "bold"))
        self._refresh_status()

    # ------------------------------------------------------------- ajuste
    def _fit_calibration(self):
        """Resolve origin_x/origin_y/tile_w por minimos quadrados a partir dos
        pontos marcados com rotulo 'tx,ty'. Projecao (de `adb_actuator.CameraState`):
            sx = origin_x + (tx-ty)*(tile_w/2)
            sy = origin_y + (tx+ty)*(tile_w/4)
        Linear em [origin_x, origin_y, tile_w] -> lstsq direto."""
        tiles = []
        for pt in self.points:
            tile = self._parse_tile_label(pt["label"])
            if tile is not None:
                tiles.append((pt["x"], pt["y"], tile[0], tile[1]))

        if len(tiles) < 2:
            messagebox.showinfo("Fit de calibracao",
                                 "Precisa de pelo menos 2 pontos rotulados com 'tx,ty' "
                                 "(tile conhecido) para ajustar a calibracao.")
            return

        rows_A, rows_b = [], []
        for sx, sy, tx, ty in tiles:
            rows_A.append([1, 0, (tx - ty) / 2.0])
            rows_b.append(sx)
            rows_A.append([0, 1, (tx + ty) / 4.0])
            rows_b.append(sy)
        A = np.array(rows_A, dtype=float)
        b = np.array(rows_b, dtype=float)
        sol, residuals, rank, _ = np.linalg.lstsq(A, b, rcond=None)
        origin_x, origin_y, tile_w = sol

        pred = A @ sol
        err = np.abs(pred - b)
        rms = float(np.sqrt(np.mean((pred - b) ** 2)))

        result = {
            "origin_x": float(origin_x), "origin_y": float(origin_y), "tile_w": float(tile_w),
            "n_points": len(tiles), "rms_error_px": rms, "max_error_px": float(err.max()),
            "note": f"ajustado por lstsq a partir de {len(tiles)} pontos manuais em {self.image_path.name}",
        }
        out_path = OUT_DIR / f"fit_calib_{int(time.time())}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2))

        messagebox.showinfo(
            "Fit de calibracao",
            f"origin_x={origin_x:.1f}  origin_y={origin_y:.1f}  tile_w={tile_w:.1f}\n"
            f"erro RMS={rms:.1f}px  erro max={err.max():.1f}px  (n={len(tiles)} pontos)\n\n"
            f"salvo em {out_path}",
        )

    # --------------------------------------------------------------- salvar
    def _save(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        json_path = OUT_DIR / f"trace_{ts}.json"
        png_path = OUT_DIR / f"trace_{ts}.png"

        data = {
            "source_screenshot": str(self.image_path),
            "lines": [{"x0": l[0], "y0": l[1], "x1": l[2], "y1": l[3]} for l in self.lines],
            "points": self.points,
        }
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

        annotated = self.img.copy()
        draw = ImageDraw.Draw(annotated)
        for x0, y0, x1, y1 in self.lines:
            draw.line([(x0, y0), (x1, y1)], fill=(0, 224, 255), width=2)
        for pt in self.points:
            is_tile = self._parse_tile_label(pt["label"]) is not None
            color = (255, 208, 0) if is_tile else (255, 64, 64)
            x, y, r = pt["x"], pt["y"], 4
            draw.ellipse([x - r, y - r, x + r, y + r], outline=color, width=2)
            draw.text((x + r + 2, y - r - 6), pt["label"], fill=color)
        annotated.save(png_path)

        self.status.config(text=f"salvo: {json_path.name} + {png_path.name}")
        print(f"[+] anotacoes salvas em: {json_path}")
        print(f"[+] imagem anotada salva em: {png_path}")

    def _quit(self):
        if self.lines or self.points:
            if messagebox.askyesno("Sair", "Salvar anotacoes antes de sair?"):
                self._save()
        self.root.destroy()


def main():
    if len(sys.argv) > 1:
        image_path = Path(sys.argv[1])
    else:
        image_path = _find_default_screenshot()
        if image_path is None:
            print("[!] nenhum screenshot informado e nenhum default encontrado "
                  "(debug/output/*.png ou /tmp/coc_calib/baseline_shot.png).")
            print("uso: .venv/bin/python3 debug/tile_tracer.py <screenshot.png>")
            sys.exit(1)
        print(f"[*] usando screenshot default: {image_path}")

    if not image_path.exists():
        print(f"[!] arquivo nao encontrado: {image_path}")
        sys.exit(1)

    root = tk.Tk()
    TileTracer(root, image_path)
    root.mainloop()


if __name__ == "__main__":
    main()
