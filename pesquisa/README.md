# Pesquisa — o que falta para o Gêmeo Digital operar contra o jogo real

Resultado da execução dos 6 prompts de pesquisa. Cada arquivo é um **briefing de metodologia
fundamentado em fontes**, com o **como descobrir** — os valores concretos que dependem da build
da `libg.so` (offsets, endereços) ficam como espaço a preencher, porque não existem publicamente
e variam por versão do jogo.

## Arquivos
| # | Arquivo | Cobre | Bloqueia? |
|---|---|---|---|
| 01 | [re_metodologia_libg](01_re_metodologia_libg.md) | Fluxo Frida+Ghidra, dump de V-Table em ARM64 stripped, recursos da comunidade (CoCSharp, SC-DevTeam) | — |
| 02 | [ponteiro_raiz_e_structs](02_ponteiro_raiz_e_structs.md) | **O gargalo:** achar a lista de entidades e os offsets de campo (id/pos/HP) | 🔴 bloqueia tudo |
| 03 | [waydroid_fedora_setup](03_waydroid_fedora_setup.md) | Instalar/rootar Waydroid, ARM, bind mount, ADB, extrair a `libg.so` | 🟠 fazer 1º |
| 04 | [injecao_scudo_libcpp](04_injecao_scudo_libcpp.md) | Injeção (Zygisk/ptrace), hooking com **Dobby**, Scudo cookie, layout libc++ | — |
| 05 | [atuador_isometrico_input](05_atuador_isometrico_input.md) | Projeção isométrica grid→tela, deploy, input via ADB/minitouch | — |
| 06 | [anticheat_risco_ban](06_anticheat_risco_ban.md) | Integridade de código, anti-ptrace, anti-hook, risco de ban | — |
| 07 | [defesas](07_defesas.md) | Referência de stats das defesas por nível (HP/DPS/alcance/splash/alvos) — `utils/defense_stats.py` | ✅ dados prontos |
| 08 | [tropas](08_tropas.md) | Referência de stats das tropas por nível (HP/DPS/espaço/voa/alvo) — `utils/troop_stats.py` | ✅ dados prontos |
| 09 | [analise_tatica](09_analise_tatica.md) | Achar brechas na vila (mapa de ameaça, zonas mortas, clusters de feitiço, lado fraco) → priors p/ o RL | 🟢 planejamento |
| 10 | [feiticos_pendentes](10_feiticos_pendentes.md) | Plano de implementação dos feitiços no motor (`combat_sim.py`): Freeze/Poison/Earthquake/Clone/Jump/etc., e o problema estrutural de "zona persistente" | 🟡 fora do treino atual |

## Ordem de execução recomendada
1. **03** (Waydroid) → extrai a `libg.so`, sem a qual nada avança.
2. **01 → 02** (RE) → o coração do projeto: V-Tables, ponteiro-raiz, offsets de campo.
3. **04 / 05 / 06** em paralelo, conforme necessário.

## Decisões técnicas que já saíram da pesquisa
- **Hooking:** avaliar **Dobby** no lugar do nosso `TrampolineARM64` manual (ele já resolve relocação ADRP). — ver 04
- **Atuador:** implementar via **ADB do Waydroid** (`utils/adb_actuator.py`), desacoplado da Camada 1. — ver 05
- **RE:** caminho é **Frida (dinâmico) + Ghidra (estático)**; `vtable-dumper` não serve (binário stripped). — ver 01
- **Repensar Camada 1:** para telemetria **só-leitura**, um leitor externo via `process_vm_readv` (sem hook, sem patch de `.text`, sem ptrace) tende a ser mais robusto e furtivo que o middleware injetado. — ver 06
- **Comunidade:** os private servers dão **data IDs e lógica (CSV)**, mas **não** os offsets de memória. — ver 01/02

## Aviso
Todo o material assume um projeto **pessoal de pesquisa** em ambiente próprio (Waydroid na sua
máquina). Injetar/instrumentar o cliente do Clash of Clans viola os ToS da Supercell e pode
banir a conta — use conta descartável e assuma o risco conscientemente (ver 06).
