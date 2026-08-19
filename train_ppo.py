#!/usr/bin/env python3
"""CLI pra rodar o treino PPO do Gêmeo Digital (ver PROXIMOS_PASSOS.md,
"Fase 1.7 -- Loop de treino PPO").

Uso:
    python3 train_ppo.py                      # config padrao, 20 iteracoes
    python3 train_ppo.py --iterations 100 --n-envs 16
    python3 train_ppo.py --dataset-dir ~/minhas_bases --video-every 5

Gera, a cada `--video-every` iterações, um vídeo mosaico
(`training_runs/<run>/videos/geracao_<N>.mp4`) com os N ataques paralelos
daquela iteração lado a lado (ver `utils/population_viz.py`).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from utils.army import dragon_attack_army
from utils.base_dataset import BaseDataset, DEFAULT_DATASET_DIR
from utils.population_viz import render_from_rollout
from utils.ppo_train import PPOConfig, train


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR,
                     help="diretório com as bases capturadas (utils/capture_dataset.py)")
    ap.add_argument("--iterations", type=int, default=20)
    ap.add_argument("--n-envs", type=int, default=8)
    ap.add_argument("--n-steps", type=int, default=48)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--troop-housing-space", type=int, default=300,
                     help="capacidade de tropa da vila real -- AJUSTAR, valor de referência não confirmado")
    ap.add_argument("--rage-count", type=int, default=5)
    ap.add_argument("--checkpoint-every", type=int, default=10)
    ap.add_argument("--video-every", type=int, default=5, help="0 desliga a geração de vídeo")
    ap.add_argument("--video-fps", type=int, default=8)
    ap.add_argument("--checkpoint-dir", type=Path, default=Path("training_runs"))
    args = ap.parse_args()

    dataset = BaseDataset(dataset_dir=args.dataset_dir)
    if dataset.is_empty():
        print(f"[train_ppo] AVISO: nenhuma base em {args.dataset_dir} -- treinando "
              "com o cenário sintético de demonstração. Rode utils/capture_dataset.py "
              "com o Waydroid aberto pra treinar contra bases reais.\n")
    else:
        print(f"[train_ppo] {len(dataset)} base(s) carregada(s) de {args.dataset_dir}\n")

    army = dragon_attack_army(troop_housing_space=args.troop_housing_space, rage_count=args.rage_count)
    cfg = PPOConfig(n_envs=args.n_envs, n_steps=args.n_steps, lr=args.lr,
                     checkpoint_every=args.checkpoint_every, checkpoint_dir=args.checkpoint_dir)

    def on_iteration(iteration, data, metrics, run_dir):
        if args.video_every and iteration % args.video_every == 0:
            out = Path(run_dir) / "videos" / f"geracao_{iteration:05d}.mp4"
            render_from_rollout(data, out, fps=args.video_fps, iteration=iteration)
            print(f"[train_ppo] vídeo da geração {iteration} salvo em {out}")

    train(cfg, n_iterations=args.iterations, dataset=dataset, army_template=army,
          on_iteration=on_iteration)


if __name__ == "__main__":
    main()
