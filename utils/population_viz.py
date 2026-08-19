"""Vídeo mosaico da população (Passo 6 do planejamento de treino PPO — ver
PROXIMOS_PASSOS.md). Mostra os N ataques simulados de uma iteração de treino
lado a lado, sincronizados no tempo — pra gravar/entender visualmente o que
o lote de simulações paralelas ("população"/"geração", no vocabulário do
usuário) está fazendo.

100% reuso do que já existe e já foi testado: `utils.sim_render.render_frame`
(um frame por indivíduo) + `utils.sim_replay.BattleReplay.state_at` (o
estado de cada ataque em qualquer instante). A única peça nova é colar N
frames pequenos numa grade (`PIL.Image.paste`) e escrever o resultado como
`.mp4` via `imageio`/`imageio-ffmpeg` (binário ffmpeg embutido no pacote,
sem precisar instalar nada no sistema).
"""

from __future__ import annotations

import math
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw

from utils.sim_render import RenderOptions, render_frame
from utils.sim_replay import BattleReplay

TILE_SIZE = 220          # px por indivíduo na grade (pequeno o bastante pra N grande)
HEADER_HEIGHT = 40        # px reservados pro HUD agregado no topo do canvas
BG_COLOR = (18, 18, 22)


def _grid_dims(n: int) -> tuple[int, int]:
    cols = max(1, math.ceil(math.sqrt(n)))
    rows = max(1, math.ceil(n / cols))
    return cols, rows


def render_population_video(battle_logs: list, path: str | Path, fps: int = 10,
                             tile_size: int = TILE_SIZE, title: str = "",
                             extra_stats: dict | None = None) -> Path:
    """`battle_logs`: lista de `BattleLog` (uma por indivíduo/env — `None`
    é permitido e vira uma célula vazia, ex.: env que não completou nenhum
    episódio na iteração). Escreve um `.mp4` em `path` e devolve o `Path`."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    replays = [BattleReplay(log) if log is not None else None for log in battle_logs]
    durations = [r.duration() for r in replays if r is not None]
    max_duration = max(durations) if durations else 0.0
    n = len(battle_logs)
    cols, rows = _grid_dims(n)

    canvas_w = cols * tile_size
    canvas_h = rows * tile_size + HEADER_HEIGHT
    n_frames = max(1, int(max_duration * fps) + 1)

    opts = RenderOptions(hud=False)

    writer = imageio.get_writer(str(path), fps=fps, codec="libx264",
                                 macro_block_size=None, quality=8)
    try:
        for frame_i in range(n_frames):
            t = frame_i / fps
            canvas = Image.new("RGB", (canvas_w, canvas_h), BG_COLOR)
            for i, replay in enumerate(replays):
                r, c = divmod(i, cols)
                x0, y0 = c * tile_size, HEADER_HEIGHT + r * tile_size
                if replay is None:
                    continue
                tile = render_frame(replay.state_at(t), size=tile_size, opts=opts)
                canvas.paste(tile, (x0, y0))
                # borda fina + índice do indivíduo (rótulo minimo, não HUD completo)
                draw = ImageDraw.Draw(canvas)
                draw.rectangle([x0, y0, x0 + tile_size - 1, y0 + tile_size - 1],
                                outline=(70, 70, 80), width=1)
                draw.text((x0 + 4, y0 + 2), f"#{i}", fill=(230, 230, 230))

            _draw_header(canvas, t, max_duration, title, extra_stats)
            writer.append_data(np.array(canvas))
    finally:
        writer.close()

    return path


def _draw_header(canvas: Image.Image, t: float, max_duration: float,
                  title: str, extra_stats: dict | None) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, canvas.width, HEADER_HEIGHT], fill=(10, 10, 14))
    parts = [title] if title else []
    parts.append(f"t={t:5.1f}s / {max_duration:5.1f}s")
    if extra_stats:
        parts.extend(f"{k}={v}" for k, v in extra_stats.items())
    draw.text((8, 10), "   |   ".join(parts), fill=(235, 235, 235))


def render_from_rollout(data, path: str | Path, fps: int = 10,
                         iteration: int | None = None) -> Path:
    """Atalho pra chamar direto com o `RolloutData` de
    `utils.ppo_train.collect_rollout`/`train` (usa `data.battle_logs`,
    `data.episode_rewards`/`episode_destructions` pro HUD agregado)."""
    stats = {}
    if data.episode_rewards:
        stats["reward_medio"] = f"{sum(data.episode_rewards) / len(data.episode_rewards):.1f}"
    if data.episode_destructions:
        stats["destruicao_media"] = f"{sum(data.episode_destructions) / len(data.episode_destructions):.0f}%"
    title = f"Geração {iteration}" if iteration is not None else ""
    return render_population_video(data.battle_logs, path, fps=fps, title=title, extra_stats=stats)
