"""Leitura por OCR de contadores fixos do HUD do Clash of Clans (Waydroid).

Usado só pro que a leitura de memória não cobre de forma prática — ex.: o
contador de construtores livres (o objeto Building não guarda esse estado,
e a busca por timestamp de conclusão na memória não bateu, ver pesquisa/06
e a sessão de 2026-08-19). Pra números exibidos na tela (ouro, elixir, %) a
leitura de memória em mem_reader.py é preferível — mais rápida e não tem
ambiguidade de fonte/escala. Ver a conversa que decidiu esse tradeoff.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageOps
import pytesseract

from utils.adb_io import screenshot as capture_screenshot

# Recortes fixos, em screenshots 1366x739 tirados via
# `adb exec-out screencap -p` neste dispositivo. Se a resolução do device
# mudar, recalibrar (ver conversa de 2026-08-19).
BUILDER_BADGE_BOX = (672, 24, 732, 60)
GOLD_BOX = (1110, 25, 1290, 58)
ELIXIR_BOX = (1110, 92, 1290, 125)
DARK_ELIXIR_BOX = (1110, 158, 1290, 195)


def _ocr_white_text_number(crop: Image.Image) -> int:
    """OCR pra números brancos com contorno escuro sobre fundo colorido
    (barras de recurso do HUD) — threshold por brilho simples falha aqui
    porque o fundo é claro/texturizado; mascara por "pixel bem branco" (as
    3 componentes RGB altas) isola só o texto de forma confiavel.

    LIMITACAO CONHECIDA (2026-08-19): quando dois dígitos "1" ficam
    adjacentes (ex.: "115465"), o tesseract às vezes perde um deles
    ("15465"), reproduzível em todo psm/escala testado nessa fonte.
    Tentativa de segmentar por coluna de pixel e ler 1 caractere por vez
    piorou (dígitos dentro do mesmo grupo, ex. "346", também colam, e
    psm 10 num grupo de 3 caracteres lê pior que a string inteira) — então
    foi revertida. Isso só importa pra semear a recalibração do wallet
    (mem_reader.py --wallet já rejeita leituras implausíveis e cai pro
    heap inteiro se a semente errar o alvo)."""
    crop = crop.resize((crop.width * 4, crop.height * 4), Image.LANCZOS)
    arr = np.array(crop.convert("RGB"))
    white_mask = (arr[:, :, 0] > 170) & (arr[:, :, 1] > 170) & (arr[:, :, 2] > 170)
    bw = np.where(white_mask, 0, 255).astype("uint8")
    txt = pytesseract.image_to_string(
        Image.fromarray(bw), config="--psm 7 -c tessedit_char_whitelist=0123456789"
    ).strip()
    if not txt:
        raise ValueError("OCR nao leu nenhum digito")
    return int(txt)


def read_resources(screenshot: Image.Image | None = None) -> tuple[int, int, int]:
    """Retorna (gold, elixir, dark_elixir) lidos das barras do HUD. Usado só
    pra semear a recalibração do wallet em mem_reader.py (--wallet) quando
    o endereço cacheado realocou — não pra leitura contínua (memória é mais
    rápida/confiável pra isso, ver conversa de 2026-08-19)."""
    img = screenshot if screenshot is not None else capture_screenshot()
    gold = _ocr_white_text_number(img.crop(GOLD_BOX))
    elixir = _ocr_white_text_number(img.crop(ELIXIR_BOX))
    dark = _ocr_white_text_number(img.crop(DARK_ELIXIR_BOX))
    return gold, elixir, dark


def _ocr_digits(crop: Image.Image, whitelist: str = "0123456789/") -> str:
    crop = crop.resize((crop.width * 4, crop.height * 4))
    gray = crop.convert("L")
    gray = ImageOps.autocontrast(gray)
    bw = gray.point(lambda p: 255 if p > 150 else 0)
    txt = pytesseract.image_to_string(
        bw, config=f"--psm 7 -c tessedit_char_whitelist={whitelist}"
    )
    return txt.strip()


def read_builders(screenshot: Image.Image | None = None) -> tuple[int, int]:
    """Retorna (construtores_livres, construtores_totais) lidos do badge do HUD.

    Levanta ValueError se o texto lido não bater no formato "N/M" esperado
    (ex.: badge fora da tela, jogo não está na visão da vila)."""
    img = screenshot if screenshot is not None else capture_screenshot()
    crop = img.crop(BUILDER_BADGE_BOX)
    txt = _ocr_digits(crop)
    if "/" not in txt:
        raise ValueError(f"OCR do badge de construtores nao reconhecido: {txt!r}")
    free_s, total_s = txt.split("/", 1)
    return int(free_s), int(total_s)


if __name__ == "__main__":
    shot = capture_screenshot()
    free, total = read_builders(shot)
    print(f"construtores livres: {free}/{total}")
    gold, elixir, dark = read_resources(shot)
    print(f"recursos: gold={gold} elixir={elixir} dark={dark}")
