"""Conversão das coordenadas de config/constants.py (espaço da janela do
emulador onde foram calibradas) pro espaço do device Android (Waydroid).

POR QUE ISSO EXISTE: as constantes em config/constants.py foram calibradas
numa janela de emulador de ~900x500. O device Waydroid aqui reporta
1366x739 (`adb shell wm size`). As duas telas têm aspecto diferente
(1.80 vs 1.85), então o Android não só escala a UI — ele RE-DIAGRAMA um
pouco. Isso significa que uma transformação afim é uma APROXIMAÇÃO, não
uma conversão exata.

O ajuste padrão abaixo veio de mínimos quadrados sobre 3 pontos que foram
verificados ao vivo em 2026-08-19/20 (o botão foi tocado e a tela reagiu
como esperado):

    'atacar'    (45, 473)  -> (85, 655)    Attack! na vila
    'encontrar' (120, 380) -> (223, 548)   Find a Match
    'voltar'    (442, 449) -> (683, 632)   Return Home

NÃO CONFIE NESSE PADRÃO SEM VERIFICAR. Rode `python3 -m utils.coord_map
--verificar` pra gerar um screenshot com todos os pontos mapeados
desenhados por cima: é muito mais barato conferir visualmente do que
descobrir no meio de um ataque que um toque caiu no lugar errado. Pontos
que estiverem fora do alvo devem ser corrigidos individualmente em
OVERRIDES_DEVICE (que tem precedência sobre a transformação).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_PATH = Path(os.environ.get(
    "COC_COORD_MAP", Path.home() / ".local/share/coc-digital-twin/coord_map.json"))

# Ajuste afim padrão: device = escala * host + offset (ver docstring).
DEFAULT_TRANSFORM = {"sx": 1.483, "ox": 30.3, "sy": 1.165, "oy": 106.1}

# Coordenadas em espaço de DEVICE que substituem o resultado da
# transformação. Use pra corrigir pontos que a afim erra (ela é aproximada).
# Os 3 abaixo são medidos, não calculados — por isso entram aqui.
OVERRIDES_DEVICE: dict[str, tuple[int, int]] = {
    "atacar": (85, 655),
    "encontrar": (223, 548),
    "voltar": (683, 632),
    # 'attack_army' NÃO existe em config/constants.BOTOES (bug antigo: o
    # clique em attack_utils.procurar_partida() falha silencioso hoje).
    # Aqui ele passa a existir, com a posição medida ao vivo.
    "attack_army": (1200, 667),
}


def carregar_transform() -> dict:
    """Transformação salva em disco, ou o padrão. Salvar permite refinar a
    calibração sem editar código."""
    if CONFIG_PATH.exists():
        try:
            dados = json.loads(CONFIG_PATH.read_text())
            return {**DEFAULT_TRANSFORM, **dados.get("transform", {})}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_TRANSFORM)


def carregar_overrides() -> dict[str, tuple[int, int]]:
    overrides = dict(OVERRIDES_DEVICE)
    if CONFIG_PATH.exists():
        try:
            dados = json.loads(CONFIG_PATH.read_text())
            for nome, xy in dados.get("overrides", {}).items():
                overrides[nome] = tuple(xy)
        except (json.JSONDecodeError, OSError):
            pass
    return overrides


def salvar(transform: dict | None = None, overrides: dict | None = None) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    atual = {}
    if CONFIG_PATH.exists():
        try:
            atual = json.loads(CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            atual = {}
    if transform is not None:
        atual["transform"] = transform
    if overrides is not None:
        atual.setdefault("overrides", {}).update(
            {k: list(v) for k, v in overrides.items()})
    CONFIG_PATH.write_text(json.dumps(atual, indent=2))
    print(f"[coord_map] salvo em {CONFIG_PATH}")


def host_para_device(x: float, y: float, transform: dict | None = None) -> tuple[int, int]:
    t = transform or carregar_transform()
    return (int(round(t["sx"] * x + t["ox"])), int(round(t["sy"] * y + t["oy"])))


def resolver_botao(nome: str, xy_host: tuple[int, int]) -> tuple[int, int]:
    """Posição em device pra um botão nomeado: override medido se houver,
    senão a transformação afim aplicada na coordenada original."""
    overrides = carregar_overrides()
    if nome in overrides:
        return overrides[nome]
    return host_para_device(*xy_host)


def ajustar_transform(pares: list[tuple[tuple[float, float], tuple[float, float]]]) -> dict:
    """Mínimos quadrados de (host -> device) em x e y independentes.
    `pares` = [((hx,hy),(dx,dy)), ...]. Precisa de >=2 pares com x
    distintos e >=2 com y distintos."""
    hx = [p[0][0] for p in pares]
    hy = [p[0][1] for p in pares]
    dx = [p[1][0] for p in pares]
    dy = [p[1][1] for p in pares]

    def fit(h, d):
        n = len(h)
        mh, md = sum(h) / n, sum(d) / n
        shh = sum((v - mh) ** 2 for v in h)
        shd = sum((h[i] - mh) * (d[i] - md) for i in range(n))
        if shh == 0:
            raise ValueError("pontos sem variação nesse eixo — não dá pra ajustar")
        s = shd / shh
        return s, md - s * mh

    sx, ox = fit(hx, dx)
    sy, oy = fit(hy, dy)
    return {"sx": round(sx, 4), "ox": round(ox, 2), "sy": round(sy, 4), "oy": round(oy, 2)}


def _verificar() -> None:
    """Desenha todos os pontos mapeados num screenshot real pra conferência
    visual. Verde = override medido, vermelho = derivado da afim (suspeito
    até prova em contrário)."""
    from PIL import ImageDraw
    from config.constants import BOTOES, CANTOS
    from utils.adb_io import screenshot

    img = screenshot().convert("RGB")
    draw = ImageDraw.Draw(img)
    overrides = carregar_overrides()
    t = carregar_transform()

    pontos = {f"B:{k}": v for k, v in BOTOES.items()}
    pontos.update({f"C:{k}": v for k, v in CANTOS.items()})

    for nome, xy_host in pontos.items():
        chave = nome.split(":", 1)[1]
        medido = chave in overrides
        x, y = overrides[chave] if medido else host_para_device(*xy_host, transform=t)
        cor = (0, 220, 0) if medido else (255, 40, 40)
        r = 7
        draw.ellipse([x - r, y - r, x + r, y + r], outline=cor, width=3)
        draw.text((x + r + 2, y - 6), chave, fill=cor)

    for nome, xy in overrides.items():
        if nome not in BOTOES and nome not in CANTOS:
            x, y = xy
            draw.ellipse([x - 7, y - 7, x + 7, y + 7], outline=(0, 220, 0), width=3)
            draw.text((x + 9, y - 6), nome, fill=(0, 220, 0))

    saida = Path.home() / ".local/share/coc-digital-twin/coord_map_check.png"
    saida.parent.mkdir(parents=True, exist_ok=True)
    img.save(saida)
    print(f"[coord_map] transform={t}")
    print(f"[coord_map] verde=medido ({len(overrides)}), vermelho=derivado da afim")
    print(f"[coord_map] imagem: {saida}")


if __name__ == "__main__":
    import sys
    if "--verificar" in sys.argv:
        _verificar()
    else:
        print("uso: python3 -m utils.coord_map --verificar")
