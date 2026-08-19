# 01 — Metodologia e ferramentas de RE da `libg.so` (Clash of Clans)

> **Status:** briefing de metodologia (verificável). Os **offsets concretos** não estão aqui —
> eles dependem da build da `libg.so` extraída do seu Waydroid (ver [02](02_ponteiro_raiz_e_structs.md)).
> Última atualização: 2026-07-22.

---

## Premissas confirmadas
- **Plataforma:** ⚠️ **CORRIGIDO em 2026-07-22 após extrair a `libg.so` real: a build entregue pela Play Store para o Waydroid é x86-64, NÃO ARM64.** O premissa original assumia AArch64, mas `file libg.so` retorna `ELF 64-bit LSB shared object, x86-64 ... for Android 24, built by NDK r27c, stripped`. A Play Store detectou o Waydroid como x86_64 e serviu a variante nativa (só existe `split_config.x86_64.apk`, sem split ARM). **Impacto na metodologia:** toda a parte de convenção de chamada muda — o `this` fica em **RDI** (não X0), os retornos em **RAX** (não X0), e as assinaturas de prólogo/pattern-scan são x86-64 (ex.: `push rbp; mov rbp, rsp` / `sub rsp, imm`), não AArch64 (`stp`/`sub sp`). Os exemplos de Frida abaixo que usam `args[0]`/X0 continuam válidos (Frida abstrai via `args[]`), mas qualquer pattern de bytes ou leitura de registrador precisa ser x86-64. **Também impacta a Lista A:** `TrampolineARM64::PatchADRP` em `native/src/layer1_native_hook.cpp` não se aplica — hooking inline aqui é x86-64 (relocação de `RIP`-relative, não `ADRP`).
- **Compilador/STL:** Clang → **libc++** (LLVM), NDK **r27c**, confirmado pelos símbolos `std::__ndk1::...` importados. → nosso `LibcxxVector`/`LibcxxSharedPtr` em `native/include/layer2_forensic_heap.hpp` já assumem esse layout.
- **Engine:** própria da Supercell ("Logic"), **não** é Unity/Unreal. Logo, dumpers de engine (UE-Dumper, Il2CppDumper) **não servem** diretamente.
- **Símbolos:** **confirmado stripped** — `r2 -qc iI` retorna `stripped true`, `lsyms false`. Sem símbolos exportados úteis (só JNI e imports libc++) e **sem nomes de RTTI** (busca por typeinfo mangled names e por nomes de classe tipo `TownHall`/`Building`/`LogicGameObject` não retorna nada). → ferramentas que dependem de RTTI Itanium (ex.: `vtable-dumper`) **falham**, como previsto; o caminho é **pattern scanning** (assinaturas de bytes) + análise dinâmica.

### Layout do binário (radare2, 2026-07-22)
- `.text`  — vaddr `0x005dd100`, tamanho `0x1089b62` (~17 MB) — código.
- `.rodata`— vaddr `0x001ed600`, tamanho `0x134808`.
- `.data.rel.ro` — vaddr `0x0166c5b0`, tamanho `0xb8a80` (~756 KB) — **é aqui que ficam as V-Tables** (RELRO full: relocadas na carga e depois marcadas somente-leitura). Alvo principal do scan estático de vtables.
- `.data` — vaddr `0x0172ada0`, tamanho `0xaa2b8`.
- Base address `0x0`, PIC, RELRO full, canary on.

---

## Fluxo de trabalho recomendado (estático + dinâmico)

O padrão da indústria para uma `.so` ARM64 stripped é **combinar**:

1. **Estático (Ghidra ou IDA Pro)** — mapear a estrutura, achar candidatos a funções (tick de update, construtores de entidade), identificar acessos ao `this` e offsets de campo.
2. **Dinâmico (Frida)** — validar em runtime: hookar as funções candidatas, imprimir endereços reais, dumpar V-Tables, encontrar o ponteiro-raiz de entidades (o passo mais difícil — ver [02](02_ponteiro_raiz_e_structs.md)).

Ghidra é gratuito e tem bom suporte AArch64; IDA Pro + Hex-Rays é mais rápido no descompilador mas pago. Comece pelo Ghidra.

---

## Frida no Android/Waydroid — o essencial

