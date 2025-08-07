# attacks/builder_base.py

import time
import random
from attacks.attack_utils import procurar_partida, ataque, render
from config.constants import DELAY_PADRAO
from utils.mouse_actions import clicar

def ganhar_uma():
    """Realiza uma batalha com vitória em uma vila do construtor."""
    procurar_partida()
    ataque()
    time.sleep(40)
    render()

def ganhar_duas():
    """Realiza uma batalha com vitória em duas vilas do construtor."""
    procurar_partida()
    ataque()
    time.sleep(60)
    ataque()
    time.sleep(22)
    render()

def perder():
    """Inicia uma batalha e se rende."""    
    procurar_partida()
    clicar('selecionar_tropa_1')
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))
    clicar('posicionar_tropa')
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))
    render()