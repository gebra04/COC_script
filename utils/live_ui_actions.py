"""Sequências de toque pra ações de UI do Clash of Clans ao vivo (Waydroid),
mapeadas em 2026-08-19: buscar ataque, iniciar batalha, voltar pra vila, e
confirmar um upgrade já selecionado (via utils.upgrade_picker.pick_upgrade).

Coordenadas fixas (Attack!/Find a Match!/Attack!(2)/Return Home) validadas
ao vivo em screenshots 1366x739 — são elementos de menu fixos, não mudam de
posição. Já "Upgrade"/"Confirm" dentro do painel de item selecionado MUDAM
de posição dependendo do tipo de prédio (muro tem um layout com botões
extras "Select Row"/"Upgrade More" que empurram o botão real de posição) —
por isso esses dois são localizados por OCR (busca o texto do botão na
tela), não por coordenada fixa. Ver a sessão de 2026-08-19 pra contexto de
por que coordenada fixa no mapa isométrico foi descartada (muito frágil).
"""
from __future__ import annotations

import time

import pytesseract
from PIL import Image

from utils.adb_io import screenshot as _screenshot, tap as _tap_xy

# --- sequencia de ataque (posicoes fixas, elementos de menu) ---
ATTACK_BUTTON = (85, 655)          # "Attack!" na vila
FIND_MATCH_BUTTON = (223, 548)     # "Find a Match" na aba Multiplayer
ATTACK2_BUTTON = (1200, 667)       # "Attack!" verde na pre-visualizacao do exercito
RETURN_HOME_BUTTON = (683, 632)    # "Return Home" no resumo pos-ataque


def _tap(pos: tuple[int, int]) -> None:
    _tap_xy(*pos)


def find_text_button(label: str, region: tuple[int, int, int, int] | None = None,
                      screenshot: Image.Image | None = None) -> tuple[int, int] | None:
    """Acha um botao pelo texto (OCR), devolve o centro em coordenada de tela
    real, ou None se nao achou. `region` limita a busca (recomendado — evita
    casar texto de outro lugar da tela) a (x0,y0,x1,y1) do screenshot cheio."""
    img = screenshot if screenshot is not None else _screenshot()
    crop = img if region is None else img.crop(region)
    x0, y0 = (0, 0) if region is None else (region[0], region[1])

    scale = 2
    big = crop.resize((crop.width * scale, crop.height * scale))
    data = pytesseract.image_to_data(big, config="--psm 11", output_type=pytesseract.Output.DICT)

    label_low = label.lower()
    for i, txt in enumerate(data["text"]):
        cleaned = "".join(c for c in txt if c.isalnum()).lower()
        if cleaned == label_low:
            left, top = data["left"][i], data["top"][i]
            w, h = data["width"][i], data["height"][i]
            cx = x0 + (left + w / 2) / scale
            cy = y0 + (top + h / 2) / scale
            return (int(cx), int(cy))
    return None


def start_attack_search(wait_s: float = 1.5) -> None:
    """Attack! (vila) -> Find a Match! (aba Multiplayer). Para na tela de
    pre-visualizacao do exercito (antes de gastar a busca de fato)."""
    _tap(ATTACK_BUTTON)
    time.sleep(wait_s)
    _tap(FIND_MATCH_BUTTON)
    time.sleep(wait_s)


def confirm_attack(wait_s: float = 2.0) -> None:
    """Attack!(2) — inicia a busca de oponente de verdade (gasta a busca)."""
    _tap(ATTACK2_BUTTON)
    time.sleep(wait_s)


def return_home(wait_s: float = 1.5) -> None:
    """Return Home — sai do resumo pos-ataque, volta pra vila."""
    _tap(RETURN_HOME_BUTTON)
    time.sleep(wait_s)


# --- confirmar upgrade ja selecionado (apos upgrade_picker.pick_upgrade) ---
# Regiao onde o painel de item selecionado aparece (parte inferior da tela,
# acima da barra de icones). Restringe a busca de OCR pra nao casar "Upgrade"
# de outro elemento da tela (ex.: o proprio botao "Upgrade" do popup de
# sugestoes, que fica mais acima).
_ITEM_PANEL_REGION = (400, 520, 1100, 650)
_CONFIRM_DIALOG_REGION = (600, 580, 1250, 700)


def confirm_selected_upgrade(spend_gems_if_needed: bool = False) -> dict:
    """Toca 'Upgrade' no painel do item ja selecionado (por pick_upgrade),
    depois 'Confirm' no dialogo que abre. GASTA RECURSO DE VERDADE — só
    chamar quando a escolha ja foi validada. Retorna {"ok": bool, "step":
    onde parou} pra diagnostico se algum botao nao for achado.

    LIMITACAO CONHECIDA (2026-08-19): alguns itens (ex.: muro em nivel alto)
    mostram DOIS botoes "Upgrade" lado a lado — um pagando em ouro, outro em
    elixir negro. find_text_button pega o primeiro que o tesseract lista
    (nao necessariamente o da esquerda/ouro) — nao ha desambiguacao por
    moeda ainda. Verificado ao vivo: pegou o de elixir negro por acaso.
    Se isso importar (custo errado), resolver antes de automatizar de vez."""
    shot = _screenshot()
    pos = find_text_button("Upgrade", region=_ITEM_PANEL_REGION, screenshot=shot)
    if pos is None:
        return {"ok": False, "step": "upgrade_button_not_found"}
    _tap(pos)
    time.sleep(1.2)

    shot2 = _screenshot()
    pos2 = find_text_button("Confirm", region=_CONFIRM_DIALOG_REGION, screenshot=shot2)
    if pos2 is None:
        return {"ok": False, "step": "confirm_button_not_found"}
    _tap(pos2)
    time.sleep(1.0)
    return {"ok": True, "step": "confirmed"}


if __name__ == "__main__":
    import sys
    if "--find-upgrade" in sys.argv:
        print(find_text_button("Upgrade", region=_ITEM_PANEL_REGION))
    elif "--find-confirm" in sys.argv:
        print(find_text_button("Confirm", region=_CONFIRM_DIALOG_REGION))
