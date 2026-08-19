"""Banco de bases pro treino (Passo 2 do planejamento de treino PPO — ver
PROXIMOS_PASSOS.md). Carrega todas as capturas salvas por
`utils.capture_dataset` e sorteia uma por episódio — cada `reset()` do
`ClashDigitalTwinEnv` ataca uma vila diferente, em vez de sempre a mesma.
"""

from __future__ import annotations

import random
from pathlib import Path

from utils import base_loader

DEFAULT_DATASET_DIR = Path.home() / ".local" / "share" / "coc-digital-twin" / "bases"


class BaseDataset:
    """Carrega todos os `.json` de `dataset_dir` (poucas dezenas de arquivos —
    não precisa lazy-load) e sorteia uma base por chamada de `sample()`.

    Uso como `base_provider` do `ClashDigitalTwinEnv`:

        ds = BaseDataset()
        env = ClashDigitalTwinEnv(base_provider=ds.sample, army=army)
    """

    def __init__(self, dataset_dir: str | Path = DEFAULT_DATASET_DIR,
                 rng: random.Random | None = None):
        self.dataset_dir = Path(dataset_dir)
        self.rng = rng or random
        self._bases: list[list[dict]] = []
        self._paths: list[Path] = []
        self._load()

    def _load(self) -> None:
        if not self.dataset_dir.exists():
            return
        for p in sorted(self.dataset_dir.glob("*.json")):
            try:
                entities = base_loader.load_base(p)
            except Exception:
                continue  # captura corrompida/incompleta -- ignora, nao derruba o dataset
            if entities:
                self._bases.append(entities)
                self._paths.append(p)

    def __len__(self) -> int:
        return len(self._bases)

    def is_empty(self) -> bool:
        return len(self._bases) == 0

    def sample(self) -> list[dict]:
        """Devolve uma base aleatória. Se o banco estiver vazio (usuário
        ainda não rodou `utils/capture_dataset.py`), cai pro cenário
        sintético de `debug/sim_viewer.py::_demo_scenario` com um aviso --
        permite testar o resto do pipeline sem depender do Waydroid aberto."""
        if self.is_empty():
            import sys

            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "debug"))
            from sim_viewer import _demo_scenario

            print("[base_dataset] AVISO: nenhuma base capturada em "
                  f"{self.dataset_dir} -- usando cenário sintético de demonstração. "
                  "Rode utils/capture_dataset.py com o Waydroid aberto pra treinar "
                  "contra bases reais.")
            entities, _plan = _demo_scenario()
            return entities
        idx = self.rng.randrange(len(self._bases))
        return self._bases[idx]

    def path_for_sample_index(self, idx: int) -> Path | None:
        return self._paths[idx] if 0 <= idx < len(self._paths) else None
