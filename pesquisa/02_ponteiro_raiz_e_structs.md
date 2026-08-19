# 02 — Ponteiro-raiz de entidades e layout dos structs (o mais crítico)

> **Status:** metodologia + tabelas a preencher. Este é o item que **bloqueia todo o resto**:
> sem o ponteiro-raiz e os offsets de campo, o `CollectEntities()` do middleware não tem o que ler.
> Última atualização: 2026-07-22.

---

## Por que este é o gargalo
Nosso `VTableResolver::IdentifyObject` já sabe dizer *o que* é um objeto a partir do vptr.
Faltam duas coisas que **só existem na build real** da `libg.so`:

- **(A) O ponteiro-raiz** → onde começa a lista de todas as entidades vivas.
- **(B) Os offsets de campo** → onde, dentro de cada objeto, ficam id / posição / HP / etc.

Nenhum dos dois é publicável — o RE da comunidade cobre protocolo de rede e CSVs, não memória em runtime (ver [01](01_re_metodologia_libg.md)). Você levanta com Frida + Ghidra.

---

## (A) Encontrar o ponteiro-raiz de entidades

Numa engine própria (a "Logic" da Supercell), a vila é um objeto (`LogicLevel`/`LogicGameObjectManager`) que contém arrays de `LogicGameObject`. Três táticas, da mais fácil à mais robusta:

### Tática 1 — Hookar o loop de tick e inspecionar o `this`
O update por frame recebe (ou tem acesso a) o gerenciador. Ache a função de tick (candidata no Ghidra: função grande chamada ~a cada frame, itera sobre um array chamando um método virtual em cada elemento — típico `for (obj : objects) obj->update(dt)`), hooke e inspecione:
```javascript
const mod = Process.getModuleByName("libg.so");
Interceptor.attach(mod.base.add(0xTICK_OFFSET), {
  onEnter(args) {
    const self = args[0];   // provável LogicLevel/manager
    // varra os primeiros ~0x200 bytes procurando um trio libc++ vector (begin/end/cap):
    for (let off = 0; off < 0x200; off += 8) {
      const begin = self.add(off).readPointer();
      const end   = self.add(off + 8).readPointer();
      if (!begin.isNull() && end.compare(begin) > 0) {
        const n = end.sub(begin).toInt32() / 8;   // ptrs de 8 bytes
        if (n > 0 && n < 5000) console.log(`vector? off=0x${off.toString(16)} count=${n}`);
      }
    }
  }
});
```
O `off` que der uma contagem plausível de objetos é forte candidato à lista de entidades.

### Tática 2 — Rastrear alocações de objetos
Hooke o `operator new`/construtor de um tipo conhecido (achado via V-Table) e registre onde o ponteiro é armazenado. Subindo a cadeia, chega-se ao container.

### Tática 3 — Frida `Memory.scan` por vptr conhecido
Uma vez que você tenha o endereço de uma V-Table (ex.: do Town Hall), escaneie a heap por ponteiros para ela → acha instâncias vivas → suba a cadeia de referências até o container. `Process.enumerateRanges('rw-')` para delimitar a heap.

> **Cuidado (Scudo):** no Android 11+ os objetos **não são contíguos** na heap (o Scudo faz shuffling/guard pages — ver [04](04_injecao_scudo_libcpp.md)). Por isso **varrer a heap linearmente é frágil**; sempre parta do ponteiro-raiz + iteração pela estrutura, não de "escanear tudo".

---

## (B) Levantar os offsets de campo dentro do objeto

Depois de ter uma instância viva (endereço `this`), descubra os offsets:

### Método Frida — hexdump + correlação
```javascript
// self = endereço de uma entidade viva (ex.: um prédio com HP conhecido no jogo)
console.log(hexdump(self, { offset: 0, length: 0x100, ansi: true }));
```
Correlacione com o estado visível no jogo:
- **vptr** em `+0x00` (confirma tipo).
- **HP:** você sabe o HP máximo do prédio pela wiki/CSV → procure esse valor (como `float` ou `int32`) no dump; ataque o prédio e veja qual campo **decai** → é o `current_hp`; o que fica fixo é `max_hp`.
- **Posição:** ande com a câmera / compare dois prédios em tiles diferentes → os campos que diferem de forma coerente com a grade são `pos_x`/`pos_y`.
- **id/level:** valores pequenos e estáveis; cruze com os data IDs do CoCSharp.

