# attacks/builder_base.py

import time
import random
from attacks.attack_utils import procurar_partida, ataque, render
from config.constants import DELAY_PADRAO
from utils.mouse_actions import clicar
from utils.stop_handler import wait_and_check

def ganhar_uma():
    """Realiza uma batalha com vitória em uma vila do construtor."""
    procurar_partida()
    ataque()
    wait_and_check(40)
    render()

def ganhar_duas():
    """Realiza uma batalha com vitória em duas vilas do construtor."""
    procurar_partida()
    ataque()
    wait_and_check(60)
    ataque()
    wait_and_check(22)
    render()

def perder():
    """Inicia uma batalha e se rende."""    
    procurar_partida()
    clicar('selecionar_tropa_1')
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))
    clicar('posicionar_tropa')
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))
    render()

def hibrido(num_vilas):
    """Realiza uma batalha híbrida em uma ou duas vilas do construtor."""
    if num_vilas == 1:
        ganhar_uma()
    else:
        ganhar_duas()
    wait_and_check(2)
    perder()
    wait_and_check(2)