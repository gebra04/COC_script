"""Navegação de menus via ADB (arquitetura B — sem injeção).

Coordenadas calibradas para Waydroid a 1366x739 (mesma resolução de
`cam_calib.json`). Cada função corresponde a UM toque/etapa do fluxo,
pra poder chamar isoladamente ou encadear.
"""

from __future__ import annotations

import time

from utils.adb_actuator import ADBInput


# --- Vila-casa ---
HOME_ATTACK_BUTTON = (90, 655)          # botão "Attack!" na vila

# --- Menu de ataque (aba já abre em "Multiplayer") ---
TAB_MULTIPLAYER = (150, 60)
TAB_PRACTICE = (695, 60)
FIND_A_MATCH_BUTTON = (225, 545)        # "Find a Match" (Multiplayer > Battle)

# --- Tela de confirmação de exército ---
CONFIRM_ATTACK_BUTTON = (1200, 667)     # "Attack!" (confirma e entra na partida)

# --- Fim de batalha ---
RETURN_HOME_BUTTON = (683, 633)

# --- Deploy ---
TROOP_SLOT_1 = (172, 670)               # 1º slot da barra de tropas em combate
DESELECT_TILE = (950, 470)              # tile de grama vazio p/ desselecionar
                                         # (NUNCA usar back/keyevent 4 aqui — ver memoria)


def _wait(seconds: float):
    time.sleep(seconds)


def start_multiplayer_search(inp: ADBInput):
    """Vila -> Attack -> (aba Multiplayer já default) -> Find a Match."""
    inp.tap(*HOME_ATTACK_BUTTON)
    _wait(2)
    inp.tap(*FIND_A_MATCH_BUTTON)
    _wait(2)


def confirm_army_and_attack(inp: ADBInput):
    """Tela de confirmação de exército -> Attack!."""
    inp.tap(*CONFIRM_ATTACK_BUTTON)


def wait_for_battle_start(seconds: float = 6.0):
    """Espera o matchmaking achar oponente e a base carregar (câmera parada)."""
    _wait(seconds)


def deploy_troop(inp: ADBInput, slot_xy: tuple[int, int], target_xy: tuple[int, int]):
    """Seleciona um slot de tropa e solta no pixel alvo (câmera já projetada)."""
    inp.tap(*slot_xy)
    _wait(0.4)
    inp.tap(*target_xy)


def return_home(inp: ADBInput):
    inp.tap(*RETURN_HOME_BUTTON)
    _wait(2)


def deselect(inp: ADBInput):
    """Desselecionar um prédio tocando grama vazia — nunca usar back (risco de
    abrir 'Confirm Exit')."""
    inp.tap(*DESELECT_TILE)


def recenter_village(inp: ADBInput, wait_after: float = 10.0):
    """Recentraliza a câmera da vila: force-stop + relançar (sempre abre
    centrado na Prefeitura). Mais confiável que adivinhar swipes de volta."""
    inp._adb("shell", "am", "force-stop", "com.supercell.clashofclans")
    _wait(2)
    inp._adb("shell", "monkey", "-p", "com.supercell.clashofclans",
              "-c", "android.intent.category.LAUNCHER", "1")
    _wait(wait_after)
