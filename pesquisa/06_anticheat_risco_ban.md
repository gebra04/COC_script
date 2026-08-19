# 06 — Proteções anti-tamper, detecção e risco de ban

> **Status:** conceitual/verificável. Escopo: **entender os riscos** de injetar/hookar a `libg.so`
> para leitura de telemetria, num projeto pessoal de pesquisa. Não é um guia de evasão para
> trapaça competitiva.
> Última atualização: 2026-07-22.

---

## Contexto e limites
O objetivo declarado é **ler** telemetria da memória (gêmeo digital / RL), não modificar
mecânicas de jogo. Ainda assim, injetar código e instalar hooks:
- **viola os Termos de Serviço da Supercell** e pode **banir a conta** (decisão consciente do humano — use conta descartável);
- esbarra em proteções anti-tamper do cliente, descritas abaixo para você saber o que esperar.

As fontes canônicas de referência são o **OWASP MASTG** (testes de resiliência) — material defensivo/educacional.

---

## 1. Verificação de integridade de código (detecta inline hook)
Apps sensíveis fazem **checksum/hash das páginas `.text`** de bibliotecas (próprias e do sistema como `libc.so`/`libart.so`) e comparam com o valor de disco; um inline hook altera bytes → detecção ([MASTG anti-tamper](https://mas.owasp.org/MASTG/tests/android/MASVS-RESILIENCE/MASTG-TEST-0046/), [Medium: securing Android apps](https://medium.com/@prahaladsharma4u/securing-android-apps-against-dynamic-attacks-and-reverse-engineering-8bb608103827)).

**Como saber se o CoC faz isso:** procurar, no Ghidra/Frida, rotinas que leem `/proc/self/maps`, mapeiam a própria `.text` e computam hash/CRC periodicamente. Se existir, um inline hook em `.text` é arriscado.

**Mitigação (para leitura):** preferir abordagens que **não patcham `.text`**:
- Ler memória **de fora** com `process_vm_readv` a partir de um processo separado (não altera bytes do alvo, não instala hook) — muito mais furtivo para *só leitura*.
- Se precisar de hook, considerar hook de **V-Table** (troca ponteiro em dado `.data`/heap) em vez de patch de `.text`, que alguns checks de integridade não cobrem.

> **Implicação de design:** para o gêmeo digital (só leitura), um **leitor externo via `process_vm_readv`** pode ser preferível ao middleware injetado — evita todo o vetor de detecção de integridade. Vale reavaliar a arquitetura da Camada 1 à luz disso.

---

## 2. Detecção de ptrace / anti-debug
- **TracerPid:** o app lê `/proc/self/status`; `TracerPid != 0` indica debugger/ptrace anexado ([MASTG-TEST-0046](https://mas.owasp.org/MASTG/tests/android/MASVS-RESILIENCE/MASTG-TEST-0046/), [recursively.review](https://recursively.review/2021/04/25/Android-Anti-debugging-Tricks-Part-1/)).
- **Self-ptrace:** o processo faz `ptrace(PTRACE_TRACEME)` em si mesmo; como só um tracer é permitido por vez, isso **bloqueia** um debugger externo posterior.

**Mitigação (conhecida, defensiva):** patch da chamada `ptrace` com NOP, hook de `ptrace`/leitura de `TracerPid` via Frida para forjar retorno, ou `LD_PRELOAD` de uma `.so` que intercepta ([GuidedHacking: bypass ptrace](https://guidedhacking.com/threads/bypass-ptrace-anti-debugger-in-android.17099/)). Não há método genérico — depende do mecanismo exato ([MASTG](https://mas.owasp.org/MASTG/tests/android/MASVS-RESILIENCE/MASTG-TEST-0046/)). **Novamente:** um leitor externo via `process_vm_readv` não usa ptrace e escapa dessa categoria.

---

## 3. Detecção anti-hook via LR/Frame Pointer
Técnica avançada: no prólogo de funções críticas, o app lê o **Link Register / Frame Pointer** (x30/x29) e verifica se o endereço de retorno cai **fora dos limites do módulo** (`dladdr` + `g_begin`/`g_end`), o que denuncia um trampoline de hook. É real em apps de segurança móvel (bancos). Reação típica: corromper a stack e crashar de forma não-rastreável.

**Relevância:** se o CoC empregar isso, hooks inline (Dobby/Frida) ficam detectáveis. Mais um argumento pró **leitura externa sem hook** para o caso de uso de telemetria.

---

## 4. Detecção de Frida / instrumentação
Apps procuram por artefatos do Frida: porta 27042, strings "frida" em `/proc/self/maps`, threads `gum-js-loop`, etc. ([Frida detection & bypass](https://qweraqq.github.io/security/2024/04/06/android-frida-detection-and-bypass.html)). Para **RE offline** (levantar offsets) isso não importa muito — você faz numa conta/ambiente de análise. Para **operação contínua**, evite depender de Frida em produção (use o middleware compilado ou leitura externa).

**Confirmado na prática em 2026-07-22**: com `frida-server` ativo (escutando em `0.0.0.0:27042` dentro do Waydroid) e o jogo já instalado/logado, `waydroid app launch com.supercell.clashofclans` resultou em **"Clash of Clans keeps stopping"**. Fechando o Waydroid, matando o `frida-server`, e reabrindo o jogo **sem** o Frida presente, o app abriu normalmente. Confirma detecção de Frida ativa no cliente (provavelmente checagem no `attach()`/init da engine, possivelmente porta 27042 ou artefato em `/proc/self/maps` — não isolamos qual exatamente). **Teste 2 (mesmo dia)**: jogo já aberto e estável (vila carregada, sem Frida). Ao subir o `frida-server` (escutando em `0.0.0.0:27042`) **sem sequer conectar** (`frida-ps`/`attach`), o jogo crashou imediatamente. Isso descarta a hipótese de "checagem só no cold-start" — a detecção é **ativa/periódica em background**, disparada pela mera presença do `frida-server` rodando no device (não pelo attach em si). Assinatura mais provável: a porta padrão `27042` (IOC clássico de Frida) ou o nome do processo/binário. Próximo teste: `frida-server` com porta customizada (`-l 0.0.0.0:<porta não-padrão>`) para ver se escapa de uma checagem ingênua baseada na porta default.

**Teste 3 e 4 (mesmo dia) — Frida descartado**: (3) `frida-server -l 0.0.0.0:9182` (porta não-padrão) → crashou igual; a porta não é o gatilho. (4) binário renomeado para `wd_helper` (`cp frida-server wd_helper`) e iniciado em porta não-padrão → crashou igual; o nome do processo/binário também não é o gatilho. **Conclusão: a detecção é por assinatura em memória (varredura por artefatos do Gum/Frida no espaço de endereço do device), não por IOC ingênuo (porta/nome).** Brigar com isso é uma corrida armamentista (frida-gadget, magisk-hide-frida, etc.) fora do escopo de um projeto de pesquisa read-only. **Decisão (2026-07-22): abandonar Frida e adotar a rota já recomendada na Conclusão de arquitetura desta seção — leitor externo via `process_vm_readv`/`/proc/<pid>/mem`**, que (a) não injeta nada no jogo, não seta `TracerPid`, é passivo/furtivo; (b) é a mesma tecnologia do middleware/reader final; (c) permite a fase dinâmica da RE (casar vptrs de objetos vivos com o inventário estático de 5.229 vtables) sem disparar o anti-Frida. A RE dinâmica passa a ser: dump de `/proc/<pid>/maps` (achar base da `libg.so`) + leitura externa da heap procurando qwords que caiam na região de vtables de `.data.rel.ro`.

---

## 5. Detecção server-side e risco de conta
- Supercell tem **validação server-side** e detecção de comportamento anômalo; ações impossíveis/temporização robótica podem sinalizar. Como o CoC valida a lógica no servidor (os private servers existem justamente porque o cliente fala um protocolo definido), **comportamento** conta tanto quanto integridade do cliente.
- **Play Integrity / SafetyNet:** um Waydroid rootado com Magisk **falha** attestation por padrão; alguns apps recusam rodar. O CoC historicamente roda em emulador, mas a postura pode mudar.

**Boas práticas (assumir o risco conscientemente):**
- **Conta descartável**, nunca a principal.
- Evitar padrões de input sobre-humanos (jitter/tempos aleatórios — o `deploy_policy.py` já introduz aleatoriedade nos pontos).
- Para pesquisa, priorizar **ataques a bases próprias / modo treino** quando possível, reduzindo exposição a matchmaking real.

---

## 6. LEITOR EXTERNO (`/proc/<pid>/mem`) TAMBÉM DETECTADO na build 18.400.22 (2026-08-19)

**A conclusão da Seção 4 está OBSOLETA para a build atual.** A arquitetura B (leitor
externo passivo, sem ptrace/injeção) foi adotada em 2026-07-22 justamente por ser
indetectável — validada então com `--live` rodando continuamente a ~200Hz por
período prolongado sem crash. Hoje, contra a build **18.400.22** (atualizada
2026-08-19), o padrão observado é **100% de correlação entre rodar o
`mem_reader.py` (mesmo em leitura pontual, sem loop) e o jogo cair em seguida**:

- Relatado pelo usuário: toda vez que abre o jogo com o `mem_reader.py` já
  rodando, crasha; toda vez que roda o `mem_reader.py` com o jogo já aberto,
  crasha também; sem rodar o script, o jogo funciona normalmente.
- Reproduzido nesta sessão via `adb logcat -d` cronometrado: `--dump 0x0`
  (leitura pontual, varre heap por instâncias de um endereço) não matou
  imediatamente; `--scan` (fase 1+2, varredura completa de ~1GB) → processo
  morreu **~1 segundo depois de o comando terminar** (`ActivityManager:
  Process ... has died: fg TOP`, sem log de OOM/lowmemorykiller antes —
  morte "limpa", sem sinal de pressão de memória do host desta vez). O
  Android tentou auto-restaurar o processo em foreground (`Start proc ...
  for next-top-activity`) e ele **morreu de novo em ~8 segundos**, sem
  nenhuma leitura nova rodando nesse intervalo — aí o sistema desistiu e
  caiu pro app drawer.
- Esse padrão (morte rápida após leitura + auto-restart falhando sozinho
  repetidamente) é mais consistente com **detecção ativa** (a engine
  percebe que sua própria memória foi lida por um processo externo — ex.:
  monitorando `/proc/self/maps`, `/proc/self/status` por handles/flags
  incomuns, ou um canary/checksum de heap que não bate) do que com pressão
  de memória do host (que também foi descartada numa tentativa anterior no
  mesmo dia: um host com pouca RAM livre coincidiu com uma queda, mas o
  padrão se repetiu depois com RAM disponível).
- **NÃO CONFIRMADO ainda**: o mecanismo exato de detecção (não isolamos se é
  a leitura de `/proc/<pid>/maps`, a abertura de `/proc/<pid>/mem`, ou o
  `read()`/`seek()` em si que dispara). Não confirmado se afeta a conta
  (nenhum teste de ban feito — os testes foram feitos numa conta de uso
  normal do usuário, não descartável, ver Seção 5 sobre esse risco).

**Isso invalida a decisão da Seção 4/Conclusão de arquitetura**: a arquitetura B
não é mais "a rota de menor detecção" — ela também está sendo pega, ao que tudo
indica pela mesma atualização que invalidou os offsets de V-Table (18.400.22,
2026-08-19). Ainda não há uma arquitetura de leitura viável identificada para
essa build. Antes de insistir em RE de offsets (que fica inútil se toda leitura
derruba o jogo), o próximo passo é entender/confirmar o mecanismo de detecção,
ou considerar que a leitura ao vivo do jogo real pode ter deixado de ser viável
nesta build — ver alternativas (ex.: reverter a versão instalada, capturar
telemetria só do modo Practice por período curtíssimo, ou aceitar que a Fase
1.5+ (simulação offline com gamefiles já extraídos) é o caminho sustentável daqui
pra frente, já que não depende de leitura ao vivo).

### RESOLVIDO na mesma sessão (2026-08-19, algumas horas depois): NÃO é detecção — é uma armadilha de páginas não-residentes, e tem correção

O parágrafo acima ficou registrado como estava no momento da investigação (não
apagar — mostra o raciocínio), mas a conclusão de "detecção ativa" estava
**errada**. Causa raiz real, isolada com um probe graduado
(`mem_reader.py --detect-probe 0..7`, cada nível toca progressivamente mais
memória) e confirmada via `/proc/<pid>/fd` + `/proc/<pid>/smaps` +
`/proc/<pid>/pagemap`:

- O jogo tem um fd `userfaultfd` aberto (confirmado). Existe pelo menos uma
  arena de heap **enorme** (~384 MiB observada) que fica **~98%
  NÃO-residente** — só uma fração pequena das páginas está fisicamente
  mapeada; o resto é espaço reservado (`mmap`) mas nunca escrito pelo
  próprio jogo.
- Ler essa região de ponta a ponta num `read()` contínuo (como o
  `--scan`/`--watch` faziam) força o kernel a **"faultar"** centenas/milhares
  dessas páginas nunca tocadas. O jogo então se **auto-encerra
  deliberadamente** (`exit(1)`, saída limpa — nunca um SIGSEGV/crash de
  verdade) alguns segundos depois. Isolado com um teste decisivo: tocar
  só **4 KiB de CADA região** (nível 7 do probe — ~4.5 MiB no total, com
  **>6 GB de RAM livre no host**, o que descarta pressão de memória) já
  bastou pra matar o jogo em ~4s — mas ler **1 MiB inteiro de uma região
  residente** (nível 5) sobreviveu sem problema. A variável que importa é
  **quais páginas são tocadas**, não o volume total lido nem a RAM livre do
  host.
- **Não é pressão de memória do host** (hipótese inicial forte mas
  descartada por teste controlado: o mesmo `--scan` completo, rodado com
  >6GB livres — Brave fechado — ainda matava o jogo do mesmo jeito).
- **Fix aplicado e validado**: ler a heap **por página**, via
  `/proc/<pid>/pagemap` (bit de presença física — metadado do kernel, não
  toca a memória do processo-alvo pra decidir), pulando qualquer página
  não-presente em vez de fazer um `read()` contínuo do início ao fim de
  cada região. Implementado em `safe_read_region()` no `mem_reader.py`
  (usado em todos os 12 pontos do arquivo que antes liam uma região
  inteira de uma vez). **Validado**: dois `--scan` completos seguidos
  (1080+ MiB, 342 mil vptrs cada) sobreviveram >60-100s de observação cada
  um — o mesmo comando que antes matava o jogo em segundos, toda vez.
- Não perde nenhuma entidade real: objetos vivos (prédios, muralhas,
  obstáculos, armadilhas) são sempre escritos pelo próprio jogo, logo
  **sempre** estão em páginas residentes — só a armadilha (nunca tocada
  pelo jogo) fica de fora, que é exatamente o objetivo.
- **Ainda não confirmado**: se essa arena de páginas-fantasma é
  deliberadamente uma armadilha anti-tamper (usando o userfaultfd como
  "sensor" de leitura externa) ou um efeito colateral de outra coisa (ex.:
  um alocador que reserva memória virtual generosamente sem comprometer
  fisicamente, e o `exit(1)` é uma resposta a ALGUM OUTRO sinal não
  identificado que só correlaciona por coincidência com o fault). Não foi
  necessário resolver essa ambiguidade pra ter uma correção que funciona —
  mas vale registrar que a explicação "é anti-tamper deliberado" é **uma
  hipótese plausível, não uma certeza confirmada**.
- **Efeito prático**: a arquitetura B (leitor externo) **continua viável**
  nesta build, ao contrário do que a Seção 6 original concluía — só
  precisava ler com mais cuidado (por página), não abandonar a abordagem.

---

## Conclusão de arquitetura (a considerar)
Para um gêmeo digital **somente leitura**, a rota de **menor detecção** é um **leitor externo via `process_vm_readv`** (processo separado, sem hook, sem patch de `.text`, sem ptrace), em vez do middleware **injetado** com inline hooks. Trade-off: sem hook no tick, a coleta vira **polling** externo em vez de "por frame". Vale pesar isto contra as Camadas 1/2 atuais antes de investir em Dobby/anti-detecção.

## Fontes
- OWASP MASTG — Testing Anti-Debugging — https://mas.owasp.org/MASTG/tests/android/MASVS-RESILIENCE/MASTG-TEST-0046/
- OWASP MSTG — Resiliency against RE — https://github.com/julepka/owasp-mstg/blob/master/Document/0x05j-Testing-Resiliency-Against-Reverse-Engineering.md
- GuidedHacking — bypass ptrace anti-debugger — https://guidedhacking.com/threads/bypass-ptrace-anti-debugger-in-android.17099/
- Frida detection & bypass — https://qweraqq.github.io/security/2024/04/06/android-frida-detection-and-bypass.html
- Android Anti-debugging Tricks — https://recursively.review/2021/04/25/Android-Anti-debugging-Tricks-Part-1/
- Securing Android apps (Medium) — https://medium.com/@prahaladsharma4u/securing-android-apps-against-dynamic-attacks-and-reverse-engineering-8bb608103827
