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
    'selecionar_tropa_1': (152 + var(), 490 + var()),
    'selecionar_tropa_2': (212 + var(), 490 + var()),
    'selecionar_tropa_3': (272 + var(), 490 + var()),
    'selecionar_tropa_4': (332 + var(), 490 + var()),
    'selecionar_tropa_5': (392 + var(), 490 + var()),
    'selecionar_tropa_6': (452 + var(), 490 + var()),
    'selecionar_tropa_7': (512 + var(), 490 + var()),
    'selecionar_tropa_8': (572 + var(), 490 + var()),
    'selecionar_tropa_9': (632 + var(), 490 + var()),
    'posicionar_tropa': (866 + var(), 276 + var()),
    'render_se': (65 + var(), 420 + var()),
    'ok': (522 + var(), 338 + var()),
    'voltar': (442 + var(), 449 + var()),
    'arrastar_inicio': (779 + var(), 264 + var()),
    'arrastar_fim': (779 + var(), 400 + var()),
    'carrinho': (614 + var(), 98 + var()),
    'coletar': (650 + var(), 450 + var()),
    'fechar': (740 + var(), 80 + var()),
    'posicao_dragao_1': (470 + var(), 420 + var()),
    'posicao_dragao_2': (480 + var(), 415 + var()),
    'posicao_dragao_3': (495 + var(), 405 + var()),
    'posicao_dragao_4': (570 + var(), 400 + var()),
    'posicao_dragao_5': (585 + var(), 332 + var()),
    'posicao_dragao_6': (600 + var(), 324 + var()),
    'posicao_dragao_7': (615 + var(), 316 + var()),
    'posicao_dragao_8': (625 + var(), 306 + var()),
    'posicao_dragao_9': (640 + var(), 296 + var()),
    'posicao_dragao_10': (655 + var(), 283 + var()),
    'posicao_dragao_11': (665 + var(), 278 + var()),
    'posicao_dragao_12': (680 + var(), 269 + var()),
    'posicao_dragao_13': (730 + var(), 230 + var()),
    'posicao_dragao_14': (745 + var(), 213 + var()),
    'posicao_dragao_15': (765 + var(), 198 + var()),
    'pocao_de_furia_1': (478 + var(), 270 + var()),
    'pocao_de_furia_2': (557 + var(), 225 + var()),
    'pocao_de_furia_3': (633 + var(), 167 + var()),
    'pocao_de_furia_4': (430 + var(), 211 + var()),
    'pocao_de_furia_5': (508 + var(), 161 + var()),
    'arrastar_cima': (441, 37),
    'arrastar_baixo': (441, 323),
}
