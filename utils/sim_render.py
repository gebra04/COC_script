"""Renderizador minimalista (PIL, top-down, abstrato — não isométrico) de um
estado de batalha (`utils.sim_replay.BattleReplay.state_at(t)` ou telemetria
real no mesmo formato). Função pura: estado -> imagem, sem interface.

Deliberadamente separado do simulador: serve tanto pra depurar o
`combat_sim` (Etapa 2 do PLANO_SIMULACAO.md) quanto, mais pra frente, pra
alimentar a aba "Gêmeo Digital" da GUI com telemetria ao vivo (Etapa 3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

from utils.battle_grid import GRID_SIZE
from utils.building_footprints import footprint as bf_footprint, is_wall as bf_is_wall
from utils import building_stats, defense_stats, troop_stats

BG = (24, 24, 28)
GRID_LINE = (40, 40, 46)
WALL_COLOR = (156, 132, 101)
HUD_COLOR = (230, 230, 235)
DEAD_OUTLINE = (70, 70, 76)

CLASS_COLOR = {
    "Defense": (193, 68, 60),
    "Resource": (212, 167, 44),
    "Army": (62, 166, 160),
    "Town Hall": (177, 93, 207),
    "Town Hall2": (177, 93, 207),
    "Npc": (122, 122, 134),
    "Npc Town Hall": (122, 122, 134),
    "Worker": (122, 122, 134),
    "Worker2": (122, 122, 134),
}
DEFAULT_BUILDING_COLOR = (140, 140, 150)

TROOP_GROUND = (240, 240, 242)
TROOP_FLYING = (126, 200, 255)

_FONT = None


def _font():
    global _FONT
    if _FONT is None:
        _FONT = ImageFont.load_default()
    return _FONT


def _building_class(did: int) -> str:
    from utils.building_footprints import _load as _bf_load
    d = _bf_load().get(int(did))
    return d[3] if d else "Unknown"


@dataclass
class RenderOptions:
    show_range: bool = False
    threat_grid: object | None = None       # np.ndarray (44,44) ou None -- ver compartment_graph.sector_dps
    weak_spot_grid: object | None = None    # np.ndarray (44,44) booleana -- compartment_graph.weakest_exterior
    highlight_troop_eid: str | None = None
    hud: bool = True


def _tile_px(size: int) -> float:
    return size / GRID_SIZE


def render_frame(state: dict, size: int = 616, opts: RenderOptions | None = None) -> Image.Image:
    """`state` no formato de `BattleReplay.state_at(t)` (ou telemetria real
    equivalente: dict com `entities` = lista de dicts classe/did/tx/ty/hp/lvl).
    Retorna uma imagem RGB `size x size` (default 14px/tile em 44x44)."""
    opts = opts or RenderOptions()
    px = _tile_px(size)
    img = Image.new("RGB", (size, size), BG)
    draw = ImageDraw.Draw(img, "RGBA")

    for i in range(0, GRID_SIZE + 1, 4):
        x = i * px
        draw.line([(x, 0), (x, size)], fill=GRID_LINE, width=1)
        draw.line([(0, x), (size, x)], fill=GRID_LINE, width=1)

    if opts.threat_grid is not None:
        _draw_heatmap(draw, opts.threat_grid, px)
    if opts.weak_spot_grid is not None:
        _draw_weak_spots(draw, opts.weak_spot_grid, px)

    entities = state.get("entities", [])
    walls = [e for e in entities if e.get("classe") == "Wall"]
    buildings = [e for e in entities if e.get("classe") not in ("Wall", "Troop")]
    troops = [e for e in entities if e.get("classe") == "Troop"]

    for e in walls:
        _draw_wall_cell(draw, e, px)
    for e in buildings:
        _draw_building(draw, e, px)
    if opts.show_range:
        for e in buildings:
            _draw_range_ring(draw, e, px)
    for e in troops:
        _draw_troop(draw, e, px, highlight=(e.get("eid") == opts.highlight_troop_eid))

    if opts.hud:
        _draw_hud(draw, state)

    return img


def _draw_wall_cell(draw: ImageDraw.ImageDraw, e: dict, px: float) -> None:
    x0, y0 = e["tx"] * px, e["ty"] * px
    alive = e.get("alive", True)  # ver nota em _draw_building: hp=0 fora de combate != morto
    color = WALL_COLOR if alive else DEAD_OUTLINE
    draw.rectangle([x0 + 1, y0 + 1, x0 + px - 1, y0 + px - 1], outline=color, width=1)


def _building_hp_ratio(e: dict) -> float:
    """Chamada só quando `alive` já é True (ver `_draw_building`). `hp<=0`
    nesse caso NAO significa morto -- na telemetria real o HP só é rastreado
    DURANTE combate (`pesquisa/02`, mesma convenção de `external_receiver.py`:
    "fora de combate (hp=0), assume cheio"); fora de batalha todo prédio
    reporta hp=0. Só distinguimos "morto de verdade" via a flag `alive`
    explícita (que o replay seta corretamente)."""
    did, lvl, hp = e["did"], int(e.get("lvl", 0) or 0), e.get("hp")
    if not hp or hp <= 0:
        return 1.0
    s = defense_stats.stats_at_level(did, lvl + 1) or building_stats.stats_at_level(did, lvl + 1)
    max_hp = s["hitpoints"] if s and s.get("hitpoints") else None
    if not max_hp:
        return 1.0
    return max(0.0, min(1.0, hp / max_hp))


def _draw_building(draw: ImageDraw.ImageDraw, e: dict, px: float) -> None:
    did = e["did"]
    w, h = bf_footprint(did)
    x0, y0 = e["tx"] * px, e["ty"] * px
    x1, y1 = x0 + w * px, y0 + h * px
    # sem flag `alive` explicita (telemetria real crua): assume vivo -- hp=0
    # fora de combate e o normal (ver docstring de `_building_hp_ratio`), nao
    # "destruido". So o replay (que rastreia `alive` de verdade) marca morto.
    alive = e.get("alive", True)
    if not alive:
        draw.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], outline=DEAD_OUTLINE, width=1)
        return
    base = CLASS_COLOR.get(_building_class(did), DEFAULT_BUILDING_COLOR)
    ratio = _building_hp_ratio(e)
    alpha = int(80 + 175 * ratio)  # nunca totalmente transparente enquanto vivo
    fill = (*base, alpha)
    draw.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], fill=fill, outline=(*base, 255), width=1)


def _draw_range_ring(draw: ImageDraw.ImageDraw, e: dict, px: float) -> None:
    if _building_class(e["did"]) != "Defense":
        return
    lvl = int(e.get("lvl", 0) or 0)
    s = defense_stats.stats_at_level(e["did"], lvl + 1)
    if not s or not s.get("range"):
        return
    w, h = bf_footprint(e["did"])
    cx, cy = (e["tx"] + w / 2.0) * px, (e["ty"] + h / 2.0) * px
    r = s["range"] * px
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(193, 68, 60, 60), width=1)


def _draw_troop(draw: ImageDraw.ImageDraw, e: dict, px: float, highlight: bool = False) -> None:
    did = e["did"]
    ts = troop_stats.get_troop(did)
    flying = bool(ts and ts.get("is_flying"))
    housing = (ts.get("housing_space") if ts else None) or 1
    radius = max(3.0, min(9.0, 2.0 + housing * 0.6)) * (px / 14.0)
    color = TROOP_FLYING if flying else TROOP_GROUND
    cx, cy = e["tx"] * px, e["ty"] * px
    if highlight:
        draw.ellipse([cx - radius - 3, cy - radius - 3, cx + radius + 3, cy + radius + 3],
                     outline=(255, 220, 80, 200), width=2)
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(*color, 235))


def _draw_heatmap(draw: ImageDraw.ImageDraw, grid, px: float) -> None:
    mx = float(grid.max()) or 1.0
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            v = float(grid[y, x])
            if v <= 0:
                continue
            alpha = int(90 * min(1.0, v / mx))
            x0, y0 = x * px, y * px
            draw.rectangle([x0, y0, x0 + px, y0 + px], fill=(220, 70, 40, alpha))


def _draw_weak_spots(draw: ImageDraw.ImageDraw, grid, px: float) -> None:
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            if grid[y, x]:
                x0, y0 = x * px, y * px
                draw.rectangle([x0, y0, x0 + px, y0 + px], fill=(60, 220, 120, 70))


def _draw_hud(draw: ImageDraw.ImageDraw, state: dict) -> None:
    t = state.get("t", 0.0)
    destruction = state.get("destruction_pct", 0.0)
    alive = state.get("troops_alive", 0)
    total = state.get("troops_total", 0)
    text = f"t={t:06.1f}s  destruicao {destruction:5.1f}%  tropas {alive}/{total}"
    draw.rectangle([2, 2, 8 + 6.2 * len(text), 16], fill=(0, 0, 0, 140))
    draw.text((5, 3), text, fill=HUD_COLOR, font=_font())


def render_gif(replay, path: str, fps: int = 10, size: int = 616,
                opts: RenderOptions | None = None) -> str:
    """Renderiza a batalha inteira do `replay` (`utils.sim_replay.BattleReplay`)
    num GIF animado em `path`. Retorna o path."""
    duration = replay.duration()
    step = 1.0 / fps
    n_frames = max(1, int(duration / step) + 1)
    frames = []
    t = 0.0
    for _ in range(n_frames):
        frames.append(render_frame(replay.state_at(t), size=size, opts=opts))
        t += step
    frames[0].save(path, save_all=True, append_images=frames[1:],
                    duration=int(1000 / fps), loop=0)
    return path
