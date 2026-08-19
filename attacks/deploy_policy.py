# attacks/deploy_policy.py
"""Conversão das ações de ataque legadas (attacks/home_base.py, attacks/attack_utils.py)
para o espaço de ações PAMDP híbrido do Gymnasium (Camada 4 do digital_twin.md).

Cada função `build_*_sequence` reconstrói, em ordem, a lógica de posicionamento de
tropas de uma das rotinas de ataque legadas como uma lista de `DeployAction`
— tupla (tipo discreto de tropa, coordenadas normalizadas (X, Y) em [0.0, 1.0]) —
compatível com `ClashDigitalTwinEnv.action_space`:
    spaces.Dict({"type": spaces.Discrete(10), "coords": spaces.Box(0.0, 1.0, shape=(2,))})

Este módulo não aciona nenhum input real (mouse/teclado): ele apenas traduz as
coordenadas de tela fixas em `config/constants.py` (BOTOES/CANTOS/RETAS) para o
espaço normalizado do ambiente, servindo de política com script (baseline/expert
trajectories) para o agente H-PPO ou para comparação com a política aprendida.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from config.constants import BOTOES, CANTOS, RETAS

# Réplicas puras de utils.mouse_actions.gerar_pontos_na_reta/gerar_pontos_nao_aleatorios.
# Não importamos utils.mouse_actions aqui de propósito: esse módulo aplica o patch
# X11/Mutter e importa pyautogui só de ser carregado, o que arrastaria uma
# dependência de display gráfico para dentro de um módulo de política que deve
# rodar sem cabeça (headless) durante o treinamento de RL.


def _gerar_pontos_na_reta(xi, yi, xf, yf, num_pontos=8):
    import random

    pontos = []
    for _ in range(num_pontos):
        fator = random.uniform(0, 1)
        x = int(round(xi + (xf - xi) * fator))
        y = int(round(yi + (yf - yi) * fator))
        pontos.append((x, y))
    return pontos


def _gerar_pontos_nao_aleatorios(xi, yi, xf, yf, num_pontos=3):
    pontos = []
    for i in range(num_pontos):
        fator = i / (num_pontos - 1)
        x = int(round(xi + (xf - xi) * fator))
        y = int(round(yi + (yf - yi) * fator))
        pontos.append((x, y))
    return pontos


# Limites de tela assumidos para normalizar as coordenadas fixas de config/constants.py
# (calibradas na janela do emulador original) para [0.0, 1.0]^2. Ajustar caso a
# resolução de captura mude.
SCREEN_WIDTH = 900.0
SCREEN_HEIGHT = 500.0

# O Discrete(10) da Camada 4 reserva os índices 0..8 para os slots de tropa
# selecionar_tropa_1..selecionar_tropa_9 (type_id = slot - 1) e o índice 9 para
# heróis/poções, que na lógica legada não têm um "tipo" próprio — são selecionados
# pelo botão dinâmico armazenado em army[<heroi>]['sel'].
MAX_TROOP_SLOTS = 9
HERO_TYPE_ID = 9


@dataclass(frozen=True)
class DeployAction:
    """Uma ação PAMDP única: tipo discreto + coordenadas normalizadas contínuas."""

    type: int
    coords: np.ndarray
    wait_after: float = 0.0

    def as_gym_action(self) -> dict:
        return {"type": self.type, "coords": self.coords}


def pixel_to_normalized(point: tuple[float, float]) -> np.ndarray:
    """Converte um ponto em pixels de config/constants.py para [0.0, 1.0]^2."""
    x, y = point
    nx = min(max(x / SCREEN_WIDTH, 0.0), 1.0)
    ny = min(max(y / SCREEN_HEIGHT, 0.0), 1.0)
    return np.array([nx, ny], dtype=np.float32)


def troop_slot_type(slot_index: int) -> int:
    """Mapeia o índice 1-based de selecionar_tropa_N para o type_id 0-based do Discrete(10)."""
    return min(max(slot_index - 1, 0), MAX_TROOP_SLOTS - 1)


def _deploy(type_id: int, point: tuple[float, float], wait_after: float = 0.0) -> DeployAction:
    return DeployAction(type=type_id, coords=pixel_to_normalized(point), wait_after=wait_after)


def build_dragon_sequence(army: dict) -> list[DeployAction]:
    """Porta attacks.home_base.ataque_dragao (afunilamento + tropa principal + poções/heróis)."""
    actions: list[DeployAction] = []
    last_troop_type = troop_slot_type(int(army["troops"]["quantidade"]))

    if army["rei"]["ativo"]:
        actions.append(_deploy(HERO_TYPE_ID, BOTOES["posicao_dragao_1"]))
    if army["siege_machine"]["ativo"]:
        actions.append(_deploy(HERO_TYPE_ID, BOTOES["posicao_dragao_1"]))

    actions.append(_deploy(last_troop_type, BOTOES["posicao_dragao_1"]))
    actions.append(_deploy(last_troop_type, BOTOES["posicao_dragao_2"], wait_after=0.3))

    for key in ("posicao_dragao_13", "posicao_dragao_14", "posicao_dragao_15"):
        actions.append(_deploy(last_troop_type, BOTOES[key]))
    if army["campea"]["ativo"]:
        actions.append(_deploy(HERO_TYPE_ID, BOTOES["posicao_dragao_15"], wait_after=0.3))

    corpo_principal = (
        "posicao_dragao_4", "posicao_dragao_5", "posicao_dragao_6", "posicao_dragao_7",
        "posicao_dragao_8", "posicao_dragao_9", "posicao_dragao_10", "posicao_dragao_10",
        "posicao_dragao_11", "posicao_dragao_12", "posicao_dragao_6",
    )
    for key in corpo_principal:
        actions.append(_deploy(last_troop_type, BOTOES[key]))

    if army["guardiao"]["ativo"]:
        actions.append(_deploy(HERO_TYPE_ID, BOTOES["posicao_dragao_6"]))
    if army["rainha"]["ativo"]:
        actions.append(_deploy(HERO_TYPE_ID, BOTOES["posicao_dragao_6"], wait_after=8.0))

    # Poções de fúria (não têm posição própria no mapa; ancoradas no ponto de deploy vigente).
    for key in ("pocao_de_furia_1", "pocao_de_furia_2", "pocao_de_furia_3"):
        actions.append(_deploy(HERO_TYPE_ID, BOTOES[key]))

    if not army["rei"]["ativo"]:
        actions.append(_deploy(troop_slot_type(2), BOTOES["posicao_dragao_10"], wait_after=12.0))

    for key in ("pocao_de_furia_4", "pocao_de_furia_5"):
        actions.append(_deploy(HERO_TYPE_ID, BOTOES[key], wait_after=2.0))

    return actions


def build_goblin_sequence(army: dict) -> list[DeployAction]:
    """Porta attacks.home_base.ataque_goblin (heróis nos cantos + tropas ao longo das RETAS)."""
    actions: list[DeployAction] = []
    last_troop_type = troop_slot_type(int(army["troops"]["quantidade"]))

    for heroi in ("rei", "campea", "guardiao", "rainha"):
        if army[heroi]["ativo"]:
            actions.append(_deploy(HERO_TYPE_ID, CANTOS["C"]))

    # O código legado referencia 'selecionar_tropa_0', que não existe em BOTOES
    # (bug pré-existente: o clique falha silenciosamente). Interpretado aqui como
    # a intenção original de posicionar o primeiro slot de tropa (type_id 0).
    actions.append(_deploy(troop_slot_type(1), CANTOS["C"]))
    actions.append(_deploy(troop_slot_type(3), CANTOS["C"]))

    for i, reta in enumerate(RETAS):
        if i == 2:
            for ponto in ((440, 200), (440, 260), (440, 320)):
                actions.append(_deploy(HERO_TYPE_ID, ponto))
        if i == 3:
            for heroi in ("rei", "campea", "guardiao", "rainha"):
                if army[heroi]["ativo"]:
                    actions.append(_deploy(HERO_TYPE_ID, CANTOS["C"]))
            for ponto in ((380, 310), (500, 310)):
                actions.append(_deploy(HERO_TYPE_ID, ponto))

        xi, yi = RETAS[reta][0]
        xf, yf = RETAS[reta][1]
        for ponto in _gerar_pontos_na_reta(xi, yi, xf, yf):
            actions.append(_deploy(last_troop_type, ponto))

    return actions


def build_rapid_sequence(army: dict, tropas_por_reta: int | None = None) -> list[DeployAction]:
    """Porta attacks.home_base.ataque_rapido (heróis nos 4 cantos + tropas distribuídas nas RETAS)."""
    actions: list[DeployAction] = []

    herois = ("rei", "rainha", "guardiao", "campea")
    cantos_herois = ("C", "B", "EC", "DC")
    herois_ativos = [h for h in herois if army.get(h, {}).get("ativo")]

    for i, heroi in enumerate(herois_ativos):
        canto = cantos_herois[i % 4]
        actions.append(_deploy(HERO_TYPE_ID, CANTOS[canto]))

    first_troop_type = troop_slot_type(1)
    tropas_totais = army.get("troops", {}).get("quantidade", 40)
    n_por_reta = tropas_por_reta or (tropas_totais // 4)
    # gerar_pontos_nao_aleatorios divide por (num_pontos - 1); protegido para o caso
    # degenerado de menos de 2 tropas por reta.
    n_por_reta = max(n_por_reta, 2)

    for reta in RETAS:
        xi, yi = RETAS[reta][0]
        xf, yf = RETAS[reta][1]
        for ponto in _gerar_pontos_nao_aleatorios(xi, yi, xf, yf, n_por_reta):
            actions.append(_deploy(first_troop_type, ponto))

    return actions


def build_builder_base_sequence() -> list[DeployAction]:
    """Porta attacks.attack_utils.posicionar_tropa (usada por ganhar_uma/ganhar_duas)."""
    return [_deploy(troop_slot_type(i), (444, 360)) for i in range(1, 9)]


def sequence_to_gym_actions(sequence: Iterable[DeployAction]) -> list[dict]:
    """Achata uma sequência de DeployAction para o formato aceito por env.step()."""
    return [step.as_gym_action() for step in sequence]
