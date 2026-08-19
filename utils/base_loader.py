"""Leitor de base inimiga para o Gêmeo Digital (Arquitetura B — leitor
externo passivo, ver `pesquisa/06`).

Um scout ÚNICO da base estática (defesas, muralhas, recursos, Town Hall)
alimenta o simulador offline (`utils.combat_sim`/`utils.attack_simulator`).
Diferente do antigo `utils.external_receiver` (lido a CADA FRAME durante o
combate ao vivo): essa arquitetura foi abandonada por decisão do usuário — o
combate agora é SIMULADO, não observado do jogo em tempo real, então só
precisamos da composição da base uma vez (ver `PROXIMOS_PASSOS.md`, Fase 1.5).

Só entidades ESTÁTICAS da base entram (Building/Wall/Obstacle/Trap):
`classe == "Troop"` é descartado mesmo que venha na leitura — o leitor
externo lê o que estiver na tela, e uma tropa em campo (própria ou de outro
jogador) não deve contaminar o estado inicial de uma base a ser simulada.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from utils.building_footprints import _load as _bf_load

DEFAULT_READER = os.path.expanduser("~/.local/share/coc-digital-twin/mem_reader.py")


def read_enemy_base(pid: str | int = "auto", reader_path: str = DEFAULT_READER,
                     python_bin: str = "/usr/bin/python3", timeout: float = 15.0) -> list[dict]:
    """Invoca `mem_reader.py --json` (via `sudo -n`, regra NOPASSWD dedicada)
    e devolve as entidades ESTÁTICAS da vila carregada (defesas, muralhas,
    recursos, TH...). Requer o Waydroid aberto com o CoC numa base carregada
    (própria em edição ou inimiga em scout/ataque ainda não iniciado)."""
    cmd = ["sudo", "-n", python_bin, reader_path, str(pid), "--json"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        raise RuntimeError(f"mem_reader --json falhou (rc={out.returncode}): {out.stderr.strip()}")
    try:
        raw = json.loads(out.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"saída do leitor não é JSON válido: {exc}") from exc
    return _filter_static(raw.get("entities", []))


def _filter_static(entities: list[dict]) -> list[dict]:
    return [e for e in entities if e.get("classe") != "Troop"]


def save_base(entities: list[dict], path: str | Path) -> None:
    """Persiste uma captura de base pra reuso offline (dev sem Waydroid,
    conjunto de regressão da Etapa 4 do PLANO_SIMULACAO.md)."""
    Path(path).write_text(json.dumps({"entities": entities}, indent=2, ensure_ascii=False))


def load_base(path: str | Path) -> list[dict]:
    """Carrega uma captura salva por `save_base` (ou o formato cru do
    `mem_reader.py --json`/`debug/sim_viewer.py --json`: `{"entities": [...]}`
    ou uma lista solta de entidades)."""
    raw = json.loads(Path(path).read_text())
    ents = raw.get("entities", raw) if isinstance(raw, dict) else raw
    return _filter_static(ents)


def base_report(entities: list[dict]) -> dict:
    """Resumo de sanidade de uma captura (mesmas heurísticas do
    `mem_reader.py scout_base`) — checar antes de usar em treino."""
    bf = _bf_load()
    n_buildings = sum(1 for e in entities if e.get("classe") == "Building")
    n_walls = sum(1 for e in entities if e.get("classe") == "Wall")
    th = next((e for e in entities if e.get("did") == 1000001), None)
    n_defenses = sum(1 for e in entities if bf.get(e.get("did"), (0, 0, "", ""))[3] == "Defense")
    n_resources = sum(1 for e in entities if bf.get(e.get("did"), (0, 0, "", ""))[3] == "Resource")
    return {
        "n_entities": len(entities),
        "n_buildings": n_buildings,
        "n_walls": n_walls,
        "n_defenses": n_defenses,
        "n_resources": n_resources,
        "th_level": (th["lvl"] if th else None),
        "th_pos": ((th["tx"], th["ty"]) if th else None),
        "has_town_hall": th is not None,
    }
