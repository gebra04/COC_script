# attacks/attack_utils.py

import time
import random
from utils.mouse_actions import clicar, arrastar, clicar_coordenadas
from utils.image_recognition import clicar_por_imagem
from config.constants import DELAY_PADRAO, BOTOES

def coletar_carrinho():
    """Função para coletar o carrinho de recursos."""
    arrastar(BOTOES['arrastar_cima'], BOTOES['arrastar_baixo'])
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))

    clicar_por_imagem('carrinho')
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))

    clicar('coletar')
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))

    clicar('fechar')
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))

def posicionar_tropa():
    """Posiciona tropas para um ataque padrão."""
    arrastar(BOTOES['arrastar_baixo'], BOTOES['arrastar_cima'])
    for i in range(9):
        clicar(f'selecionar_tropa_{i}')
        clicar_coordenadas((444, 360))
        time.sleep(random.uniform(0.1, 0.2))

def procurar_partida():
    """Procura uma partida no jogo."""
    clicar('atacar')
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))
    
    clicar('encontrar')
    time.sleep(DELAY_PADRAO + 5 + random.uniform(0.1, 0.2))

def render():
    """Aciona a rendição e retorna ao menu principal."""
    clicar('render_se')
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))

    clicar('ok')
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))

    clicar('voltar')
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))

def ataque():
    """Função para realizar um ataque padrão."""
    posicionar_tropa()
    # Acionar habilidades ao longo do ataque
    time.sleep(8 + random.uniform(0.1, 0.2))
    clicar('selecionar_tropa_1')
    clicar('selecionar_tropa_2')
    clicar('selecionar_tropa_7')
    clicar('selecionar_tropa_8')
    time.sleep(9 + random.uniform(0.1, 0.2))
    clicar('selecionar_tropa_3')
    clicar('selecionar_tropa_4')
    time.sleep(3)
    clicar('selecionar_tropa_0')
    time.sleep(9 + random.uniform(0.1, 0.2))
    clicar('selecionar_tropa_5')
    clicar('selecionar_tropa_6')

def ajustar_hotbar(rei, rainha, guardiao, campea):
    """Ajusta a hotbar de acordo com os heróis selecionados."""
    sel_rei, sel_rainha, sel_guardiao, sel_campea, sel_pocao = None, None, None, None, None

    if guardiao['ativo']:
        sel_guardiao = f"selecionar_tropa_{3}"
    if rainha['ativo']:
        sel_rainha = f"selecionar_tropa_{3 + guardiao['ativo']}"
    if rei['ativo']:
        sel_rei = f"selecionar_tropa_{3 + guardiao['ativo'] + rainha['ativo']}"
    if campea['ativo']:
        sel_campea = f"selecionar_tropa_{3 + guardiao['ativo'] + rainha['ativo'] + rei['ativo']}"

    sel_pocao = f"selecionar_tropa_{3 + guardiao['ativo'] + rainha['ativo'] + rei['ativo'] + campea['ativo']}"

    return sel_rei, sel_rainha, sel_guardiao, sel_campea, sel_pocao