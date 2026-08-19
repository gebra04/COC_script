"""Caminho canônico do socket IPC do Gêmeo Digital (Camada 3 do digital_twin.md).

Módulo deliberadamente sem dependências pesadas (só `os`), para que qualquer
consumidor — incluindo `gui.py` no momento em que a janela é montada, antes de
o usuário sequer abrir a aba "Gêmeo Digital" — possa importar o caminho padrão
sem forçar a carga de `numpy`/`torch`/`gymnasium`.

O guest Android (Waydroid) e o host Fedora têm namespaces de sistema de
arquivos separados: um caminho como `/tmp/coc_dt.sock` criado dentro do
container Waydroid não é visível em `/tmp` do host. Para que o servidor
nativo (Camada 3, ainda não implementado em `native/`) e os clientes Python
deste repositório enxerguem o mesmo socket, o diretório abaixo deve ser
compartilhado entre host e guest via bind mount do LXC do Waydroid:

    # /var/lib/waydroid/lxc/waydroid/config
    lxc.mount.entry = /home/<usuario>/.local/share/coc-digital-twin data/media/0/coc-digital-twin none bind,create=dir,optional 0 0

Nota: a raiz do container (`/`, montada a partir de `system.img`) é somente
leitura, então `create=dir` falha para qualquer alvo fora de uma partição
gravável — por isso o alvo é `data/media/0/...` (a partição `/data`, que
corresponde a `/sdcard` no guest) e não um diretório solto na raiz.

Isso expõe o diretório do host em `/data/media/0/coc-digital-twin` (a.k.a.
`/sdcard/coc-digital-twin`) dentro do container. O servidor nativo (quando
implementado) deve criar o socket em `/data/media/0/coc-digital-twin/coc_dt.sock`
*dentro* do Waydroid; do lado do host, o mesmo arquivo aparece em
`DEFAULT_SOCKET_PATH` abaixo. Ver `mapeamento_arquivos.md` seção 5 para o
passo a passo completo.
"""

from __future__ import annotations

import os

DEFAULT_SHARED_DIR = os.path.expanduser("~/.local/share/coc-digital-twin")
DEFAULT_SOCKET_PATH = os.path.join(DEFAULT_SHARED_DIR, "coc_dt.sock")
