"""Loader das constantes de engine em `game_constants.json` (ver esse arquivo
pra fonte/versao/ressalvas). Expondo como modulo Python pra nao duplicar
`json.loads(...)` em cada consumidor (`combat_sim.py`, `attack_simulator.py`)."""

from __future__ import annotations

import json
from pathlib import Path

_RAW = json.loads(Path(__file__).with_name("game_constants.json").read_text())


def get(name: str):
    """Valor cru da constante `name` (ja desembrulhado do {"value":...})."""
    entry = _RAW[name]
    return entry["value"] if isinstance(entry, dict) and "value" in entry else entry


CHAR_VS_CHAR_RADIUS_FOR_ATTACKER = get("CHAR_VS_CHAR_RADIUS_FOR_ATTACKER")
CASTLE_DEFENDER_SEARCH_RADIUS = get("CASTLE_DEFENDER_SEARCH_RADIUS")
CLAN_CASTLE_RADIUS = get("CLAN_CASTLE_RADIUS")
FORGET_TARGET_TIME_MS = get("FORGET_TARGET_TIME")
ATTACK_PREPARATION_LENGTH_SEC = get("ATTACK_PREPARATION_LENGTH_SEC")
ATTACK_LENGTH_SEC = 180.0  # valor ATUAL confirmado ao vivo nesta sessao (o
                           # game_constants.json guarda 210 da versao antiga do dump)
