"""Receptor de telemetria via LEITOR EXTERNO de memória (arquitetura B).

Substituto do `ZeroCopyIPCReceiver` (arquitetura A, middleware C++ injetado)
para o caso — confirmado necessário — em que a injeção/Frida é detectada e
derrubada pelo anti-tamper do Clash of Clans (ver `pesquisa/06`).

Em vez de receber telemetria de um servidor nativo injetado no jogo, este
receptor lê a memória do processo do jogo **de fora**, de forma passiva, via
`/proc/<pid>/mem`. A leitura em si é feita pelo script `mem_reader.py`
(fora do repositório, em ~/.local/share/coc-digital-twin/), invocado com
privilégio via `sudo` (regra NOPASSWD dedicada) no modo `--json`.

Expõe a MESMA interface que o `ZeroCopyIPCReceiver` — `read_latest_telemetry()`
retornando `(sequence, entities_ndarray)` com o `TELEMETRY_DTYPE` — de modo que
`utils.clash_env.ClashDigitalTwinEnv` funciona sem alteração, apenas trocando a
fonte de telemetria. Ver `mapeamento_arquivos.md` (Seção "Arquitetura B") e
`pesquisa/02` para os offsets levantados.

Offsets/cadeias usados pelo `mem_reader.py` são desta build da `libg.so`
(x86-64). As posições (`tx`,`ty`) já saem em **tiles** (o script divide os
subtiles por 512), então o grid do ambiente deve ser 44×44.
"""

from __future__ import annotations

import json
import os
import subprocess

import numpy as np

from utils.ipc_receiver import TELEMETRY_DTYPE

# Tipos genéricos esperados pelo clash_env (defesa=1 / tropa=2 / recurso=3).
ENTITY_TYPE_DEFENSE = 1
ENTITY_TYPE_TROOP = 2
ENTITY_TYPE_RESOURCE = 3
ENTITY_TYPE_OTHER = 0  # muralha, CV, army camp, obstáculo, armadilha (ignorado pelo grid atual)

# data-id (linha do buildings.csv + 1000000) → categoria genérica.
_DEFENSE_IDS = {
    1000008, 1000009, 1000011, 1000012, 1000013, 1000019, 1000028,
    1000021, 1000027, 1000030, 1000029, 1000067,  # X-Bow, Inferno, Eagle, Bomb Tower, Scattershot
}
_RESOURCE_IDS = {1000002, 1000003, 1000004, 1000005, 1000023, 1000024}


def _generic_type(did: int) -> int:
    if did in _DEFENSE_IDS:
        return ENTITY_TYPE_DEFENSE
    if did in _RESOURCE_IDS:
        return ENTITY_TYPE_RESOURCE
    # tropas (4000000+) entram como TROOP quando aparecerem em combate
    if 4000000 <= did <= 4100000:
        return ENTITY_TYPE_TROOP
    return ENTITY_TYPE_OTHER


# Caminho do leitor externo e comando sudo (regra NOPASSWD dedicada).
DEFAULT_READER = os.path.expanduser("~/.local/share/coc-digital-twin/mem_reader.py")


class ExternalMemoryReceiver:
    """Lê a telemetria da vila carregada (sua ou inimiga em scout) via
    `mem_reader.py --json`. Interface compatível com `ZeroCopyIPCReceiver`.

    Parâmetros
    ----------
    pid : int | str
        PID (host) do processo do jogo, ou "auto" para o script descobrir.
    reader_path : caminho do mem_reader.py.
    python_bin : interpretador (deve casar com a regra sudoers: /usr/bin/python3).
    """

    def __init__(self, pid="auto", reader_path: str = DEFAULT_READER,
                 python_bin: str = "/usr/bin/python3"):
        self.pid = str(pid)
        self.reader_path = reader_path
        self.python_bin = python_bin
        self._seq = 0
        # HP (current_hp) só é populado durante a batalha (ver pesquisa/02).
        # Rastreamos o PICO por entity_id como max_hp: no início do combate
        # current_hp == HP cheio, então o pico captura o máximo e a razão
        # current/max fica correta conforme o prédio apanha.
        self._max_hp: dict[int, int] = {}

    # --- interface compatível com ZeroCopyIPCReceiver ---
    def connect(self):
        """Não há conexão persistente; valida que o leitor responde."""
        self._invoke()  # levanta se algo estiver errado
        return self

    def read_latest_telemetry(self):
        """Retorna (sequence, entities_ndarray) da vila carregada, ou None."""
        raw = self._invoke()
        if raw is None:
            return None
        ents = raw.get("entities", [])
        arr = np.zeros(len(ents), dtype=TELEMETRY_DTYPE)
        for i, e in enumerate(ents):
            eid = e["eid"] & 0xFFFFFFFF
            arr[i]["entity_id"] = eid
            arr[i]["type_id"] = _generic_type(e["did"])
            arr[i]["level"] = min(max(e["lvl"], 0), 255)
            arr[i]["state"] = 0
            arr[i]["pos_x"] = float(e["tx"])   # já em tiles
            arr[i]["pos_y"] = float(e["ty"])
            # current_hp populado só em combate; max_hp = pico rastreado por
            # entidade. Fora de combate (hp=0), assume cheio (razão 1.0).
            hp = int(e.get("hp", 0) or 0)
            peak = max(self._max_hp.get(eid, 0), hp)
            self._max_hp[eid] = peak
            if peak > 0 and hp > 0:
                arr[i]["current_hp"] = float(hp)
                arr[i]["max_hp"] = float(peak)
            else:
                arr[i]["current_hp"] = 1.0   # sem HP em memória (scout) → cheio
                arr[i]["max_hp"] = 1.0
        self._seq += 1
        return self._seq, arr

    def close(self):
        pass

    def __enter__(self):
        return self.connect()

    def __exit__(self, *exc):
        self.close()

    # --- interno ---
    def _invoke(self):
        cmd = ["sudo", self.python_bin, self.reader_path, self.pid, "--json"]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            raise RuntimeError(f"falha ao invocar o leitor externo: {exc}") from exc
        if out.returncode != 0:
            raise RuntimeError(
                f"mem_reader --json falhou (rc={out.returncode}): {out.stderr.strip()}"
            )
        try:
            return json.loads(out.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"saída do leitor não é JSON válido: {exc}") from exc
