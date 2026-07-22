# 03 — Waydroid no Fedora: instalação, ARM, root e IPC

> **Status:** guia de infra (verificável). **Faça este primeiro** — sem o Waydroid + jogo
> rodando você não extrai a `libg.so` nem testa o pipeline.
> Última atualização: 2026-07-22. Ajuste os comandos à versão atual do Fedora.

---

## 1. Instalar e inicializar o Waydroid
Requer **sessão Wayland** (o Waydroid não roda sob X11 puro — ver armadilha no fim do doc se sua sessão for X11).

A instalação difere conforme a variante do Fedora:
```bash
# Fedora Workstation e demais edições RPM tradicionais:
sudo dnf install waydroid          # se ausente, ver repo COPR / docs.waydro.id

# Fedora Silverblue / Kinoite (imutáveis, rpm-ostree):
rpm-ostree install waydroid
# reinicie o sistema após o overlay do rpm-ostree
```
> **Não** rode o `waydroid-container` dentro de um Toolbox/Distrobox nas edições imutáveis — ele
> precisa de acesso direto a privilégios do sistema e ao `systemd` do hospedeiro, que um ambiente
> Toolbox isola por design.

```bash
sudo systemctl enable --now waydroid-container
sudo waydroid init -s GAPPS        # GAPPS = com Play Store (recomendado p/ instalar o CoC)
# alternativa sem Google: -s VANILLA (aí instala o CoC via sideload de APK)
waydroid session start &           # inicia a sessão do usuário
waydroid show-full-ui              # abre a UI
```
> Escolha **GAPPS** para baixar o CoC pela Play Store. VANILLA exige `waydroid app install <apk>`.

### 1.1 Certificar o dispositivo GAPPS junto à Google (obrigatório p/ Play Store)
Sem este passo a Play Store pode recusar login ou marcar o dispositivo como não certificado,
mesmo com a imagem GAPPS. Com `waydroid show-full-ui` já rodando:
```bash
sudo waydroid shell \
  ANDROID_RUNTIME_ROOT=/apex/com.android.runtime \
  ANDROID_DATA=/data \
  ANDROID_TZDATA_ROOT=/apex/com.android.tzdata \
  ANDROID_I18N_ROOT=/apex/com.android.i18n \
  sqlite3 /data/data/com.google.android.gsf/databases/gservices.db \
  "select * from main where name = \"android_id\";"
```
Pegue o número retornado e registre-o em https://www.google.com/android/uncertified/ (página oficial
de dispositivos não certificados da Google). Aguarde a propagação (pode levar alguns minutos) antes
de tentar logar na Play Store.

---

