# 03 — Waydroid no Fedora: instalação, ARM, root e IPC

> **Status:** guia de infra (verificável). **Faça este primeiro** — sem o Waydroid + jogo
> rodando você não extrai a `libg.so` nem testa o pipeline.
> Última atualização: 2026-07-22. Ajuste os comandos à versão atual do Fedora.

---

## 1. Instalar e inicializar o Waydroid
Requer **sessão Wayland** (o Waydroid não roda sob X11 puro).
```bash
sudo dnf install waydroid          # se ausente, ver repo COPR / docs.waydro.id
sudo waydroid init -s GAPPS        # GAPPS = com Play Store (recomendado p/ instalar o CoC)
# alternativa sem Google: -s VANILLA (aí instala o CoC via sideload de APK)
sudo systemctl enable --now waydroid-container
waydroid session start &           # inicia a sessão do usuário
waydroid show-full-ui              # abre a UI
```
> Escolha **GAPPS** para baixar o CoC pela Play Store. VANILLA exige `waydroid app install <apk>`.

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
# reinicie o container e verifique:
sudo systemctl restart waydroid-container
adb shell su -c "id"    # deve retornar uid=0(root)
```
(O mesmo `main.py` também oferece `nodataperm`, `microg`, `smartdock` — opcionais.)

---

## 4. SELinux / permissões (host Fedora)
O Fedora usa SELinux em enforcing. Para o injector conseguir `ptrace`/`process_vm_readv` dentro do container pode ser necessário:
```bash
getenforce                      # ver estado
sudo setenforce 0               # TESTE apenas — permissive; reative depois com setenforce 1
```
> `setenforce 0` é um martelo. O ideal é uma política dedicada, mas para prototipar em máquina pessoal o modo permissive destrava o diagnóstico. **Reative** (`setenforce 1`) quando terminar, ou torne a decisão consciente.

Dentro do guest, o Android também tem SELinux próprio; com Magisk root normalmente já se consegue `ptrace` sobre processos do mesmo usuário.

---

## 5. Confirmar memfd_create + SCM_RIGHTS no container
Nosso IPC (Camada 3) depende de `memfd_create` e passagem de FD via `SCM_RIGHTS` **dentro** do Waydroid. Teste rápido:
```bash
# empurre e rode o coc_dt_middleware (cross-compilado p/ a ABI do guest — ver 04) dentro do guest;
# se Initialize() não falhar em memfd_create, está ok.
adb shell "cat /proc/version"    # confere kernel do guest
```
Se `memfd_create` falhar por seccomp, verifique a policy do container LXC.

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

## 7. ADB a partir do host (para o atuador depois)
O Waydroid expõe `adbd`. Descubra o IP/porta e conecte:
```bash
adb connect $(waydroid status | grep IP | awk '{print $3}'):5555   # ou a porta reportada
adb devices
adb shell input tap 500 500     # teste de toque (ver 05)
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
- **Sem rede no guest:** ajustar nftables/masquerade; ver [Ivon's Blog — Waydroid Tips](https://ivonblog.com/en-us/posts/waydroid-tips/).
- **Toque não responde:** idem (prop options).
- **X11 em vez de Wayland:** o Waydroid não sobe — troque a sessão no login.
- **`waydroid_script` sob venv:** rode sempre com `sudo venv/bin/python3 main.py ...` (o sudo precisa do python do venv).

## Fontes
- Waydroid docs — https://docs.waydro.id/
- casualsnek/waydroid_script — https://github.com/casualsnek/waydroid_script
- ARM translation (DeepWiki) — https://deepwiki.com/casualsnek/waydroid_script/5.4-arm-translation-(libndk-and-libhoudini)
- Install & setup (DeepWiki) — https://deepwiki.com/casualsnek/waydroid_script/2-installation-and-setup
- issue #119 (não misturar libndk/libhoudini) — https://github.com/casualsnek/waydroid_script/issues/119
- Ivon's Blog — Waydroid Tips — https://ivonblog.com/en-us/posts/waydroid-tips/
- Waydroid prop options — https://docs.waydro.id/usage/waydroid-prop-options
