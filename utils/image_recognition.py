# utils/image_recognition.py

"""Busca de template na tela. Duas rotas, conforme o backend de input ativo:

  - ADB: screenshot via adb + template matching em numpy (sem OpenCV).
  - PyAutoGUI: comportamento antigo (locateCenterOnScreen).

NOTA (2026-08-20): a rota PyAutoGUI provavelmente já estava quebrada neste
setup — `confidence=` exige OpenCV, e cv2 não está instalado no venv. Isso
faz `clicar_por_imagem` cair sempre no except e retornar False, o que
explica `coletar_carrinho()` não funcionar. A rota ADB abaixo não depende
de OpenCV.
"""

import os

import numpy as np
from PIL import Image

from utils.input_backend import get_backend

CONFIANCA_PADRAO = 0.6


def _match_template(tela: Image.Image, template: Image.Image) -> tuple[float, tuple[int, int]]:
    """Correlação cruzada normalizada por força bruta, em escala de cinza.
    Devolve (melhor_score, (cx, cy)). Sem OpenCV: usa numpy stride tricks
    pra montar as janelas de uma vez. Templates de UI são pequenos, então
    o custo é aceitável (~dezenas de ms)."""
    t = np.asarray(template.convert("L"), dtype=np.float32)
    s = np.asarray(tela.convert("L"), dtype=np.float32)
    th, tw = t.shape
    sh, sw = s.shape
    if th > sh or tw > sw:
        return 0.0, (0, 0)

    t_norm = t - t.mean()
    t_denom = np.sqrt((t_norm ** 2).sum())
    if t_denom == 0:
        return 0.0, (0, 0)

    janelas = np.lib.stride_tricks.sliding_window_view(s, (th, tw))
    # média/desvio por janela, vetorizado
    medias = janelas.mean(axis=(2, 3), keepdims=True)
    centradas = janelas - medias
    denoms = np.sqrt((centradas ** 2).sum(axis=(2, 3)))
    numers = (centradas * t_norm).sum(axis=(2, 3))
    with np.errstate(divide="ignore", invalid="ignore"):
        scores = np.where(denoms > 0, numers / (denoms * t_denom), 0.0)

    idx = np.unravel_index(np.argmax(scores), scores.shape)
    melhor = float(scores[idx])
    cy, cx = int(idx[0] + th // 2), int(idx[1] + tw // 2)
    return melhor, (cx, cy)


def _clicar_por_imagem_adb(pasta: str, confianca: float) -> bool:
    from utils.adb_io import screenshot

    tela = screenshot()
    for nome in sorted(os.listdir(pasta)):
        if not nome.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            continue
        try:
            template = Image.open(os.path.join(pasta, nome))
        except OSError as e:
            print(f"Erro ao abrir '{nome}': {e}")
            continue
        score, (cx, cy) = _match_template(tela, template)
        if score >= confianca:
            get_backend().click(cx, cy)
            print(f"Clicou na imagem '{nome}' em ({cx}, {cy}) [score={score:.2f}].")
            return True
        print(f"Imagem '{nome}' não bateu (score={score:.2f} < {confianca}).")
    print("Nenhuma das imagens na pasta foi encontrada.")
    return False


def _clicar_por_imagem_pyautogui(pasta: str, confianca: float) -> bool:
    import pyautogui

    for nome in sorted(os.listdir(pasta)):
        if not nome.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            continue
        caminho = os.path.join(pasta, nome)
        try:
            local = pyautogui.locateCenterOnScreen(caminho, confidence=confianca)
            if local:
                pyautogui.click(local)
                print(f"Clicou na imagem '{nome}' em {local}.")
                return True
        except pyautogui.ImageNotFoundException:
            print(f"Imagem '{nome}' não encontrada na tela.")
        except Exception as e:
            print(f"Erro ao encontrar a imagem '{nome}': {e}")
    print("Nenhuma das imagens na pasta foi encontrada.")
    return False


def clicar_por_imagem(caminho_da_pasta, confianca=CONFIANCA_PADRAO):
    """Percorre uma pasta e tenta clicar na primeira imagem encontrada."""
    caminho_base = os.path.join(os.path.dirname(__file__), "..", "images")
    pasta = os.path.join(caminho_base, caminho_da_pasta)
    if not os.path.isdir(pasta):
        print(f"Erro: A pasta '{pasta}' não foi encontrada.")
        return False

    if get_backend().name == "adb":
        return _clicar_por_imagem_adb(pasta, confianca)
    return _clicar_por_imagem_pyautogui(pasta, confianca)