### Método Ghidra — acessos ao `this`
No descompilador, os campos aparecem como `*(int *)(this + 0xNN)`. Renomeie conforme for validando no Frida. A ferramenta `ida-vtable-tools` (se usar IDA) tipa o 1º argumento como `this` automaticamente.

---

## Encoding dos campos — o que investigar
| Campo | Hipóteses a testar | Como confirmar |
|---|---|---|
| `pos_x`, `pos_y` | tile inteiro? **subtile** (o CoC costuma usar 1 tile = 512 subtiles)? float? | Mover objeto/comparar; ver se o passo é 1 ou 512. |
| `current_hp`/`max_hp` | `int32` ou `float`? | Atacar e observar decaimento no dump. |
| `entity_id` | `int32` global incremental | Estável por instância. |
| `level` | `int` pequeno | Cruzar com o nível real no jogo. |
| `state`/flags | bitfield | Observar mudança ao selecionar/destruir. |

> **Grid do jogo:** o mapa jogável do CoC é ~**44×44 tiles**. Nosso `clash_env` usa um grid 50×50 arbitrário — ao ter o encoding real, ajuste a conversão *coordenada-de-entidade → célula* em `utils/clash_env.py` (`_get_observation`) e, se for subtile, divida por 512.

---

## Resultados da RE — build x86-64 (levantado em 2026-07-22)

> ⚠️ Estes offsets são desta build específica da `libg.so` (x86-64, NDK r27c, sha256
> `4df1813d…`). Outra build vai ter outros offsets — o método (não os números) é o que
> transfere. Levantado **sem Frida** (o CoC detecta e crasha — ver [06](06_anticheat_risco_ban.md)),
> com leitor externo passivo via `/proc/<pid>/mem` (`~/.local/share/coc-digital-twin/mem_reader.py`),
> por análise de frequência de vptr cruzada com o inventário exato da vila (JSON da API do jogo).

### V-Tables identificadas (offset base-relativo = endereço_runtime − base_da_libg)
Método: histograma de todos os vptr vivos na heap, casado com contagens exatas do inventário.
Todas ficam num cluster contíguo (`0x1680`–`0x1685`) com ~126-127 métodos virtuais — a família `LogicGameObject`.

| Classe (inferida) | vtable (base+) | nº métodos | nº instâncias | como foi confirmada |
|---|---|---|---|---|
| `LogicBuilding` (todos os prédios não-muralha) | **`0x01680d20`** | 127 | 52 | contagem 52 = prédios da vila; data-ids batem 22/22 |
| `LogicWall` | **`0x016851b0`** | 127 | 175 | contagem = 175 muralhas exatas |
| `LogicObstacle` (árvores/pedras) | **`0x01682f60`** | 126 | 23 | data-ids batem 8/8 com obstáculos |
| `LogicTrap` (armadilhas) | **`0x01683b60`** | 126 | 15 | contagem = 15 armadilhas |
| `LogicGameMode`/`LogicLevel` (candidato) | `0x016893d8` | 332 | 1 | maior classe, única |
| não classificadas | `0x01683f60` (20), `0x01684360` (5), `0x01681ab8` (1) | — | — | contagens sem match direto no inventário da vila principal |

**IMPORTANTE — tipo do prédio NÃO é a vtable:** todos os 52 prédios compartilham `LogicBuilding` (`0x01680d20`);
canhão/mina/armazém se distinguem pelo **data-id** lido do `LogicBuildingData*` (ver cadeia abaixo).
Mapear data-id → nome/`EntityType` usa as CSVs do CoCSharp (ainda a fazer).

### Offsets de campo (a partir do endereço do objeto = onde está o vptr)
| campo | offset | tipo | observação |
|---|---|---|---|
| `vptr` | `+0x00` | uintptr_t | identifica a classe (tabela acima) |
| ptr p/ sub-objeto núcleo | `+0x08` | ptr | "componente núcleo" do `LogicGameObject` (posição + data) |
| `entity_id` | `+0x20` | int32 | ID global único, esquema `500000000+` |
| `level` | `+0xd0` | int32 | **0-indexed** (muralha nível 7 → valor 6) |

