# config/constants.py

import random

# Delay padrão para simular um tempo de resposta humano.
DELAY_PADRAO = 0.3

# Dicionários de coordenadas
CANTOS = {
    'EB': (66, 181),
    'B': (445, 443),
    'DB': (834, 183),
    'EC': (42, 338),
    'C': (433, 54),
    'DC': (810, 339)
}

RETAS = {
    'EB': (CANTOS['EB'], CANTOS['B']),
    'DB': (CANTOS['DB'], CANTOS['B']),
    'EC': (CANTOS['EC'], CANTOS['C']),
    'DC': (CANTOS['DC'], CANTOS['C'])
}

def var():
    """Adiciona uma variação aleatória às coordenadas."""
    return random.randint(-2, 2)

BOTOES = {
    'atacar': (45 + var(), 473 + var()),
    'encontrar': (660 + var(), 350 + var()),
    'selecionar_tropa_0': (152 + var(), 470 + var()),
    # ... e todos os outros botões
    'arrastar_cima' : (441, 37),
    'arrastar_baixo' : (441, 323),
}