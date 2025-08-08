# attacks/home_base.py

import time
import random
import pyautogui
from utils.mouse_actions import clicar, arrastar, clicar_coordenadas, gerar_pontos_na_reta
from attacks.attack_utils import procurar_partida, render
from config.constants import DELAY_PADRAO, BOTOES, CANTOS, RETAS
from utils.stop_handler import wait_and_check

def ataque_dragao(army):
    procurar_partida()
    wait_and_check(3)

    # Arrastar a tela
    arrastar(BOTOES['arrastar_baixo'], BOTOES['arrastar_cima'])
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))

    # Posicionar tropas de afunilamento
    if army['rei']['ativo']:
        clicar(army['rei']['sel'])
        clicar('posicao_dragao_1')
        clicar('selecionar_tropa_2')
        clicar('posicao_dragao_1')
            
    clicar('selecionar_tropa_1')
    clicar('posicao_dragao_1')
    clicar('posicao_dragao_2')
    
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))

    # Posicionar tropas de afunilamento
    clicar('posicao_dragao_13')
    clicar('posicao_dragao_14')
    clicar('posicao_dragao_15')

    if army['campea']['ativo']:
        clicar(army['campea']['sel'])
        clicar('posicao_dragao_15')
    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))

    # Posicionar tropas centrais
    clicar('selecionar_tropa_1')
    clicar('posicao_dragao_4')
    clicar('posicao_dragao_5')
    clicar('posicao_dragao_6')
    clicar('posicao_dragao_7')
    clicar('posicao_dragao_8')
    clicar('posicao_dragao_9')
    clicar('posicao_dragao_10')
    clicar('posicao_dragao_10')
    clicar('posicao_dragao_11')
    clicar('posicao_dragao_12')
    clicar('selecionar_tropa_0')
    clicar('posicao_dragao_6')

    if army['guardiao']['ativo']:
        clicar(army['guardiao']['sel'])
        clicar('posicao_dragao_6')
    if army['rainha']['ativo']:
        clicar(army['rainha']['sel'])
        clicar('posicao_dragao_6')

    wait_and_check(DELAY_PADRAO + random.uniform(0.1, 0.2))

    # Esperar as tropas se afunilarem
    wait_and_check(8)

    # Usar poções de fúria
    clicar(army['pocao_1']['sel'])
    clicar('pocao_de_furia_1')
    clicar('pocao_de_furia_2')
    clicar('pocao_de_furia_3')
    # Posicionar máquina de cerco
    if not army['rei']['ativo']:
        clicar('selecionar_tropa_2')
        clicar('posicao_dragao_10')

    # Esperar a primeira fúria acabar
    wait_and_check(12)

    # Usar últimas poções de fúria
    clicar(army['pocao_1']['sel'])
    clicar('pocao_de_furia_4')
    clicar('pocao_de_furia_5')

    wait_and_check(2)
    # Ativar habilidades dos heróis
    if army['guardiao']['ativo']:
        clicar(army['guardiao']['sel'])
    if army['rainha']['ativo']:
        clicar(army['rainha']['sel'])
    if army['rei']['ativo']:
        clicar(army['rei']['sel'])
    if army['campea']['ativo']:
        clicar(army['campea']['sel'])

    # Esperar o ataque terminar
    wait_and_check(85)
    render()
    

def ataque_goblin(army):
    procurar_partida()
    wait_and_check(2)

    arrastar(BOTOES['arrastar_cima'], BOTOES['arrastar_baixo'])
    if army['rei']['ativo']:
        clicar(army['rei']['sel'])
        clicar_coordenadas(CANTOS['C'])
    if army['campea']['ativo']:
        clicar(army['campea']['sel'])
        clicar_coordenadas(CANTOS['C'])
    if army['guardiao']['ativo']:
        clicar(army['guardiao']['sel'])
        clicar_coordenadas(CANTOS['C'])
    if army['rainha']['ativo']:
        clicar(army['rainha']['sel'])
        clicar_coordenadas(CANTOS['C'])

    clicar('selecionar_tropa_0')
    clicar_coordenadas(CANTOS['C'])
    clicar('selecionar_tropa_2')
    clicar_coordenadas(CANTOS['C'])

    arrastar(BOTOES['arrastar_baixo'], BOTOES['arrastar_cima'])
    i = 0

    clicar('selecionar_tropa_1')
    for reta in RETAS:
        if i == 2:                           
            arrastar(BOTOES['arrastar_cima'], BOTOES['arrastar_baixo'])
            clicar(army['pocao_1']['sel'])
            clicar_coordenadas((440, 200))
            clicar_coordenadas((440, 260))
            clicar_coordenadas((440, 320))
            clicar('selecionar_tropa_1')

        if i == 3:
            if army['rei']['ativo']:
                clicar(army['rei']['sel'])
            if army['campea']['ativo']:
                clicar(army['campea']['sel'])
            if army['guardiao']['ativo']:
                clicar(army['guardiao']['sel'])
            if army['rainha']['ativo']:
                clicar(army['rainha']['sel'])
            clicar(army['pocao_1']['sel'])
            clicar_coordenadas((380, 310))
            clicar_coordenadas((500, 310))
            clicar('selecionar_tropa_1')



        pontos = gerar_pontos_na_reta(RETAS[reta][0][0], RETAS[reta][0][1], RETAS[reta][1][0], RETAS[reta][1][1])
        for ponto in pontos:
            pyautogui.moveTo(ponto[0], ponto[1], duration=0.1)
            clicar_coordenadas(ponto)
            clicar_coordenadas(ponto)
            clicar_coordenadas(ponto)            
                
        i += 1

    wait_and_check(15)
    render()
    