Frida é o toolkit de instrumentação dinâmica padrão ([frida.re](https://frida.re/)). Ele injeta scripts JS num processo e permite hookar qualquer função, ler/escrever memória e escanear por padrões — sem código-fonte ([RedFox: Native Modules with Frida](https://www.redfoxsec.com/blog/exploring-native-modules-in-android-with-frida)).

### Setup (dentro do Waydroid com root)
```bash
# no host: instalar o cliente
pip install frida-tools
# baixar frida-server ARM64 (versão CASADA com o frida-tools) e empurrar pro Waydroid via adb
adb push frida-server /data/local/tmp/
adb shell "chmod 755 /data/local/tmp/frida-server && /data/local/tmp/frida-server &"
# listar processos
frida-ps -U
```

### Achar a base da libg.so e enumerar exports/imports
```javascript
// frida -U -f com.supercell.clashofclans -l base.js
const mod = Process.getModuleByName("libg.so");
console.log("base:", mod.base, "size:", mod.size);
console.log("path:", mod.path);
// se houver algum export (raro em stripped):
mod.enumerateExports().slice(0, 20).forEach(e => console.log(e.type, e.name, e.address));
```

### Pattern scanning para achar função stripped
Quando não há símbolos, localiza-se por assinatura de bytes ([8kSec: Memory Scanning in Android](https://www.8ksec.io/advanced-frida-usage-part-9-memory-scanning-in-android/)):
```javascript
const mod = Process.getModuleByName("libg.so");
// exemplo de prólogo AArch64 típico (sub sp / stp) — a assinatura real você levanta no Ghidra
const pattern = "FF 43 01 D1 F4 4F 02 A9";
Memory.scan(mod.base, mod.size, pattern, {
  onMatch(addr) { console.log("match @", addr, "offset:", addr.sub(mod.base)); },
  onComplete() { console.log("scan done"); }
});
```

### Hookar uma função candidata e inspecionar o `this` (X0 em AArch64)
```javascript
Interceptor.attach(ptr(mod.base).add(0xOFFSET_DA_FUNCAO), {
  onEnter(args) {
    const self = args[0];          // 'this' em ABI AArch64 = X0
    const vptr = self.readPointer(); // offset 0 = vptr
    console.log("this:", self, "vptr:", vptr, "vtable offset:",
                vptr.sub(mod.base));
  }
});
```

---

## Dump de V-Tables — o que funciona em ARM64 stripped

| Ferramenta | Serve? | Observação |
|---|---|---|
| **Frida (memory scan + Interceptor)** | ✅✅ | O caminho principal: dumpar vptr real em runtime a partir de objetos vivos. |
| **Ghidra** (+ scripts de RTTI) | ✅ | Estático; sem RTTI você reconstrói V-Tables manualmente pelos construtores. |
| **radare2 / Cutter** (`avrr` = analyze vtables) | ✅ | Alternativa livre; parseia V-Tables. |
| **Virtuailor** (IDAPython) | ⚠️ | Reconstrói V-Tables com suporte AArch64 (via GDB remoto), mas é IDA. |
| **vtable-dumper** (Ponomarenko) | ❌ | Depende de símbolos RTTI Itanium → falha em binário stripped. |

Fontes: [awesome-reverse-engineering](https://github.com/alphaSeclab/awesome-reverse-engineering/blob/master/Readme_en.md), [Braincoke: Android RE with Frida](https://braincoke.fr/blog/2021/03/android-reverse-engineering-for-beginners-frida/).

---

## Recursos da comunidade (private servers) — o que dá e o que NÃO dá

A comunidade de RE do CoC é **grande**, mas focada em **rede/protocolo e nas tabelas de dados (CSV)**, **não** em offsets de memória em runtime. Isso é uma distinção crucial:

- **SC-DevTeam / Pinocchio** ([github.com/SC-DevTeam](https://github.com/SC-DevTeam)) — "all-in-one reverse" de CoC/CR/BB/HayDay; ferramentas de **packet dump, proto parser, encriptação** (`GDumper`, `node-coc-proxy`, `SCKeys`, `coc-patcher`).
- **CoCSharp** ([FICTURE7/CoCSharp](https://github.com/FICTURE7/CoCSharp)) — servidor .NET; `CoCSharp.Logic` tem classes `Village`, `Building`, `Trap`, `Obstacle`; `CoCSharp.Csv` lê as tabelas CSV do jogo (hitpoints, dps, IDs). **Unmaintained**, mas ótima referência de *lógica* e *IDs de dados*.
- **Supercell.Magic** ([Mimi8298/Supercell.Magic](https://github.com/Mimi8298/Supercell.Magic)) — servidor privado 9.256.x.
- **UCS / RetroClash / cocct** — outros emuladores de servidor.

**O que você TIRA daí:** os **data IDs** (cada prédio/tropa tem um ID numérico nas CSVs), a taxonomia de classes lógicas, e como o jogo estrutura logicamente a vila. Isso resolve os itens de *taxonomia* (nosso `EntityType` / `type_id`) e de *sentido dos campos*.

**O que você NÃO tira daí:** os **offsets em memória** da `libg.so` (vptr de cada classe, offset de `pos_x`/`hp` dentro da struct). O protocolo de rede ≠ layout de memória. Esses offsets continuam sendo trabalho seu com Frida+Ghidra.

Ref. adicional sobre a encriptação/logic: [Giovanni Rocca — SuperCell encryption RE](http://www.giovanni-rocca.com/clash-clans-supercell-new-encryption-reverse-engineering/).

---

## Decisão / próximos passos
1. ✅ **Extrair a `libg.so` do Waydroid** (ver [03](03_waydroid_fedora_setup.md)) — feito em 2026-07-22, em `~/.local/share/coc-digital-twin/libg.so`.
2. ✅ **Inventário estático de V-Tables** (radare2 + script próprio) — feito em 2026-07-22. Em vez de Ghidra GUI, usamos **radare2** (CLI, scriptável) + um scan direto das relocações. Ver seção "Inventário estático" abaixo. Resultado: **5.229 V-Tables candidatas** mapeadas por endereço, salvas em `~/.local/share/coc-digital-twin/vtable_inventory.txt` (script reproduzível em `vtable_scan.py` ao lado).
3. ⏳ **Rodar Frida** para validar dinamicamente e dumpar V-Tables reais, mapeando endereço→classe (ver [02](02_ponteiro_raiz_e_structs.md)). **Este é o passo que NOMEIA as vtables** — sem RTTI, o inventário estático só tem endereços anônimos; é o hook dinâmico dos construtores no processo vivo que diz "esta vtable = TownHall". Requer `frida-server` **x86_64** (não ARM64, por causa da arquitetura corrigida) empurrado pro Waydroid.
4. ⏳ Cruzar os **data IDs** do CoCSharp/CSV com as V-Tables encontradas para preencher `RegisterClassVTable(...)`.

## Inventário estático de V-Tables (2026-07-22)

Método (100% CLI, reproduzível via `~/.local/share/coc-digital-twin/vtable_scan.py`): com PIC + full RELRO, cada slot de vtable é uma relocação `R_X86_64_RELATIVE` cujo `r_offset` cai em `.data.rel.ro` e cujo addend aponta para `.text`. Relocações consecutivas (de 8 em 8 bytes) formam uma vtable. Parseando `.rela.dyn` direto do ELF:

- **77.088** slots (ponteiros de método virtual) dentro de `.data.rel.ro` apontando para `.text`.
- Agrupados em **5.229 vtables** candidatas (≥2 métodos cada).
- Distribuição por nº de métodos virtuais: 2-3 → 1.298; 4-9 → 2.035; 10-19 → 871; 20+ → 1.025.
- Maiores: duas de 332 métodos, uma de 165, várias de ~126-127 (provavelmente as classes-base da hierarquia `LogicGameObject`/`GameObject`).

**Limite desta fase:** o inventário é anônimo (só endereços). Casar endereço↔classe (`TownHall`, `Cannon`, etc.) e achar os offsets de campo (`pos_x`/`hp`/`id`) exige a fase dinâmica (Frida, passo 3). O inventário serve como (a) lista de alvos a validar em runtime e (b) forma de confirmar, no processo vivo, que um vptr lido de um objeto realmente bate com uma dessas 5.229 entradas.

## Fontes
- Frida — https://frida.re/
- RedFox — Native Modules in Android with Frida — https://www.redfoxsec.com/blog/exploring-native-modules-in-android-with-frida
- 8kSec — Memory Scanning in Android — https://www.8ksec.io/advanced-frida-usage-part-9-memory-scanning-in-android/
- Braincoke — Android RE for beginners (Frida) — https://braincoke.fr/blog/2021/03/android-reverse-engineering-for-beginners-frida/
- awesome-reverse-engineering — https://github.com/alphaSeclab/awesome-reverse-engineering
- SC-DevTeam — https://github.com/SC-DevTeam
- CoCSharp — https://github.com/FICTURE7/CoCSharp
- Supercell.Magic — https://github.com/Mimi8298/Supercell.Magic
- Giovanni Rocca — CoC encryption RE — http://www.giovanni-rocca.com/clash-clans-supercell-new-encryption-reverse-engineering/
