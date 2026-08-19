"""Atuador — traduz a ação do agente em toques na tela do jogo (arquitetura B).

Fecha o único canal que faltava: o lado Python era só leitura. Aqui convertemos
uma ação `(tropa, tile_x, tile_y)` do PAMDP (Camada 4) em toques reais no
Waydroid via ADB — **sem injeção**, coerente com a arquitetura B (leitura externa
+ input externo; ver `mapeamento_arquivos.md` §Arquitetura B e `pesquisa/05`/`06`).

## O problema da câmera (crucial)
A memória dá a posição da entidade em **tiles do mundo** (coordenada lógica). A
tela mostra só um **recorte** do mapa, definido pelo estado da câmera:
- **pan** (para onde a câmera olha) → desloca a origem da projeção;
- **zoom** → escala o tamanho do tile em pixels.

Logo `tile_do_mundo → pixel_da_tela` depende de `CameraState(origin_x, origin_y,
tile_w)`. Esses parâmetros vêm da **memória** (o transform da câmera de render) —
ver `--cam-hunt` no `mem_reader.py` (a levantar) e `pesquisa/05`. Enquanto não
levantados, podem ser calibrados manualmente (fixando o zoom).

Projeção isométrica 2:1 (diamond), de `pesquisa/05`:
    screen_x = origin_x + (tx - ty) * (tile_w / 2)
    screen_y = origin_y + (tx + ty) * (tile_w / 4)
"""

from __future__ import annotations

import subprocess
import time
import random
from dataclasses import dataclass


@dataclass
class CameraState:
    """Estado da câmera que define o recorte visível → parâmetros da projeção.

    origin_x/origin_y = pixel da tela correspondente ao tile do mundo (0,0)
    (embute o pan). tile_w = largura de um tile em pixels (embute o zoom;
    altura = tile_w/2 na projeção 2:1).

    A levantar da memória (transform da câmera); ver `mem_reader --cam-hunt`.
    Defaults abaixo calibrados na vila-casa a 1366x739 via overlay-fit dos
    centros-de-chão dos prédios (ver `pesquisa/05` e `utils/cam_calib.json`).
    `origin_*` embute o PAN atual e muda quando a câmera se move; `tile_w`
    embute o ZOOM e vale enquanto o zoom não mudar.
    """
    origin_x: float = 620.0
    origin_y: float = -248.0
    tile_w: float = 46.0

    @classmethod
    def from_calib(cls, path: str = "utils/cam_calib.json") -> "CameraState":
        """Carrega a calibração salva (resolução/pan/zoom de referência)."""
        import json
        with open(path) as f:
            c = json.load(f)
        return cls(origin_x=c["origin_x"], origin_y=c["origin_y"], tile_w=c["tile_w"])

    def tile_to_screen(self, tx: float, ty: float) -> tuple[int, int]:
        sx = self.origin_x + (tx - ty) * (self.tile_w / 2.0)
        sy = self.origin_y + (tx + ty) * (self.tile_w / 4.0)
        return int(round(sx)), int(round(sy))

    def screen_to_tile(self, sx: float, sy: float) -> tuple[float, float]:
        """Inverso (útil para calibrar cruzando memória×tela)."""
        a = (sx - self.origin_x) / (self.tile_w / 2.0)
        b = (sy - self.origin_y) / (self.tile_w / 4.0)
        return (a + b) / 2.0, (b - a) / 2.0


class ADBInput:
    """Canal de input via ADB conectado ao Waydroid (`adb connect <ip>:5555`)."""

    def __init__(self, serial: str = "192.168.240.112:5555"):
        self.serial = serial

    def _adb(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["adb", "-s", self.serial, *args],
                              capture_output=True, text=True, timeout=10)

    def tap(self, x: int, y: int):
        self._adb("shell", "input", "tap", str(x), str(y))

    def screen_size(self) -> tuple[int, int] | None:
        out = self._adb("shell", "wm", "size").stdout
        # ex.: "Physical size: 1080x2340"
        for tok in out.replace(":", " ").split():
            if "x" in tok and tok.replace("x", "").isdigit():
                w, h = tok.split("x")
                return int(w), int(h)
        return None


# slot de cada tropa na barra inferior (pixel) — calibrar 1x por resolução.
# índice = ação discreta do PAMDP (Discrete(K)). A preencher na calibração.
TROOP_SLOTS: dict[int, tuple[int, int]] = {}


class Actuator:
    """Junta câmera + input: executa ações `(tropa, tx, ty)` do agente."""

    def __init__(self, camera: CameraState | None = None,
                 inp: ADBInput | None = None,
                 jitter_px: int = 6, jitter_ms: tuple[int, int] = (40, 120)):
        self.camera = camera or CameraState()
        self.inp = inp or ADBInput()
        self.jitter_px = jitter_px          # ruído espacial (anti-detecção, pesquisa/06)
        self.jitter_ms = jitter_ms          # ruído temporal entre toques

    def _tap_jittered(self, x: int, y: int):
        jx = x + random.randint(-self.jitter_px, self.jitter_px)
        jy = y + random.randint(-self.jitter_px, self.jitter_px)
        self.inp.tap(jx, jy)
        time.sleep(random.uniform(*self.jitter_ms) / 1000.0)

    def select_troop(self, slot_index: int):
        if slot_index not in TROOP_SLOTS:
            raise KeyError(f"slot {slot_index} não calibrado em TROOP_SLOTS")
        self._tap_jittered(*TROOP_SLOTS[slot_index])

    def deploy(self, slot_index: int, tx: float, ty: float, count: int = 1):
        """Seleciona a tropa e a solta no tile do mundo (tx,ty). count>1 = rajada."""
        self.select_troop(slot_index)
        px, py = self.camera.tile_to_screen(tx, ty)
        for _ in range(count):
            self._tap_jittered(px, py)

    def deploy_line(self, slot_index: int, tx0, ty0, tx1, ty1, n: int):
        """Deploy 'em linha' entre dois tiles (espalha n tropas)."""
        self.select_troop(slot_index)
        for i in range(n):
            f = i / max(n - 1, 1)
            tx = tx0 + (tx1 - tx0) * f
            ty = ty0 + (ty1 - ty0) * f
            self._tap_jittered(*self.camera.tile_to_screen(tx, ty))
