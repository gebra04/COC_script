# 04 — Injeção, hooking ARM64 (Dobby), Scudo e libc++

> **Status:** técnico/verificável. Detalhes que fecham as Camadas 1 e 2 no ambiente Android.
> Última atualização: 2026-07-22.

---

## 1. Método de injeção do middleware no processo do jogo

| Método | Viável no Waydroid c/ root? | Notas |
|---|---|---|
| **ptrace injector** | ✅ | Injeta `.so` via `ptrace(ATTACH)` + `dlopen` remoto. Simples de entender; sensível a anti-debug (ver [06](06_anticheat_risco_ban.md)). |
| **Zygisk (Magisk)** | ✅✅ | Módulo carregado pelo Zygote **antes** do processo do app subir → mais estável e furtivo que ptrace. Recomendado com Magisk já instalado. |
| **Riru** | ⚠️ | Antecessor do Zygisk; hoje Zygisk é o padrão. |
| **LD_PRELOAD via wrapper** | ⚠️ | Funciona se você controlar o launch; no Android/Waydroid é mais chato de encaixar. |

**Recomendação:** como o [03](03_waydroid_fedora_setup.md) já instala Magisk, use **Zygisk** para carregar o middleware, com fallback de **ptrace injector** para prototipagem rápida.

---

## 2. Hooking ARM64: use o Dobby em vez do trampoline à mão

Nosso `native/include/layer1_native_hook.hpp` tem um `TrampolineARM64::PatchADRP` **manual**. O problema que ele resolve (relocação de `ADRP`/`ADD` PC-relative ao mover o prólogo) é **exatamente** o que frameworks maduros já fazem — e melhor.