## 2. Tradução ARM (o Fedora é x86_64, o CoC é ARM64)
Sem isto o jogo **não inicia**. Use o [`casualsnek/waydroid_script`](https://github.com/casualsnek/waydroid_script):
```bash
sudo dnf install lzip
git clone https://github.com/casualsnek/waydroid_script
cd waydroid_script
python3 -m venv venv
venv/bin/pip install -r requirements.txt
# escolha UM tradutor (não instale os dois):
sudo venv/bin/python3 main.py install libhoudini   # Intel
# ou:
sudo venv/bin/python3 main.py install libndk        # AMD
```
- **libhoudini** → CPUs Intel; **libndk** → CPUs AMD ([DeepWiki: ARM translation](https://deepwiki.com/casualsnek/waydroid_script/5.4-arm-translation-(libndk-and-libhoudini))).
- **Nunca** instale os dois juntos — há bug de estado que deixa o libndk "uninstallable" ([issue #119](https://github.com/casualsnek/waydroid_script/issues/119)).
- Descubra seu fabricante de CPU: `lscpu | grep -i vendor`.

---

## 3. Root com Magisk
Necessário para o middleware ter `ptrace`/`process_vm_readv` e ler `/proc/<pid>/maps`.
```bash
sudo venv/bin/python3 main.py install magisk
# a injeção do Magisk mexe no boot/ramdisk do container — pare tudo e reinicie por completo:
sudo waydroid container stop
waydroid session stop
sudo systemctl restart waydroid-container
waydroid session start &
```
Verifique de duas formas:
```bash
sudo waydroid shell        # shell root direto do hospedeiro — deve já ser uid=0
# ou dentro da própria UI: abra um terminal Android (ex. Termux) e rode `su`;
# o Magisk deve interceptar e mostrar o diálogo de concessão de root.
```
(O mesmo `main.py` também oferece `nodataperm`, `microg`, `smartdock` — opcionais.)

---

## 4. SELinux / permissões (host Fedora)
O Fedora usa SELinux em **enforcing** por padrão. Para o injector conseguir `ptrace`/
`process_vm_readv` dentro do container, **não** é necessário desligar o SELinux globalmente — o
caminho correto é habilitar as três permissões específicas abaixo, mantendo o resto do sistema
protegido:

**a) YAMA ptrace_scope (kernel do hospedeiro)** — por padrão o módulo YAMA restringe `ptrace` a
relações pai-filho diretas. Libere para permitir inspeção de processos arbitrários do container:
```bash
sudo sysctl -w kernel.yama.ptrace_scope=0     # imediato
echo "kernel.yama.ptrace_scope = 0" | sudo tee /etc/sysctl.d/10-ptrace.conf
sudo sysctl --system                          # persiste entre reboots
```

**b) Capability do LXC** — confirme que `/var/lib/waydroid/lxc/waydroid/config` mantém
`sys_ptrace` na linha `lxc.cap.keep` (normalmente já vem assim por padrão):
```
lxc.cap.keep = audit_control sys_nice wake_alarm setpcap setgid setuid sys_ptrace sys_admin block_suspend sys_time net_admin
```

**c) Booleano dedicado do SELinux** — em vez de `setenforce 0` (que desliga a proteção do sistema
inteiro), habilite só a permissão de que o container precisa:
```bash
sudo ausearch -m avc -ts recent | grep waydroid   # confirma se há negação AVC relacionada
sudo setsebool -P container_use_sys_ptrace 1      # persistente, escopo limitado a containers
```
Isso é estritamente melhor que desabilitar o enforcing global: mantém o resto do hospedeiro protegido
e resolve o caso específico de `ptrace`/`process_vm_readv` sobre processos do container.

> **Último recurso:** se ainda houver bloqueio de comunicação *dentro* da imagem Android (SELinux
> interno do Android, não o do hospedeiro), alterne o guest para permissivo via
> `sudo waydroid shell` seguido de `setenforce 0` **dentro do shell do container** — isso não afeta
> o SELinux do Fedora hospedeiro. Evite `setenforce 0` no hospedeiro; se usar como teste pontual,
> reative com `setenforce 1` assim que terminar o diagnóstico.

---

## 5. Confirmar memfd_create + SCM_RIGHTS no container
Nosso IPC (Camada 3) depende de `memfd_create` e passagem de FD via `SCM_RIGHTS` **dentro** do Waydroid. Teste rápido:
```bash
# empurre e rode o coc_dt_middleware (cross-compilado p/ a ABI do guest — ver 04) dentro do guest;
# se Initialize() não falhar em memfd_create, está ok.
adb shell "cat /proc/version"    # confere kernel do guest
```
Se `memfd_create` falhar por seccomp, verifique a policy do container LXC.

**Por que isso funciona (mecanismo, confirma a premissa do `layer3_ipc_bridge.hpp`):** o próprio
Waydroid já usa esse caminho para a pilha gráfica, então se ele renderiza normalmente, o mecanismo
está disponível para o middleware também. Em `/var/lib/waydroid/waydroid_base.prop`, a propriedade
`sys.use_memfd=true` instrui a Mesa do guest a alocar buffers via `memfd_create` (substituindo o
antigo `ashmem`) e a transferir o descritor de ficheiro para o compositor do hospedeiro (Mutter/KWin)
via `sendmsg()` com `SCM_RIGHTS`, sobre o socket Unix do Wayland em `/run/user/1000/wayland-0` — o
mesmo padrão FD-over-socket que nosso IPC usa para o socket `/coc-digital-twin/coc_dt.sock` (seção 6).
Se quiser confirmar a flag: `grep sys.use_memfd /var/lib/waydroid/waydroid_base.prop`.

---

## 6. Bind mount do socket (host ↔ guest)
Para o receptor Python (host) enxergar o socket criado pelo middleware (guest). Ver `utils/digital_twin_paths.py` (lado host) e `native/include/layer3_ipc_bridge.hpp` (`DEFAULT_SOCKET_PATH = "/coc-digital-twin/coc_dt.sock"`, lado guest).
```bash
mkdir -p ~/.local/share/coc-digital-twin
# editar a config do LXC do Waydroid:
sudo nano /var/lib/waydroid/lxc/waydroid/config
# adicionar (host dir -> guest dir):
#   lxc.mount.entry = /home/SEU_USUARIO/.local/share/coc-digital-twin coc-digital-twin none bind,create=dir 0 0
sudo systemctl restart waydroid-container
adb shell ls -la /coc-digital-twin   # deve aparecer dentro do guest
```

---

## 7. Rede (firewalld) e ADB a partir do host (para o atuador depois)
O Waydroid cria uma interface virtual `waydroid0` no hospedeiro. O `firewalld` do Fedora, por
padrão, costuma bloquear DHCP/DNS nessa interface, deixando o **guest sem internet** mesmo com o
container rodando — isso também impede a Play Store de baixar o CoC na seção 1. Se o guest não
tiver rede, resolva **antes** de depurar qualquer outra coisa:
```bash
sudo firewall-cmd --zone=trusted --add-interface=waydroid0 --permanent
sudo firewall-cmd --reload
sudo waydroid container stop
sudo systemctl restart waydroid-container
```

Descubra o IP do guest e conecte o ADB:
```bash
ip addr show waydroid0                 # IP visto do hospedeiro (rede 192.168.240.x, tipicamente)
# ou, de dentro do guest:
sudo waydroid shell ip addr show eth0

sudo dnf install android-tools         # se o comando `adb` não existir
adb connect 192.168.240.XXX:5555       # porta 5555, adbd habilitado por auto_adb=True
adb devices
adb shell input tap 500 500            # teste de toque (ver 05)
```
Isto habilita o **atuador via ADB** (ver [05](05_atuador_isometrico_input.md)).

---

## 8. Instalar o Clash of Clans e extrair a `libg.so`
```bash
# GAPPS: instalar pela Play Store dentro da UI, logar, chegar até uma vila.
# extrair a lib nativa (desbloqueia 01/02):
adb shell pm path com.supercell.clashofclans       # acha o base.apk
adb pull /data/app/.../base.apk ./coc.apk          # ou o caminho reportado
unzip coc.apk 'lib/arm64-v8a/*' -d coc_libs         # libg.so fica aqui
# alternativamente, puxar a .so já mapeada:
adb shell "su -c 'cat /proc/$(pidof com.supercell.clashofclans)/maps | grep libg.so'"
```
A `libg.so` extraída é o insumo de [01](01_re_metodologia_libg.md) e [02](02_ponteiro_raiz_e_structs.md).

---

## Armadilhas comuns (Fedora/Waydroid)
- **Sem rede no guest:** ver fix do `firewalld`/`waydroid0` na seção 7. Se persistir, ajustar
  nftables/masquerade; ver [Ivon's Blog — Waydroid Tips](https://ivonblog.com/en-us/posts/waydroid-tips/).
- **`ERROR: Binder node "binder" for waydroid not found`:** o `binderfs` não foi montado.
  ```bash
  sudo mkdir -p /dev/binderfs
  sudo mount -t binder binder /dev/binderfs
  ```
- **`Wayland socket 'wayland-0' doesn't exist` / sessão X11 pura:** o Waydroid exige um
  compositor Wayland nativo. Se a sessão de login só tem X11 disponível, rode um compositor
  Wayland aninhado como ponte:
  ```bash
  sudo dnf install weston
  weston &
  WAYLAND_DISPLAY=wayland-1 waydroid show-full-ui
  ```
- **Waydroid captura teclado/mouse mesmo sem foco, ou o app exige toque em vez de clique:**
  ```bash
  waydroid prop set persist.waydroid.uevent false                  # não capturar sem foco
  waydroid prop set persist.waydroid.fake_touch "com.supercell.clashofclans"  # emular toque p/ o CoC
  waydroid prop set persist.waydroid.fake_touch ""                 # reverter, se precisar
  ```
  Relevante para o atuador (ver [05](05_atuador_isometrico_input.md)) — se o clique de mouse via
  ADB não for reconhecido pelo jogo como toque, `fake_touch` resolve sem precisar de `minitouch`.
- **`waydroid_script` sob venv:** rode sempre com `sudo venv/bin/python3 main.py ...` (o sudo precisa do python do venv).

## Fontes
- Waydroid docs — https://docs.waydro.id/
- casualsnek/waydroid_script — https://github.com/casualsnek/waydroid_script
- ARM translation (DeepWiki) — https://deepwiki.com/casualsnek/waydroid_script/5.4-arm-translation-(libndk-and-libhoudini)
- Install & setup (DeepWiki) — https://deepwiki.com/casualsnek/waydroid_script/2-installation-and-setup
- issue #119 (não misturar libndk/libhoudini) — https://github.com/casualsnek/waydroid_script/issues/119
- Ivon's Blog — Waydroid Tips — https://ivonblog.com/en-us/posts/waydroid-tips/
- Waydroid prop options — https://docs.waydro.id/usage/waydroid-prop-options
- Google — página de dispositivos não certificados (registro de `android_id` p/ GAPPS) — https://www.google.com/android/uncertified/
- SELinux `container_use_sys_ptrace` / YAMA `ptrace_scope` — documentação padrão do Fedora sobre SELinux booleans e `man 7 ptrace` (seção YAMA)
- `firewalld` zona `trusted` para a interface `waydroid0` — comportamento documentado de rede do Waydroid em ambientes com firewall ativo por padrão (Fedora)
