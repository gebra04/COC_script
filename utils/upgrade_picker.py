"""Escolhe qual upgrade colocar num construtor livre, no popup de sugestões
que abre ao tocar no badge de construtores no HUD.

Regra (definida em 2026-08-19): muro tem prioridade se aparecer em qualquer
lugar da lista (rola pra baixo procurando); senão, usa a primeira sugestão
("Suggested upgrades:", primeiro item). Muro nunca aparece nessa lista
quando já tem um muro selecionável — na prática, "aparecer na lista" só
acontece se NÃO houver muro upgradeable perto do nível máximo atual (ver
nota abaixo); mesmo assim mantemos a busca porque a UI do jogo pode listar
muro em builds diferentes.

Não usamos coordenada de toque no mapa isométrico pra selecionar prédio —
muito frágil (ver conversa de 2026-08-19, várias trombadas com elementos
errados). Tudo aqui opera só dentro do popup fixo em tela.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import pytesseract
from PIL import Image

from utils.adb_io import screenshot as _screenshot, tap as _tap, swipe as _swipe_raw

BUILDER_BADGE_POS = (700, 42)
POPUP_NAME_COL = (528, 100, 760, 560)  # coluna de nomes dos itens, sem preço
TAP_X_IN_ROW = 630  # x pra tocar em cima do nome do item (dentro do popup)
MAX_SCROLLS = 30
SWIPE_DOWN = (700, 480, 700, 200, 200)  # x1 y1 x2 y2 duration_ms — rola conteudo pra baixo
SWIPE_UP = (700, 200, 700, 480, 200)    # inverso — volta ao topo


def _swipe(down: bool = True) -> None:
    _swipe_raw(*(SWIPE_DOWN if down else SWIPE_UP))


@dataclass
class Row:
    text: str
    y_screen: int  # coordenada real de tela (ja convertida do crop 2x)


def _read_rows(img: Image.Image) -> list[Row]:
    """OCR da coluna de nomes do popup, agrupado por linha. Usa a propria
    hierarquia (block_num, par_num, line_num) que o tesseract calcula pra
    juntar palavras da mesma linha — bucket manual por posicao Y (tentativa
    anterior) errava quando duas linhas ficavam proximas, juntando um
    fragmento (ex.: badge '3' do Builder's Apprentice) como se fosse item."""
    x0, y0, x1, y1 = POPUP_NAME_COL
    crop = img.crop((x0, y0, x1, y1))
    crop = crop.resize((crop.width * 2, crop.height * 2))
    data = pytesseract.image_to_data(crop, config="--psm 6", output_type=pytesseract.Output.DICT)

    lines: dict[tuple[int, int, int], list[tuple[int, int, str]]] = {}
    for i, txt in enumerate(data["text"]):
        if not txt.strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append((data["left"][i], data["top"][i], txt))

    rows = []
    for key, words in sorted(lines.items(), key=lambda kv: min(t for _, t, _ in kv[1])):
        words.sort()  # por 'left', ordem de leitura da linha
        text = " ".join(w for _, _, w in words)
        avg_top = sum(t for _, t, _ in words) / len(words)
        y_screen = y0 + int(avg_top / 2) + 12  # +12 ~ centro da linha
        if any(c.isalpha() for c in text):  # descarta fragmentos so-numero (ex.: badge)
            rows.append(Row(text=text, y_screen=y_screen))
    return rows


# Rotulos/cabecalhos do popup que NAO sao itens de upgrade (ver 2026-08-19:
# 'Available!' e um banner sobre o Builder's Apprentice, clicavel, que foi
# pego por engano como se fosse a primeira sugestao).
_HEADER_LABELS = ("available", "suggested upgrades", "other upgrades")

# Herois nunca devem ser escolhidos automaticamente como "primeira sugestao"
# (regra do usuario, 2026-08-19: heroi fora de combate por horas/dias e pior
# que builder ocioso por um tempo). Upgrade de heroi usa outro fluxo (Barrack
# Heroes) e nao consome um construtor normal mesmo — mas ainda assim pode
# aparecer no topo da lista de sugestoes, entao filtramos explicitamente.
_HERO_NAMES = ("barbarian king", "archer queen", "grand warden",
               "royal champion", "minion prince")


def _is_header(text: str) -> bool:
    low = text.lower()
    return any(h in low for h in _HEADER_LABELS)


def _is_hero(text: str) -> bool:
    low = text.lower()
    return any(h in low for h in _HERO_NAMES)


def pick_upgrade(max_scrolls: int = MAX_SCROLLS, dry_run: bool = False, debug: bool = False) -> dict:
    """Abre o popup de sugestoes, procura 'Wall' rolando a lista; se achar,
    toca nele. Se nao achar ate o fim da lista, volta ao topo e toca na
    primeira sugestao (pulando cabecalhos tipo 'Available!'). Retorna
    {"picked": nome_da_linha, "via": "wall"|"first_suggestion"} ou
    {"picked": None} se nada pode ser lido (popup nao abriu etc).

    dry_run=True: faz tudo (abre, rola, le) mas NAO toca no item final —
    só reporta o que teria escolhido. Usar pra validar antes de deixar
    tocar de verdade numa conta real."""
    _tap(*BUILDER_BADGE_POS)
    time.sleep(1.0)

    first_shot = _screenshot()
    first_rows = [r for r in _read_rows(first_shot) if not _is_header(r.text) and not _is_hero(r.text)]
    first_suggestion = first_rows[0] if first_rows else None
    if debug:
        print(f"[scroll 0] rows={[r.text for r in _read_rows(first_shot)]}")

    prev_signature = None
    scrolls_done = 0
    for scroll_i in range(max_scrolls):
        shot = first_shot if scroll_i == 0 else _screenshot()
        all_rows = _read_rows(shot)
        if debug and scroll_i > 0:
            print(f"[scroll {scroll_i}] rows={[r.text for r in all_rows]}")
        signature = tuple(r.text for r in all_rows)
        if signature == prev_signature:
            break  # rolagem nao mudou nada -> fim da lista
        prev_signature = signature

        for r in all_rows:
            if _is_header(r.text):
                continue
            if "wall" in r.text.lower():
                if not dry_run:
                    _tap(TAP_X_IN_ROW, r.y_screen)
                return {"picked": r.text, "via": "wall", "scroll": scroll_i}

        _swipe(down=True)
        scrolls_done += 1
        time.sleep(0.5)

    if first_suggestion is not None:
        if not dry_run:
            # volta ao topo revertendo exatamente os swipes que fizemos (mais
            # confiavel que fechar/reabrir o popup — um toggle as cegas pode
            # sair sincronizado se o popup ja tiver fechado por outro motivo
            # externo, ex.: desconexao por inatividade, visto ao vivo em
            # 2026-08-19).
            for _ in range(scrolls_done):
                _swipe(down=False)
                time.sleep(0.3)
            shot = _screenshot()
            rows = [r for r in _read_rows(shot) if not _is_header(r.text) and not _is_hero(r.text)]
            if rows:
                _tap(TAP_X_IN_ROW, rows[0].y_screen)
                return {"picked": rows[0].text, "via": "first_suggestion"}
        return {"picked": first_suggestion.text, "via": "first_suggestion"}

    return {"picked": None}


if __name__ == "__main__":
    import sys
    result = pick_upgrade(dry_run="--dry-run" in sys.argv, debug="--debug" in sys.argv)
    print(result)