- **Dobby** ([jmpews/Dobby](https://deepwiki.com/jmpews/Dobby)) — framework de inline hook multi-arch. Seu subsistema **InstructionRelocation** move o prólogo preservando semântica, e ele tem trampolines dedicados (`ARM64_ADRP_ADD_BR`, `ARM64_LDR_BR`, `ARM64_B_XXX`) escolhidos por alcance do salto. É o padrão em Android ARM64.
- Alternativas: **And64InlineHook** ([rprop.github.io/And64InlineHook](https://rprop.github.io/And64InlineHook/)) — lib leve só p/ ARM64; **HookZz** ([killvxk/HookZz](https://github.com/killvxk/HookZz)) — precursor do Dobby.

### Uso típico do Dobby
```cpp
#include "dobby.h"
void* g_orig_tick = nullptr;
void hooked_tick(void* self, float dt) {
    CollectAndPublish(self);          // nossa Camada 2/3 por frame
    ((void(*)(void*,float))g_orig_tick)(self, dt);
}
// instalar:
DobbyHook((void*)(libg_base + TICK_OFFSET),
          (void*)hooked_tick, (void**)&g_orig_tick);
```
> **Decisão sugerida:** substituir o hook manual por Dobby no `middleware_main.cpp` (troca o `sleep(16.6ms)` do stub pelo hook real no tick). Manter o `layer1_native_hook.hpp` como referência/estudo. Ver issue de sucesso/erros em Android 10 arm64: [Dobby #132](https://github.com/jmpews/Dobby/issues/132).

---

## 3. Scudo Hardened Allocator (Android 11+)

Nosso `ScudoAuditor` valida o header de chunk, mas recebe o **cookie** pronto. Detalhes reais:

### Estrutura e checksum
- O header de chunk é **checksummed**; a corrupção é detectada no acesso ([AOSP: Scudo](https://source.android.com/docs/security/test/scudo)).
- O checksum é um **CRC32** sobre: o **cookie** global (32 bits, aleatório na inicialização), o **ponteiro do chunk**, e os **8 bytes do header** com o campo checksum zerado ([LLVM: Scudo docs](https://llvm.org/docs/ScudoHardenedAllocator.html)).
- Resultado: o CRC32 tem os 16 bits altos e baixos **XORados** entre si → **checksum de 16 bits** armazenado ([L3Harris: Scudo internals](https://www.l3harris.com/newsroom/editorial/2023/10/scudo-hardened-allocator-unofficial-internals-documentation)).
- **Não é criptograficamente forte** (vulnerável a colisões), mas serve para detectar corrupção/leituras erradas.

### Como obter o cookie em runtime
O cookie de 32 bits fica na instância do **allocator de topo** (classe estática). Caminhos:
1. Com Frida/Ghidra, achar o símbolo/estrutura do allocator do Scudo na `libc.so`/`libscudo` e ler o campo `Cookie`.
2. Referências detalhadas de layout e exploração: [WOOT'24 — Exploiting Android's Hardened Allocator (Mao)](https://www.usenix.org/system/files/woot24-mao.pdf) e [slides](https://www.nohat.it/slides/2024/mao.pdf).

### Implicação para a Camada 2 (importante)
O Scudo faz **randomização espacial** e **guard pages** → objetos **não são contíguos** e tocar uma guard page dá **SIGSEGV**. Consequências:
- **Nunca varra a heap linearmente.** Parta sempre do ponteiro-raiz (ver [02](02_ponteiro_raiz_e_structs.md)) e itere pela estrutura.
- Antes de desreferenciar um ponteiro suspeito, **valide o chunk** (`ScudoAuditor::ValidateChunk`) ou proteja com leitura segura (`process_vm_readv`, que não crasha — retorna erro).

---

## 4. libc++ no Android (NDK) — layout ARM64 (64-bit)

Confirma o que já assumimos em `layer2_forensic_heap.hpp`:

| Tipo | Layout (libc++) | Tamanho |
|---|---|---|
| `std::vector<T>` | `__begin_`, `__end_`, `__end_cap_` (3 ponteiros) | 24 bytes |
| `std::shared_ptr<T>` | `__ptr_` (obj) + `__cntrl_` (control block c/ contadores) | 16 bytes |
| `std::string` | união SSO/heap (SSO: strings curtas inline; heap: cap/size/data) | 24 bytes |

- Nosso `LibcxxVector<T>` (`my_first`/`my_last`/`my_end`) == `__begin_`/`__end_`/`__end_cap_`. ✅
- Nosso `LibcxxSharedPtr<T>` (`ptr` + `control_block` com `shared_owners`/`weak_owners`) == `__ptr_`/`__cntrl_`. ✅
- **Atenção `std::string`:** por causa do **SSO**, strings curtas ficam inline (sem ponteiro para heap). Se algum campo de entidade for string (ex.: nome), trate os dois casos.

---

## Decisões que saem daqui
1. **Injeção:** Zygisk (principal) + ptrace injector (protótipo).
2. **Hooking:** adotar **Dobby**; hookar o tick real e chamar a coleta por frame (remove o `sleep` do stub).
3. **Scudo:** implementar extração do cookie e **validar antes de desreferenciar**; abandonar qualquer varredura linear de heap.
4. **libc++:** layout confirmado; adicionar tratamento de SSO se houver campos string.

## Fontes
- Dobby (DeepWiki) — https://deepwiki.com/jmpews/Dobby
- Dobby issue #132 (Android arm64) — https://github.com/jmpews/Dobby/issues/132
- And64InlineHook — https://rprop.github.io/And64InlineHook/
- HookZz — https://github.com/killvxk/HookZz
- AOSP Scudo — https://source.android.com/docs/security/test/scudo
- LLVM Scudo docs — https://llvm.org/docs/ScudoHardenedAllocator.html
- L3Harris — Scudo internals — https://www.l3harris.com/newsroom/editorial/2023/10/scudo-hardened-allocator-unofficial-internals-documentation
- WOOT'24 — Exploiting Android's Hardened Allocator — https://www.usenix.org/system/files/woot24-mao.pdf
