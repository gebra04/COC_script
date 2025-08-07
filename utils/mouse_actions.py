# utils/mouse_actions.py

import pyautogui
import time
import random
from config.constants import BOTOES, DELAY_PADRAO

def clicar(nome_do_botao, duracao_clique=0.1):
    """Clica em um botão com base no seu nome no dicionário BOTOES."""
    if nome_do_botao in BOTOES:
        x, y = BOTOES[nome_do_botao]
        espera_aleatoria = random.uniform(0.1, 0.2)
        time.sleep(espera_aleatoria)
        pyautogui.click(x, y, duration=duracao_clique)
        print(f"Botão '{nome_do_botao}' clicado em ({x}, {y}).")
    else:
        print(f"Erro: Botão '{nome_do_botao}' não encontrado.")

def clicar_coordenadas(coordenadas, duracao_clique=0.1):
    """Clica em coordenadas específicas."""
    x, y = coordenadas
    espera_aleatoria = random.uniform(0.1, 0.2)
    time.sleep(espera_aleatoria)
    pyautogui.click(x, y, duration=duracao_clique)
    print(f"Clicado em coordenadas ({x}, {y}).")

def arrastar(inicio, fim, duracao=1):
    """Arrasta de um ponto inicial para um ponto final."""
    print(f"Iniciando arrasto de {inicio} para {fim}...")
    pyautogui.moveTo(inicio[0], inicio[1], duration=0.5)
    pyautogui.mouseDown(inicio[0], inicio[1])
    pyautogui.moveTo(fim[0], fim[1], duration=duracao)
    pyautogui.mouseUp(fim[0], fim[1])
    print("Arrasto concluído.")

def gerar_pontos_na_reta(xi, yi, xf, yf, num_pontos=8):
    """Gera uma lista de pontos aleatórios em uma reta."""
    pontos = []
    for _ in range(num_pontos):
        fator_aleatorio = random.uniform(0, 1)
        x = int(round(xi + (xf - xi) * fator_aleatorio))
        y = int(round(yi + (yf - yi) * fator_aleatorio))
        pontos.append((x, y))
    return pontos