# attacks/home_base.py

import time
import random
from utils.mouse_actions import clicar, arrastar, clicar_coordenadas, gerar_pontos_na_reta
from attacks.attack_utils import procurar_partida, render
from config.constants import DELAY_PADRAO, BOTOES, CANTOS, RETAS


def ataque_dragao(herois, rei, rainha, guardiao, campea, sel_pocao):
    procurar_partida()
    time.sleep(3)

    # Arrastar a tela
    arrastar(BOTOES['arrastar_baixo'], BOTOES['arrastar_cima'])
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))

    # Posicionar tropas de afunilamento
    if rei['ativo']:
        clicar(rei['sel'])
        clicar('posicao_dragao_1')
        clicar('selecionar_tropa_2')
        clicar('posicao_dragao_1')
            
    clicar('selecionar_tropa_1')
    clicar('posicao_dragao_1')
    clicar('posicao_dragao_2')
    
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))

    # Posicionar tropas de afunilamento
    clicar('posicao_dragao_13')
    clicar('posicao_dragao_14')
    clicar('posicao_dragao_15')

    if campea['ativo']:
        clicar(campea['sel'])
        clicar('posicao_dragao_15')
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))

    # Posicionar tropas centrais]
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
    clicar('posicao_dragao_12')
    if herois:
        if guardiao['ativo']:
            clicar(guardiao['sel'])
            clicar('posicao_dragao_6')
        if rainha['ativo']:
            clicar(rainha['sel'])
            clicar('posicao_dragao_6')
    time.sleep(DELAY_PADRAO + random.uniform(0.1, 0.2))

    # Esperar as tropas se afunilarem
    time.sleep(8)

    # Usar poções de fúria
    clicar(sel_pocao)
    clicar('pocao_de_furia_1')
    clicar('pocao_de_furia_2')
    clicar('pocao_de_furia_3')
    # Posicionar máquina de cerco
    if not rei['ativo']:
        clicar('selecionar_tropa_2')
        clicar('posicao_dragao_10')

    # Esperar a primeira fúria acabar
    time.sleep(12)

    # Usar últimas poções de fúria
    clicar(sel_pocao)
    clicar('pocao_de_furia_4')
    clicar('pocao_de_furia_5')

    time.sleep(2)
    # Ativar habilidades dos heróis
    if herois:
        clicar(guardiao['sel']) if guardiao['ativo'] else None
        clicar(rainha['sel']) if rainha['ativo'] else None
        clicar(rei['sel']) if rei['ativo'] else None
        clicar(campea['sel']) if campea['ativo'] else None

    # Esperar o ataque terminar
    time.sleep(85)
    render()
    

def ataque_goblin(herois, rei, rainha, guardiao, campea, sel_pocao):
    procurar_partida()
    time.sleep(2)

    arrastar(BOTOES['arrastar_cima'], BOTOES['arrastar_baixo'])
    if herois:
        if rei['ativo']:
            clicar(rei['sel'])
            clicar_coordenadas(CANTOS['C'])
        if campea['ativo']:
            clicar(campea['sel'])
            clicar_coordenadas(CANTOS['C'])
        if guardiao['ativo']:
            clicar(guardiao['sel'])
            clicar_coordenadas(CANTOS['C'])
        if rainha['ativo']:
            clicar(rainha['sel'])
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
            clicar(sel_pocao)
            clicar_coordenadas((440, 200))
            clicar_coordenadas((440, 260))
            clicar_coordenadas((440, 320))
            clicar('selecionar_tropa_1')

        if i == 3:
            if herois:
                if rei['ativo']:
                    clicar(rei['sel'])
                if campea['ativo']:
                    clicar(campea['sel'])
                if guardiao['ativo']:
                    clicar(guardiao['sel'])
                if rainha['ativo']:
                    clicar(rainha['sel'])
            clicar(sel_pocao)
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

    time.sleep(15)
    render()
    
