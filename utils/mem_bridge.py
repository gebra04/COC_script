"""Ponte pra chamar mem_reader.py (fora deste repo, em
~/.local/share/coc-digital-twin/) via a regra de sudoers escopada, parseando
a saida texto de --wallet e --battle-report pro session_loop consumir."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# Caminho do leitor externo (fora deste repo). A regra de sudoers é escopada
# a ESTE caminho exato — se mudar aqui, atualize /etc/sudoers.d/ também.
MEM_READER = os.environ.get(
    "COC_MEM_READER",
    str(Path.home() / ".local/share/coc-digital-twin/mem_reader.py"))


def find_game_pid() -> int | None:
    out = subprocess.run(["pgrep", "-f", "com.supercell.clashofclans"],
                          capture_output=True, text=True).stdout.strip()
    for line in out.splitlines():
        pid = line.strip()
        if pid.isdigit():
            return int(pid)
    return None


def _run(args: list[str]) -> str:
    cmd = ["sudo", "-n", "python3", MEM_READER, *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return proc.stdout + proc.stderr


def read_wallet(pid: int, cached_addr: str | None, seed: tuple[int, int, int]) -> dict | None:
    """seed = (gold, elixir, dark) lidos via hud_ocr.read_resources(), usados
    só se o endereço cacheado nao bater mais. Retorna None se nao achou nada
    (nem cache, nem faixa restrita, nem heap inteiro)."""
    args = [str(pid), "--wallet"]
    if cached_addr:
        args.append(cached_addr)
    args += [str(seed[0]), str(seed[1]), str(seed[2])]
    out = _run(args)
    if "nao encontrado" in out:
        return None
    m_addr = re.search(r"wallet @ (0x[0-9a-f]+)", out)
    m_gems = re.search(r"gems: (\d+)", out)
    m_gold = re.search(r"gold: (\d+)", out)
    m_elixir = re.search(r"elixir: (\d+)", out)
    m_dark = re.search(r"dark_elixir: (\d+)", out)
    if not (m_addr and m_gold and m_elixir and m_dark):
        return None
    return {
        "addr": m_addr.group(1),
        "gems": int(m_gems.group(1)) if m_gems else None,
        "gold": int(m_gold.group(1)),
        "elixir": int(m_elixir.group(1)),
        "dark_elixir": int(m_dark.group(1)),
    }


def read_battle_report(pid: int) -> dict | None:
    """None se nao ha resumo de batalha aberto agora (fora dessa tela)."""
    out = _run([str(pid), "--battle-report"])
    if "nenhuma instancia" in out:
        return None
    m_pct = re.search(r"destruicao:\s+(\d+)%", out)
    m_gold = re.search(r"saque ouro:\s+(-?\d+)", out)
    m_elixir = re.search(r"saque elixir:\s+(-?\d+)", out)
    m_dark = re.search(r"saque escuro:\s+(-?\d+)", out)
    m_tokens = re.search(r"tokens:\s+(-?\d+)", out)
    m_stars = re.search(r"estrelas:\s+(-?\d+)", out)
    if not (m_pct and m_gold and m_elixir and m_dark and m_stars):
        return None
    return {
        "destruction_pct": int(m_pct.group(1)),
        "loot_gold": int(m_gold.group(1)),
        "loot_elixir": int(m_elixir.group(1)),
        "loot_dark_elixir": int(m_dark.group(1)),
        "tokens": int(m_tokens.group(1)) if m_tokens else None,
        "stars": int(m_stars.group(1)),
    }
