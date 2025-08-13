# attacks/attack_utils.py

import time
import random
from utils.mouse_actions import clicar, arrastar, clicar_coordenadas
from utils.image_recognition import clicar_por_imagem
from config.constants import DELAY_PADRAO, BOTOES
from utils.stop_handler import wait_and_check

def coletar_carrinho():
    """Função para coletar o carrinho de recursos."""
    arrastar(BOTOES['arrastar_cima'], BOTOES['arrastar_baixo'])
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))

    clicar_por_imagem('carrinho')
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))

    clicar('coletar')
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))

    clicar('fechar')
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))

def posicionar_tropa():
    """Posiciona tropas para um ataque padrão."""
    arrastar(BOTOES['arrastar_baixo'], BOTOES['arrastar_cima'])
    for i in range(9):
        clicar(f'selecionar_tropa_{i}')
        clicar_coordenadas((444, 360))
        wait_and_check(random.uniform(0.1, 0.2))

def procurar_partida():
    """Procura uma partida no jogo."""
    clicar('atacar')
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))
    
    clicar('encontrar')
    wait_and_check(DELAY_PADRAO + 5 + random.uniform(0.1, 0.2))

def render():
    """Aciona a rendição e retorna ao menu principal."""
    clicar('render_se')
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))

    clicar('ok')
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))

    clicar('voltar')
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))

def ataque():
    """Função para realizar um ataque padrão."""
    posicionar_tropa()
    # Acionar habilidades ao longo do ataque
    wait_and_check(8 + random.uniform(0.1, 0.2))
    clicar('selecionar_tropa_1')
    clicar('selecionar_tropa_2')
    clicar('selecionar_tropa_7')
    clicar('selecionar_tropa_8')
    wait_and_check(9 + random.uniform(0.1, 0.2))
    clicar('selecionar_tropa_3')
    clicar('selecionar_tropa_4')
    wait_and_check(3)
    clicar('selecionar_tropa_0')
    wait_and_check(9 + random.uniform(0.1, 0.2))
    clicar('selecionar_tropa_5')
    clicar('selecionar_tropa_6')

def ajustar_hotbar(army):
    """Ajusta a hotbar de acordo com os heróis selecionados."""

    for tropa in range (army['troops']['quantidade']):
        key = f"selecionar_tropa_{tropa+1}"
        if key not in army:
            army[key] = {}
        army[key]['sel'] = f"selecionar_tropa_{tropa+1}"
        
    if army['guardiao']['ativo']:
        army['guardiao']['sel'] = f"selecionar_tropa_{army['tropas']['quantidade']}"
    if army['rainha']['ativo']:
        army['rainha']['sel'] = f"selecionar_tropa_{army['tropas']['quantidade'] + army['guardiao']['ativo']}"
    if army['rei']['ativo']:
        army['rei']['sel'] = f"selecionar_tropa_{army['tropas']['quantidade'] + army['guardiao']['ativo'] + army['rainha']['ativo']}"
    if army['campea']['ativo']:
        army['campea']['sel'] = f"selecionar_tropa_{army['tropas']['quantidade'] + army['guardiao']['ativo'] + army['rainha']['ativo'] + army['rei']['ativo']}"

    for i in range(army['pocoes']['quantidade']):
        key = f"pocao_{i+1}"
        if key not in army:
            army[key] = {}
        army[key]['sel'] = f"selecionar_tropa_{army['tropas']['quantidade'] + army['guardiao']['ativo'] + army['rainha']['ativo'] + army['rei']['ativo'] + army['campea']['ativo'] + i}"

    return army