#!/usr/bin/env python3
"""Captura em lote de bases pro "banco de dados" de treino (Passo 1 do
planejamento de treino PPO — ver PROXIMOS_PASSOS.md).

Fica escaneando a vila carregada no Waydroid enquanto o usuário troca de vila
MANUALMENTE no jogo (a própria + inimigas via scout). Detecta sozinho quando
uma vila NOVA estabilizou na tela e salva automaticamente — sem precisar
apertar Enter a cada uma.

Uso:
    python3 utils/capture_dataset.py
    python3 utils/capture_dataset.py --dataset-dir ~/minhas_bases --count 20

IMPORTANTE (2026-08-19, corrigido após o jogo fechar na v1 deste script):
a v1 fazia polling recriando um processo `sudo python3 mem_reader.py --json`
NOVO a cada leitura (a cada 0.7-2s) -- cada invocação faz uma varredura
completa do heap do zero, e respawnar isso em loop apertado sobrecarrega o
host o bastante pra derrubar o jogo (diferente do `--live`/`--watch` já
usados antes com segurança, que rodam como UM processo de longa duração).
Corrigido: agora sobe UM ÚNICO processo `mem_reader.py --watch-json`
(persistente, mesmo padrão de sleep do `--watch` humano já validado) e só
lê a saída dele -- nenhum processo novo é criado a cada poll. Uma segunda
leitura (via `read_enemy_base`, UMA chamada só) é feita apenas pra CONFIRMAR
que a base não estava no meio de uma transição de tela antes de salvar.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import base_loader

DEFAULT_DATASET_DIR = Path.home() / ".local" / "share" / "coc-digital-twin" / "bases"
DEFAULT_READER = base_loader.DEFAULT_READER

CONFIRM_DELAY_S = 1.0       # espera antes de reler pra confirmar estabilidade
SAVE_COOLDOWN_S = 4.0       # espera depois de salvar antes de aceitar nova deteccao
MIN_BUILDINGS = 3           # sanidade minima pra aceitar uma captura


def _signature(entities: list[dict]) -> frozenset:
    """Identidade de uma vila: QUAIS prédios existem e ONDE — sem HP/nível
    (mudam por ruído/decaimento de HP fora de combate, não indicam vila
    diferente). `entities` já vem sem Troop (filtrado por base_loader)."""
    return frozenset((e.get("did"), e.get("tx"), e.get("ty")) for e in entities)


def _next_filename(dataset_dir: Path, th_level: int | None) -> Path:
    th = th_level if th_level is not None else "x"
    n = 1
    while (p := dataset_dir / f"base_th{th}_{n:03d}.json").exists():
        n += 1
    return p


def capture_loop(dataset_dir: Path, pid: str = "auto", count: int | None = None,
                  reader_path: str = DEFAULT_READER, python_bin: str = "/usr/bin/python3") -> int:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    print(f"[capture] salvando em: {dataset_dir}")

    # Sanidade ANTES de subir o processo de observação em loop: se o jogo
    # atualizou (versão nova da libg.so), os offsets hardcoded no
    # mem_reader.py podem ter ficado obsoletos e a leitura não acha NADA --
    # sem este aviso, o script ficaria parado esperando uma vila que nunca
    # vai "aparecer" pra ele, sem explicação (2026-08-19: foi exatamente
    # esse cenário, combinado com a falta de backoff no --watch, que
    # sobrecarregou o host e derrubou o jogo por pressão de memória).
    print("[capture] checagem de sanidade (uma leitura única)...")
    try:
        probe = base_loader.read_enemy_base(pid=pid, reader_path=reader_path, python_bin=python_bin)
    except Exception as exc:
        print(f"[capture] leitura de teste falhou: {exc}", file=sys.stderr)
        probe = []
    if not probe:
        print(
            "\n⚠️  A leitura de teste não encontrou NENHUMA entidade. Provável causa: o "
            "jogo atualizou e os offsets de V-Table hardcoded em mem_reader.py (KNOWN_CLASSES) "
            "ficaram obsoletos para a nova build — precisa refazer a engenharia reversa "
            "(ver pesquisa/01/02) antes deste script conseguir detectar vilas.\n"
            "Prosseguindo mesmo assim é seguro (o loop agora tem backoff, não martela o "
            "host), mas não vai achar nada até os offsets serem atualizados. Ctrl+C pra "
            "cancelar, ou aguarde — vai continuar tentando com intervalo crescente.\n"
        )

    print("[capture] subindo processo único de observação (mem_reader.py --watch-json)...")

    cmd = ["sudo", "-n", python_bin, reader_path, str(pid), "--watch-json"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

    print("[capture] aguardando vilas (Ctrl+C pra parar)...\n")
    saved = 0
    try:
        while count is None or saved < count:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    err = proc.stderr.read()
                    print(f"[capture] processo de observação terminou inesperadamente: {err}", file=sys.stderr)
                    break
                continue
            line = line.strip()
            if not line.startswith("{"):
                continue  # ruido / linha nao-JSON

            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            entities = base_loader._filter_static(raw.get("entities", []))
            candidate_sig = _signature(entities)

            # confirma com UMA leitura extra (nao um loop) antes de salvar --
            # protege contra pegar o estado no meio de uma transicao de tela.
            time.sleep(CONFIRM_DELAY_S)
            try:
                confirm_entities = base_loader.read_enemy_base(pid=pid, reader_path=reader_path, python_bin=python_bin)
            except Exception as exc:
                print(f"[capture] confirmação falhou (ignorando esta detecção): {exc}", file=sys.stderr)
                continue

            if _signature(confirm_entities) != candidate_sig:
                print("[capture] detecção instável (tela ainda mudando) — aguardando a próxima.")
                continue

            report = base_loader.base_report(confirm_entities)
            if not (report["has_town_hall"] and report["n_buildings"] >= MIN_BUILDINGS):
                print(f"[capture] vila reprovada na sanidade "
                      f"(TH={report['th_level']}, prédios={report['n_buildings']}) — ignorando\n")
                time.sleep(SAVE_COOLDOWN_S)
                continue

            out_path = _next_filename(dataset_dir, report["th_level"])
            base_loader.save_base(confirm_entities, out_path)
            saved += 1
            print(
                f"✅ [{saved}] Vila salva — TH{report['th_level']} | "
                f"{report['n_buildings']} prédios, {report['n_walls']} muralhas, "
                f"{report['n_defenses']} defesas → {out_path.name}"
            )
            print("   >>> pode trocar de vila agora <<<\n")
            time.sleep(SAVE_COOLDOWN_S)
    except KeyboardInterrupt:
        print("\n[capture] interrompido pelo usuário.")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print(f"\n[capture] concluído: {saved} vila(s) salva(s) em {dataset_dir}")
    return saved


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR,
                     help=f"diretório onde salvar as capturas (padrão: {DEFAULT_DATASET_DIR})")
    ap.add_argument("--pid", default="auto", help="PID do jogo no Waydroid, ou 'auto'")
    ap.add_argument("--count", type=int, default=None, help="parar depois de N capturas")
    args = ap.parse_args()

    capture_loop(args.dataset_dir, pid=args.pid, count=args.count)


if __name__ == "__main__":
    main()
