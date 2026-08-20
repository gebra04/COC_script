"""Loop de decisão que junta as peças construídas em 2026-08-19:

  - mem_bridge: leitura de saldo (--wallet) e resultado de ataque
    (--battle-report), via mem_reader.py (fora deste repo).
  - hud_ocr: construtores livres, e semente de OCR pro saldo quando o
    cache de endereço da memória precisa recalibrar.
  - upgrade_picker: escolhe o que upar (muro primeiro, senão a primeira
    sugestão, nunca herói) quando há folga de recurso e construtor livre.
  - live_ui_actions: confirma o upgrade escolhido, e sai da tela de resumo
    de ataque (Return Home) quando um BattleReport é achado.

O QUE NÃO ESTÁ AQUI: automação de ataque em si (buscar partida + soltar
tropa). start_attack_search()/confirm_attack() existem em live_ui_actions
como blocos prontos, mas ligar isso a um loop de verdade precisa de uma
política de deploy de tropas — que é o próprio projeto de RL/simulação
(utils/army.py, attack_simulator.py, ppo_train.py), não algo que se resolve
com toque de botão. Por enquanto o loop só REAGE a um resumo de ataque já
aberto (ex.: você atacou manualmente) — loga o resultado e sai da tela.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from utils import hud_ocr, mem_bridge, upgrade_picker, live_ui_actions

DEFAULT_LOG_PATH = Path.home() / ".local/share/coc-digital-twin/session_log.jsonl"

# Limiares de "quase cheio" pra disparar upgrade — cada conta tem
# capacidade de armazém diferente (não achamos leitura confiável da
# capacidade máxima nesta sessão, ver conversa de 2026-08-19), então isso
# É CONFIGURAÇÃO MANUAL por conta, não um valor universal. Ajuste antes de
# rodar de verdade.
DEFAULT_THRESHOLDS = {"gold": 1_000_000, "elixir": 1_000_000, "dark_elixir": 50_000}

MIN_FREE_BUILDERS_TO_ACT = 2  # sempre deixa pelo menos 1 livre (regra do usuário)


def _log(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": time.time(), **entry}
    with path.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def check_and_log_battle(pid: int, log_path: Path = DEFAULT_LOG_PATH) -> dict | None:
    """Se um resumo de ataque estiver aberto agora, loga o resultado e sai
    da tela (Return Home). Retorna o resultado lido, ou None se não havia
    resumo aberto (nada a fazer)."""
    report = mem_bridge.read_battle_report(pid)
    if report is None:
        return None
    _log(log_path, {"type": "battle_report", **report})
    live_ui_actions.return_home()
    return report


def check_and_upgrade(pid: int, wallet_addr: str | None, thresholds: dict = None,
                       log_path: Path = DEFAULT_LOG_PATH, dry_run: bool = False) -> dict:
    """Lê construtores livres + saldo; se algum recurso passou do limiar E
    sobra construtor (reservando 1), escolhe e confirma um upgrade (muro
    primeiro). Retorna um dict de diagnóstico com o que foi decidido/feito,
    e sempre inclui "wallet_addr" atualizado (cachear pra próxima chamada —
    ver mem_bridge.read_wallet, é bem mais rápido com cache valido)."""
    thresholds = thresholds or DEFAULT_THRESHOLDS

    free, total = hud_ocr.read_builders()
    if free < MIN_FREE_BUILDERS_TO_ACT:
        return {"action": "skip", "reason": "reserva de construtor", "free_builders": free,
                "wallet_addr": wallet_addr}

    seed = hud_ocr.read_resources()  # só usado se o cache falhar
    wallet = mem_bridge.read_wallet(pid, wallet_addr, seed)
    if wallet is None:
        return {"action": "skip", "reason": "wallet nao encontrado", "wallet_addr": None}
    new_addr = wallet["addr"]

    over_threshold = any(wallet[k] >= v for k, v in thresholds.items())
    if not over_threshold:
        return {"action": "skip", "reason": "recursos abaixo do limiar",
                "wallet": wallet, "wallet_addr": new_addr}

    picked = upgrade_picker.pick_upgrade(dry_run=dry_run)
    if picked.get("picked") is None:
        return {"action": "skip", "reason": "nada pra upar (lista vazia/ilegivel)",
                "wallet": wallet, "wallet_addr": new_addr}

    result = {"action": "upgrade", "picked": picked, "wallet": wallet, "wallet_addr": new_addr}
    if not dry_run:
        confirm = live_ui_actions.confirm_selected_upgrade()
        result["confirm"] = confirm
    _log(log_path, {"type": "upgrade_decision", **result})
    return result


def run_loop(pid: int | None = None, interval_s: float = 60.0, iterations: int | None = None,
             thresholds: dict = None, log_path: Path = DEFAULT_LOG_PATH, dry_run: bool = False) -> None:
    """Loop principal. iterations=None roda pra sempre (Ctrl+C pra parar);
    um número finito é pra teste. dry_run propaga pra check_and_upgrade —
    não toca em nada de verdade, só reporta o que faria."""
    pid = pid or mem_bridge.find_game_pid()
    if pid is None:
        raise RuntimeError("Clash of Clans nao esta rodando (pgrep nao achou o processo)")

    wallet_addr = None
    i = 0
    while iterations is None or i < iterations:
        battle = check_and_log_battle(pid, log_path)
        if battle:
            print(f"[loop] resumo de ataque: {battle}")

        result = check_and_upgrade(pid, wallet_addr, thresholds, log_path, dry_run)
        wallet_addr = result.get("wallet_addr", wallet_addr)
        print(f"[loop] {result.get('action')}: {result.get('reason', result.get('picked'))}")

        i += 1
        if iterations is None or i < iterations:
            time.sleep(interval_s)


if __name__ == "__main__":
    import sys
    n = None
    for a in sys.argv[1:]:
        if a.startswith("--iterations="):
            n = int(a.split("=", 1)[1])
    run_loop(iterations=n, interval_s=10.0 if n else 60.0, dry_run="--dry-run" in sys.argv)
