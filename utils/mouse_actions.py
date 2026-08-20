# utils/mouse_actions.py

"""API de input dos ataques. A assinatura pública (clicar, clicar_coordenadas,
arrastar, gerar_pontos_*) é a mesma de sempre — attacks/*.py não muda.

O que mudou em 2026-08-20: em vez de chamar pyautogui direto, delega pro
backend selecionado em utils.input_backend (ADB por padrão, PyAutoGUI como
compatibilidade — ver docstring de lá). Com o backend ADB as coordenadas de
config/constants.py são convertidas do espaço da janela original pro espaço
do device por utils.coord_map; com PyAutoGUI elas são usadas como estão,
preservando o comportamento antigo.
"""

import random
import time

from config.constants import BOTOES, DELAY_PADRAO
from utils.input_backend import get_backend, jitter_ms


def _converter(nome, xy):
    """Coordenada final pro backend ativo. No PyAutoGUI as constantes já
    estão no espaço certo (tela do host); no ADB precisam ir pro espaço do
    device."""
    if get_backend().name != "adb":
        return xy
    from utils import coord_map
    if nome is None:
        return coord_map.host_para_device(*xy)
    return coord_map.resolver_botao(nome, xy)


def clicar(nome_do_botao, duracao_clique=0.1):
    """Clica em um botão com base no seu nome no dicionário BOTOES."""
    from utils import coord_map

    xy_host = BOTOES.get(nome_do_botao)
    if xy_host is None:
        # Alguns nomes só existem como override medido em coord_map (ex.:
        # 'attack_army', que nunca esteve em BOTOES — o clique falhava
        # silenciosamente antes de 2026-08-20).
        overrides = coord_map.carregar_overrides()
        if get_backend().name == "adb" and nome_do_botao in overrides:
            x, y = overrides[nome_do_botao]
            jitter_ms()
            get_backend().click(x, y, duracao_clique)
            print(f"Botão '{nome_do_botao}' clicado em ({x}, {y}).")
            return
        print(f"Erro: Botão '{nome_do_botao}' não encontrado.")
        return

    x, y = _converter(nome_do_botao, xy_host)
    jitter_ms()
    get_backend().click(x, y, duracao_clique)
    print(f"Botão '{nome_do_botao}' clicado em ({x}, {y}).")


def clicar_coordenadas(coordenadas, duracao_clique=0.1):
    """Clica em coordenadas específicas (espaço de config/constants.py)."""
    x, y = _converter(None, coordenadas)
    jitter_ms()
    get_backend().click(x, y, duracao_clique)
    print(f"Clicado em coordenadas ({x}, {y}).")


def mover(coordenadas, duracao=0.1):
    """Move sem clicar. No backend ADB é no-op (não há cursor) — existe pra
    attacks/home_base.py não precisar falar com pyautogui direto."""
    x, y = _converter(None, coordenadas)
    get_backend().move(x, y, duracao)


def arrastar(inicio, fim, duracao=1):
    """Arrasta de um ponto inicial para um ponto final."""
    print(f"Iniciando arrasto de {inicio} para {fim}...")
    x1, y1 = _converter(None, inicio)
    x2, y2 = _converter(None, fim)
    get_backend().drag(x1, y1, x2, y2, duracao)
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


def gerar_pontos_nao_aleatorios(xi, yi, xf, yf, num_pontos=3):
    """Gera uma lista de pontos que dividem a reta em partes iguais, de acordo
    com o número de pontos especificado."""
    pontos = []
    for i in range(num_pontos):
        fator = i / (num_pontos - 1)  # Varia de 0 a 1
        x = int(round(xi + (xf - xi) * fator))
        y = int(round(yi + (yf - yi) * fator))
        pontos.append((x, y))
    return pontos
