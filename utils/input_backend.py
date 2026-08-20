"""Backend de input plugável: ADB (padrão) ou PyAutoGUI (compatibilidade).

Motivação (2026-08-20): o backend PyAutoGUI dirige o cursor REAL do host —
toma conta da máquina enquanto o bot roda, e no Fedora/Wayland só funciona
via Xwayland com o patch de auth em utils/xlib_mutter_xauth.py. O backend
ADB injeta direto no InputManager do Android (Waydroid), sem tocar no
cursor do host: dá pra usar o computador normalmente com o bot rodando, e
funciona mesmo com a janela do Waydroid atrás/sem foco (verificado).

Custo medido do ADB neste setup: ~50ms por toque (~33ms em lote). Nos
ataques isso é diluído pelos wait_and_check (o dragão tem 107s de espera
pra ~48 toques); o goblin é o mais afetado (~116 toques ≈ 6s de overhead).

Seleção do backend:
  COC_INPUT_BACKEND=adb        força ADB
  COC_INPUT_BACKEND=pyautogui  força PyAutoGUI (Windows/emulador na tela)
  (não setado)                 auto: ADB se houver device conectado, senão
                               PyAutoGUI — mantém o comportamento antigo
                               funcionando onde o ADB não se aplica.
"""
from __future__ import annotations

import os
import random
import subprocess
import time


class InputBackend:
    """Interface comum. Coordenadas sempre no espaço de destino final
    (device pro ADB, tela do host pro PyAutoGUI) — a conversão de espaço é
    responsabilidade de utils.coord_map, não daqui."""

    name = "base"

    def click(self, x: int, y: int, duracao: float = 0.1) -> None:
        raise NotImplementedError

    def move(self, x: int, y: int, duracao: float = 0.1) -> None:
        """Move sem clicar. No ADB não existe cursor: vira no-op (o clique
        seguinte já carrega a posição). Mantido na interface porque
        attacks/home_base.py usa moveTo antes de clicar em alguns pontos."""
        raise NotImplementedError

    def drag(self, x1: int, y1: int, x2: int, y2: int, duracao: float = 1.0) -> None:
        raise NotImplementedError


class ADBBackend(InputBackend):
    name = "adb"

    def __init__(self, serial: str | None = None):
        self.serial = serial or os.environ.get("COC_ADB_SERIAL")

    def _adb(self, *args: str) -> None:
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += list(args)
        subprocess.run(cmd, capture_output=True, timeout=15)

    def click(self, x: int, y: int, duracao: float = 0.1) -> None:
        self._adb("shell", "input", "tap", str(int(x)), str(int(y)))

    def move(self, x: int, y: int, duracao: float = 0.1) -> None:
        return  # sem cursor no ADB — ver docstring da interface

    def drag(self, x1: int, y1: int, x2: int, y2: int, duracao: float = 1.0) -> None:
        self._adb("shell", "input", "swipe", str(int(x1)), str(int(y1)),
                  str(int(x2)), str(int(y2)), str(int(duracao * 1000)))


class PyAutoGUIBackend(InputBackend):
    """Backend legado. Import de pyautogui é adiado pro construtor pra não
    arrastar X11/patch de auth em quem só usa ADB."""

    name = "pyautogui"

    def __init__(self):
        from utils.xlib_mutter_xauth import apply_patch as _patch
        _patch()
        import pyautogui
        self._pg = pyautogui

    def click(self, x: int, y: int, duracao: float = 0.1) -> None:
        self._pg.click(x, y, duration=duracao)

    def move(self, x: int, y: int, duracao: float = 0.1) -> None:
        self._pg.moveTo(x, y, duration=duracao)

    def drag(self, x1: int, y1: int, x2: int, y2: int, duracao: float = 1.0) -> None:
        self._pg.moveTo(x1, y1, duration=0.5)
        self._pg.mouseDown(x1, y1)
        self._pg.moveTo(x2, y2, duration=duracao)
        self._pg.mouseUp(x2, y2)


def _adb_disponivel() -> bool:
    try:
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return any(line.strip().endswith("device") for line in out.splitlines()[1:])


_backend: InputBackend | None = None


def get_backend() -> InputBackend:
    """Backend ativo (singleton). Ver docstring do módulo pra seleção."""
    global _backend
    if _backend is not None:
        return _backend

    escolha = (os.environ.get("COC_INPUT_BACKEND") or "").strip().lower()
    if escolha == "adb":
        _backend = ADBBackend()
    elif escolha in ("pyautogui", "pyautogui-compat", "compat"):
        _backend = PyAutoGUIBackend()
    elif escolha:
        raise ValueError(f"COC_INPUT_BACKEND desconhecido: {escolha!r} (use 'adb' ou 'pyautogui')")
    else:
        _backend = ADBBackend() if _adb_disponivel() else PyAutoGUIBackend()

    print(f"[input] backend: {_backend.name}")
    return _backend


def set_backend(backend: InputBackend) -> None:
    """Troca o backend em runtime (testes, ou GUI oferecendo a escolha)."""
    global _backend
    _backend = backend


def jitter_ms(lo: float = 0.1, hi: float = 0.2) -> None:
    """Pausa curta aleatória entre ações — preserva o comportamento antigo
    (mouse_actions dormia uniform(0.1,0.2) antes de cada clique)."""
    time.sleep(random.uniform(lo, hi))
