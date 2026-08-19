#!/usr/bin/env python3
"""Viewer interativo (Tkinter) de uma batalha simulada -- Etapa 3 do
PLANO_SIMULACAO.md. Casca fina em volta de `utils.sim_render.render_frame`:
toda a lógica de desenho mora lá, esta janela só monta o slider/play/toggles
e chama a função pura a cada frame.

Uso:
    python3 debug/sim_viewer.py --demo          # batalha sintetica embutida
    python3 debug/sim_viewer.py --json base.json --plan plan.json

`base.json`: lista de entidades no formato mem_reader.py --json (era 'entities').
`plan.json`: lista de {"did":, "level":, "tx":, "ty":, "t":} (DeployStep).
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.attack_simulator import DeployStep, simulate
from utils.sim_replay import BattleReplay
from utils.sim_render import RenderOptions, render_frame

CANVAS_SIZE = 616


def _demo_scenario():
    entities = [
        {"eid": 1, "did": 1000008, "classe": "Defense", "tx": 20, "ty": 20, "lvl": 0, "hp": None},
        {"eid": 2, "did": 1000010, "classe": "Wall", "tx": 19, "ty": 19, "lvl": 4, "hp": None},
        {"eid": 3, "did": 1000010, "classe": "Wall", "tx": 19, "ty": 20, "lvl": 4, "hp": None},
        {"eid": 4, "did": 1000010, "classe": "Wall", "tx": 19, "ty": 21, "lvl": 4, "hp": None},
        {"eid": 5, "did": 1000012, "classe": "Defense", "tx": 25, "ty": 10, "lvl": 0, "hp": None},
        {"eid": 6, "did": 1000004, "classe": "Resource", "tx": 5, "ty": 25, "lvl": 0, "hp": None},
        {"eid": 7, "did": 1000009, "classe": "Defense", "tx": 30, "ty": 30, "lvl": 2, "hp": None},
        {"eid": 8, "did": 1000013, "classe": "Defense", "tx": 10, "ty": 30, "lvl": 1, "hp": None},
    ]
    plan = [
        DeployStep(did=4000009, level=1, tx=10, ty=10, t=0.0),   # PEKKA
        DeployStep(did=4000008, level=1, tx=2, ty=30, t=2.0),    # Dragao
        DeployStep(did=4000003, level=1, tx=10, ty=2, t=4.0),    # Giant
        DeployStep(did=4000004, level=1, tx=19, ty=18, t=1.0),   # Wall Breaker
    ]
    return entities, plan


class SimViewer(tk.Tk):
    def __init__(self, replay: BattleReplay):
        super().__init__()
        self.title("Gêmeo Digital — Viewer de Simulação")
        self.replay = replay
        self.duration = replay.duration()
        self.playing = False
        self.speed = 1.0
        self._photo = None  # ref viva p/ o Tk nao coletar a imagem

        self.opts = RenderOptions()
        self.show_range_var = tk.BooleanVar(value=False)
        self.speed_var = tk.DoubleVar(value=1.0)
        self.time_var = tk.DoubleVar(value=0.0)
        self._syncing_slider = False  # evita reentrancia: ttk.Scale.set() dispara o proprio -command

        self._build_ui()
        self._render(0.0)

    # ------------------------------------------------------------- layout
    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=6, pady=4)

        self.canvas = tk.Canvas(self, width=CANVAS_SIZE, height=CANVAS_SIZE,
                                 bg="black", highlightthickness=0)
        self.canvas.pack(side=tk.TOP)
        self.canvas.bind("<Button-1>", self._on_click)

        bottom = ttk.Frame(self)
        bottom.pack(side=tk.TOP, fill=tk.X, padx=6, pady=4)

        self.play_btn = ttk.Button(bottom, text="▶ Play", command=self._toggle_play)
        self.play_btn.grid(row=0, column=0, padx=4)

        ttk.Label(bottom, text="Velocidade").grid(row=0, column=1, padx=(12, 2))
        speed_menu = ttk.OptionMenu(bottom, self.speed_var, 1.0, 0.25, 0.5, 1.0, 2.0, 4.0,
                                     command=self._on_speed_change)
        speed_menu.grid(row=0, column=2)

        ttk.Checkbutton(bottom, text="Alcance das defesas", variable=self.show_range_var,
                         command=self._on_toggle).grid(row=0, column=3, padx=(16, 4))

        self.slider = ttk.Scale(self, from_=0.0, to=max(self.duration, 0.01),
                                 orient=tk.HORIZONTAL, command=self._on_slide)
        self.slider.pack(side=tk.TOP, fill=tk.X, padx=6, pady=(0, 4))

        self.info_var = tk.StringVar(value="Clique numa tropa/prédio p/ inspecionar.")
        ttk.Label(self, textvariable=self.info_var, anchor="w").pack(
            side=tk.TOP, fill=tk.X, padx=8, pady=(0, 6))

    # ------------------------------------------------------------ eventos
    def _on_speed_change(self, value):
        self.speed = float(value)

    def _on_toggle(self):
        self.opts.show_range = self.show_range_var.get()
        self._render(self.time_var.get())

    def _on_slide(self, value):
        if self._syncing_slider:
            return  # disparado pelo nosso proprio slider.set() em _render, nao pelo usuario
        self.playing = False
        self.play_btn.config(text="▶ Play")
        self._render(float(value))

    def _toggle_play(self):
        self.playing = not self.playing
        self.play_btn.config(text="⏸ Pause" if self.playing else "▶ Play")
        if self.playing:
            self._tick()

    def _tick(self):
        if not self.playing:
            return
        t = self.time_var.get() + 0.1 * self.speed
        if t >= self.duration:
            t = self.duration
            self.playing = False
            self.play_btn.config(text="▶ Play")
        self._render(t)
        self.after(100, self._tick)

    def _on_click(self, event):
        px = CANVAS_SIZE / 44.0
        tx, ty = event.x / px, event.y / px
        state = self.replay.state_at(self.time_var.get())
        best, best_d = None, 2.5
        for e in state["entities"]:
            d = ((e["tx"] - tx) ** 2 + (e["ty"] - ty) ** 2) ** 0.5
            if d < best_d:
                best, best_d = e, d
        if best is None:
            self.info_var.set("Nada aqui.")
            return
        name = best["classe"]
        self.info_var.set(
            f"{name}  did={best['did']}  eid={best['eid']}  "
            f"hp={best['hp']:.0f}  pos=({best['tx']:.1f},{best['ty']:.1f})  "
            f"vivo={best.get('alive', True)}")

    # -------------------------------------------------------------- render
    def _render(self, t: float):
        t = max(0.0, min(t, self.duration))
        self.time_var.set(t)
        self._syncing_slider = True
        try:
            self.slider.set(t)
        finally:
            self._syncing_slider = False
        state = self.replay.state_at(t)
        img = render_frame(state, size=CANVAS_SIZE, opts=self.opts)
        # tk.PhotoImage nativo (via bytes PNG) em vez de PIL.ImageTk: evita
        # depender do binario _imagingtk (ABI Tcl/Tk pode nao bater com o
        # tkinter do venv -- ver PLANO_SIMULACAO.md nota da Etapa 3).
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        self._photo = tk.PhotoImage(data=buf.getvalue())
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="usa a batalha sintetica embutida")
    ap.add_argument("--json", type=str, help="path p/ base (lista de entidades, formato mem_reader --json)")
    ap.add_argument("--plan", type=str, help="path p/ plano de deploy (lista de DeployStep)")
    ap.add_argument("--max-time", type=float, default=180.0)
    args = ap.parse_args()

    if args.demo or not (args.json and args.plan):
        entities, plan = _demo_scenario()
    else:
        entities = json.loads(Path(args.json).read_text()).get("entities", [])
        raw_plan = json.loads(Path(args.plan).read_text())
        plan = [DeployStep(**p) for p in raw_plan]

    result = simulate(entities, plan, max_time=args.max_time)
    replay = BattleReplay(result.battle_log)
    print(f"Batalha simulada: destruicao={result.destruction_pct:.1f}% "
          f"tempo={result.time_elapsed:.1f}s sobreviventes={result.surviving_troops}/{result.total_troops}")

    app = SimViewer(replay)
    app.mainloop()


if __name__ == "__main__":
    main()