### Sub-objeto núcleo (`*(obj+0x08)`) — posição e tipo
| campo | offset no sub-objeto | tipo | observação |
|---|---|---|---|
| `Logic*Data*` (ponteiro de dados) | `+0x18` | ptr | → `+0x18` = **data-id** (int32) |
| `pos_x` | `+0x20` | int32 | **subtile**; `pos_x / 512` = tile X |
| `pos_y` | `+0x24` | int32 | **subtile**; `pos_y / 512` = tile Y |
| `entity_id` (back-ref) | `+0x30` | int32 | mesmo valor de obj+0x20 |

### Componente de combate (`*(obj+0xa8)`) — HP
| campo | offset no componente | tipo | observação |
|---|---|---|---|
| `current_hp` | `+0xcc` | int32 | **só populado DURANTE a batalha**; no scout vem 0/constante. Decai ao apanhar, vai a 0 quando destruído (levantado com `--hp-hunt`: 32/37 prédios zeraram este campo num ataque real). Provável ponto-fixo (pico ~280000 num TH6 ≈ HP×128). |

`max_hp`: não há campo estático confiável no scout (HP é de combate). Estratégia adotada: rastrear o **pico** de `current_hp` por `entity_id` (no início do combate `current==max`), feito no `ExternalMemoryReceiver`. A razão `current/max` fica correta e é o que o grid do RL usa (independe da escala/ponto-fixo).

### Cadeia de resolução de TIPO (data-id)
```
data_id = *(int32*)( *(void**)( *(void**)(obj + 0x08) + 0x18 ) + 0x18 )
          └─ obj+0x08 (sub-obj núcleo) ─┘└─ +0x18 (Logic*Data*) ─┘└ +0x18 (id) ┘
```
Confirmado para `LogicBuilding` (22 tipos, ex.: `1000000 x4`, `1000002 x6`, `1000008 x5`…) e
`LogicObstacle` (8 tipos, `8000000 x9`…) — **casamento exato** com o inventário. Faixas de data-id:
prédios `1000000+`, tropas `4000000+`, obstáculos `8000000+`, armadilhas `12000000+`, decorações `18000000+`.

### Escala e grid
- **1 tile = 512 subtiles** (posição inteira em subtiles, tile-alinhada para prédios).
- Grid jogável ~44×44 → ajustar `utils/clash_env.py` (`_get_observation`) para dividir por 512 e usar 44, não 50.

### Ainda PENDENTE
- ~~HP~~ **RESOLVIDO (2026-07-22)**: `current_hp` em `*(obj+0xa8)+0xcc` (int32), levantado com `--hp-hunt` durante um ataque real. É dado de combate (só populado na batalha). `max_hp` via pico rastreado. Ver tabela "Componente de combate" acima. Integrado no `mem_reader._read_all_entities` e no `ExternalMemoryReceiver`.
- **Ponteiro-raiz / lista de entidades**: não foi necessário para o levantamento (o leitor externo varre a heap inteira por vptr conhecido, contornando o problema do root pointer). Para o middleware *injetado* (Camada 2) ainda vale achar a lista; para o **leitor externo** (rota preferida da Seção 6), a varredura por vptr já basta.
- **Classes não classificadas** (`0x01683f60`=20, `0x01684360`=5, `0x01681ab8`=1) e o mapa data-id→nome (via CSV do CoCSharp).

### Ferramenta
`~/.local/share/coc-digital-twin/mem_reader.py` (roda no host como `sudo python3`, recebe o PID *host* do jogo). Modos: `--scan` (histograma de vptr), `--dump <vt>` (hexdump+diff de instâncias), `--fields <vt>` (perfil de campos), `--chase <vt>` (acha posição em componentes), `--comp <vt> <ptr_off>` (perfila um componente), `--dataid <vt>` (acha data-id / tipo).

## Fontes
- CoCSharp (classes lógicas + leitor de CSV) — https://github.com/FICTURE7/CoCSharp
- Frida memory scanning — https://www.8ksec.io/advanced-frida-usage-part-9-memory-scanning-in-android/
- Frida API (Memory, Interceptor, hexdump) — https://frida.re/docs/javascript-api/
- (contexto isométrico/tiles) ver [05](05_atuador_isometrico_input.md)
