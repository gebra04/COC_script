# Plano — Simulação Fiel + Visualização Minimalista

> Criado em 2026-07-23. Complementa o `PROXIMOS_PASSOS.md` (roadmap geral).
> Escopo: levar `utils/combat_sim.py` de "protótipo plausível" a
> **simulação validada contra o jogo real**, com uma **visualização top-down
> minimalista** para inspecionar/depurar cada batalha simulada.

## Contexto

O motor de combate já existe e é bom: `utils/combat_sim.py` é um simulador
**event-driven** de verdade (fila de prioridade, tempo-até-morte em forma
fechada, invalidação por época quando um prédio cai), rodando sobre
`utils/battle_grid.py` (Dijkstra multi-fonte, muralha como custo 128 em vez de
bloqueio → funil emerge sozinho). `utils/attack_simulator.py` é a fachada
`(entidades, plano) → BattleResult` que o `utils/clash_env.py` já chama.

Dois problemas impedem chamar isso de "fidelidade":

1. **Os dados que alimentam o motor estão incompletos ou errados** — mais da
   metade da base simula com HP=100 fixo, todo prédio é nível 1, e o
   multiplicador de dano contra muralha está 100× errado.
2. **Não dá para ver a simulação.** Não existe nenhum renderizador do
   `CombatSim` — só overlay sobre screenshot real (`debug/village_overlay.py`).
   Sem enxergar, refinar o motor é chute.

Este plano ataca os dois, nesta ordem: **dados → poder ver → refinar → medir
contra o jogo real**. A visualização vem **cedo de propósito**: ela é a
ferramenta de depuração de tudo que vem depois, não um enfeite final.

**Independência:** nada aqui depende da Fase 1 (atuador/calibração de câmera,
travada nos TODOs de contexto-de-tela). Tudo roda offline sobre um snapshot de
base já capturado por `mem_reader.py --json`. Só a Etapa 4 (validação) precisa
do jogo, e só para *gravar*, não para agir.

---

## Etapa 0 — Consertar os dados (base de tudo)

Sem isso, refinar o motor é otimizar em cima de ruído.

- [x] **Bug do multiplicador de dano vs. alvo preferido.**
      `utils/gen_troop_data.py:65` fazia `div=100` num campo que é multiplicador
      puro. Verificado no CSV: Wall Breaker `PreferedTargetDamageMod = 40`
      (=40×) virava `0.4`; Goblin `2` virava `0.02`; Barbarian `1` virava `0.01`.
      Corrigido para `div=1`, `troop_data.json` regenerado, e `combat_sim.py`
      agora APLICA o multiplicador no dano quando o alvo bate com a classe
      preferida (antes só usava pra escolher o alvo, não pro dano em si).
      2026-07-23: feito.
- [x] **HP de todo prédio, não só defesa.** Antes `combat_sim.py:155` usava
      `hp = 100.0` fixo pra Town Hall, depósitos, acampamentos, coletores —
      ~metade da base. Criado `utils/gen_building_data.py` +
      `utils/building_data.json` + `utils/building_stats.py` (mesmo formato de
      `defense_stats.py`), cobrindo TODAS as classes de prédio inclusive
      **muralha** (HP 300→12500 por nível, confirmado batendo com a sequência
      conhecida). `combat_sim.py` usa como 2º fallback antes do `100.0`.
      2026-07-23: feito.
- [x] **Usar o nível real.** `combat_sim.py:143` fixava `lvl = 1`. Corrigido pra
      ler `inst.level` (0-indexed, +1). Achado no caminho: a telemetria real do
      `mem_reader.py` usa a chave `lvl`, não `level` — `battle_grid.py` lia a
      chave errada (sempre caía no default 0); corrigido nos dois pontos onde
      `BuildingInstance` é populado. 2026-07-23: feito.
- [x] **Modos alternativos e DPS que não está na coluna DPS:**
      Estendido `utils/gen_defense_data.py` + `defense_stats.stats_at_level`
      com `alt_air_targets`/`alt_attack_range_tiles` (X-Bow), `increasing_damage`/
      `dps_lv2`/`dps_lv3` (Inferno — dados expostos, ainda não aplicados na
      rampa dentro do `combat_sim`, isso fica pra Etapa 5), e `effective_dps`
      (= `damage_per_shot / (attack_speed_ms/1000)` quando `dps` vem 0/vazio —
      resolve Eagle Artillery e Multi Mortar, que antes davam DPS zero na
      simulação). `combat_sim.py` já usa `effective_dps` pro `DefenseUnit`.
      2026-07-23: feito (o ramp do Inferno fica pra Etapa 5, dado já disponível).
- [ ] **Calibrar `movement_speed` → tiles/s.** `combat_sim.py:238` ainda chuta
      `speed/100.0` com um comentário admitindo que é chute.
      `utils/measure_troop_speed.py` já existe e mede a velocidade real lendo o
      endereço de uma tropa em loop apertado. Rodar com um **Dragão** (voa em
      linha reta, sem pathing) e gravar a constante medida em
      `utils/game_constants.json` como `SPEED_UNITS_PER_TILE_S`.
      *Este é o único item da Etapa 0 que precisa do jogo rodando — adiado a
      pedido do usuário em 2026-07-23, junto com a Etapa 4.*

**Dados que continuam faltando (aceitar como limites conhecidos, documentar):**
armadilhas (não existe `traps.csv`; `buildings.csv` não tem classe `Trap`),
feitiços (não existe `spells.csv`), heróis (`characters.csv` tem zero heróis).
Simulação sem armadilha/feitiço/herói é honesta desde que o comparativo da
Etapa 4 use ataques **sem** esses elementos.

---

## Etapa 1 — Log de replay no motor

O motor hoje devolve só o resultado final. Para desenhar (e para comparar com o
real) é preciso reconstruir o estado em **qualquer instante t**.

A propriedade que torna isso barato: sendo event-driven com movimento em linha
reta a velocidade constante entre eventos, **a trajetória inteira é uma lista de
segmentos** — não precisa gravar frames, basta interpolar.

- [x] `CombatSim` grava um `BattleLog` durante `run()` (`get_log()`):
      `TroopKeyframe`/`BuildingKeyframe`/`DeployLogEntry` — desenho final ficou
      diferente do esboço original (keyframes com um campo `phase` que descreve
      o comportamento ATÉ o próximo ponto — TRAVEL/ENGAGE/DEAD/IDLE — em vez de
      segmentos explícitos; equivalente, mais simples de gerar inline nos
      pontos de evento já existentes em `_apply`). 2026-07-23: feito.
- [x] `utils/sim_replay.py`: `BattleReplay(log).state_at(t)` — interpola
      posição/HP entre keyframes (linear na posição durante TRAVEL, HP linear
      sempre, posição fixa durante ENGAGE). Retorna dict no formato real
      (`entities`: lista de `classe`/`did`/`eid`/`tx`/`ty`/`hp`/`lvl`/`alive`).
      Testado ponta a ponta com PEKKA vs Canhão+muralha: posição/HP/instante de
      morte batendo com o esperado. 2026-07-23: feito.

**Ponto de projeto importante:** o formato de estado do replay deve ser o mesmo
da telemetria real. Isso é o que permite a Etapa 3 (viewer único) e a Etapa 4
(comparação lado a lado) sem código duplicado.

---

## Etapa 2 — Renderizador minimalista (PIL)

Função pura `estado → imagem`. Sem interface, sem jogo, testável offline.

- [x] `utils/sim_render.py`:
      - `render_frame(state, size=616, opts: RenderOptions) -> PIL.Image` — feito.
      - `render_gif(replay, path, fps=10)` — feito.
- [x] Especificação visual (top-down 44×44 abstrato, 14px/tile): fundo escuro,
      grade a cada 4 tiles, prédios coloridos por `BuildingClass` com HP por
      opacidade (`_building_hp_ratio`, busca max_hp via `defense_stats`/
      `building_stats` pelo did+lvl), muralha como traço fino, tropas como
      círculos (cor terrestre/voador, raio ∝ `housing_space`), HUD de uma
      linha. Toggles implementados: `show_range` (círculos de alcance das
      defesas). `threat_grid`/`weak_spot_grid` existem como parâmetros de
      `RenderOptions` já com desenho pronto (`_draw_heatmap`/`_draw_weak_spots`)
      mas ainda não têm produtor — ficam pra Etapa 6 quando
      `tactical_analysis.py`/`compartment_graph` alimentarem isso.
      2026-07-23: feito (toggles de ameaça/rota adiados, sem produtor ainda).
- [x] Reaproveitado `building_footprints.py`, `defense_stats`/`building_stats`,
      `troop_stats`. Zero deps novas (Pillow já era dependência).

**Critério de pronto:** ✅ testado com base sintética multi-prédio (2 defesas
de tipos diferentes + muralha + recurso, PEKKA terrestre + Dragão voador) —
GIF e frame final conferidos visualmente: tropas seguem rota reta até o alvo,
não nascem dentro de prédio, prédios destruídos viram contorno esmaecido na
ordem certa, muralha intacta (nenhuma tropa mirava nela nesse cenário).
**Nota:** não havia base real capturada no repo nem jogo rodando nesta sessão
— o teste "real" (base de verdade) fica pendente pra quando o Waydroid estiver
de pé; o teste sintético já valida a mecânica do renderizador.

---

## Etapa 3 — Viewer interativo

- [x] `debug/sim_viewer.py` — Tkinter: slider de tempo, play/pause, controle de
      velocidade, checkbox de alcance, clique pra inspecionar tropa/prédio.
      `--demo` roda uma batalha sintética embutida; `--json`/`--plan` aceitam
      base+plano capturados de verdade quando existirem. Achados de ambiente
      registrados abaixo (nota). 2026-07-23: feito.
- [x] Aba "Gêmeo Digital" do `gui.py`: adicionado botão "🗺 Iniciar Mapa ao
      Vivo" + `tk.Canvas` (não substituiu o `CTkTextbox` de texto — os dois
      convivem, o mapa é uma seção nova). Usa `utils/telemetry_capture.py`
      (não o `ZeroCopyIPCReceiver` já conectado no botão existente) porque o
      IPC reduz a telemetria a um `type_id` genérico 1/2/3 sem `did`/`classe`
      — o renderizador precisa do formato bruto do `mem_reader.py --json`.
      2026-07-23: feito (sem testar contra o jogo real — sem sessão ativa;
      testado que a thread liga/desliga e falha graciosamente sem crashar).

**Notas de ambiente encontradas e corrigidas nesta etapa:**
- O projeto tem `.venv` próprio (Python 3.12) com Pillow compilado com suporte
  a Tk; o Python de sistema (3.14) não tem `PIL.ImageTk`. Rodar sempre com
  `.venv/bin/python3` pra qualquer coisa com GUI.
- Mesmo no `.venv`, `PIL.ImageTk.PhotoImage` falhava (`invalid command name
  "PyImagingPhoto"` — descompasso de ABI Tcl/Tk entre o `_imagingtk` compilado
  e o Tk carregado em runtime). Contornado usando `tkinter.PhotoImage(data=
  <bytes PNG>)` nativo em vez de `PIL.ImageTk` — mais robusto, zero dependência
  binária extra. Usado em `sim_viewer.py` e no mapa do `gui.py`.
- Bug real (não de ambiente) achado no meio do caminho: `ttk.Scale.set()`
  dispara o próprio `-command`, causando recursão infinita entre `_render` e
  `_on_slide`. Corrigido com uma trava de reentrância (`_syncing_slider`).
- Atualizar widgets Tk direto de uma thread de background (fora da thread
  principal) causou `core dump`. Corrigido no polling do mapa do `gui.py`
  fazendo o trabalho pesado (ler telemetria + renderizar) na thread de fundo e
  só aplicando no canvas via `self.after(0, ...)` (thread principal). O
  polling de texto existente (`_loop_polling_gemeo_digital`) tem o mesmo risco
  em teoria — não mexido aqui por estar fora do escopo desta etapa, mas vale
  registrar como possível causa de crash intermitente se aparecer.

---

## Etapa 4 — Validar fidelidade contra o jogo real (ADIADA — retomar depois de E0-E3)

> Nota 2026-07-23: decidido executar E0→E3 agora e deixar E4 parada por enquanto
> (precisa do jogo rodando e de tempo dedicado à gravação/comparação). O texto
> abaixo fica como está, para retomar quando chegar a vez.

É aqui que "fidelidade" deixa de ser opinião. Sem esta etapa não dá para
afirmar que o simulador está certo — só que ele parece razoável.

- [ ] **Gravador de ataque real.** Estender `utils/telemetry_capture.py` (hoje
      é captura pontual, um par screenshot+telemetria) para um modo *timeline*:
      amostrar `mem_reader.py --json` a ~5 Hz durante um ataque inteiro e
      gravar `snapshot inicial da base + [(t, entidades)] + log dos deploys
      (did, t, tile)` num `.jsonl`.
- [ ] **Replay comparativo.** Rodar o `CombatSim` com o *mesmo* snapshot
      inicial e o *mesmo* log de deploy → dois `BattleReplay`, um simulado, um
      real.
- [ ] **Métricas de erro** (`utils/sim_validate.py`), objetivas, não "no olho":
      - erro de destruição % ao longo do tempo (MAE e curva)
      - erro no instante de morte de cada prédio (mediana, p90)
      - erro no tempo de vida de cada tropa
      - erro de posição da tropa ao longo do tempo (mede o pathing)
- [ ] **Visualização lado a lado**: `render_frame` do sim à esquerda, do real à
      direita, mesmo cursor de tempo. Onde as duas divergem visualmente é onde
      falta modelagem.
- [ ] Coletar 5–10 ataques como conjunto de regressão fixo, para toda mudança no
      motor ser medida e não achada.

**Ressalva de método:** as posições por instância ainda não são confiáveis fora
da Town Hall (`PROXIMOS_PASSOS.md:77-88`: erros de 10–25 px sem direção
consistente, não resolvido se é o heap-scan ou a medição). O erro de posição da
tropa herda isso. Resolver aquele TODO antes de tratar erro de pathing pequeno
como sinal — ordens de grandeza (tropa foi para o lado oposto) são válidas de
imediato; diferenças sub-tile, não.

---

## Etapa 5 — Refinar o motor, guiado pelas métricas

Só agora, com número na tela, na ordem em que o erro medido justificar:

- [ ] **Dano em área** (`combat_sim.py:21`, único TODO real do motor). O dado
      `splash_radius_tiles` já existe para 23 tropas e 11 defesas. Muda muito
      Morteiro, Torre de Feiticeiro, Bombardeiro, Dragão.
- [ ] **Semântica de muralha**: com o multiplicador corrigido (Etapa 0), o Wall
      Breaker precisa mirar muralha de verdade — `cheapest_entry` e
      `best_wallbreak_target` de `compartment_graph.py` já existem para isso.
      Também `is_jumper` e `wall_movement_cost` (Hog Rider ignora muralha).
- [ ] **Curandeiro**: DPS negativo (`pesquisa/08:161`) hoje daria tempo-de-morte
      negativo em `combat_sim.py:315`. Tratar como cura ou excluir explicitamente.
- [ ] **Retarget realista**: `FORGET_TARGET_TIME` (6 s) e
      `CHAR_VS_CHAR_RADIUS_FOR_ATTACKER` (7 tiles) já estão em
      `game_constants.json`, exportados e não usados.
- [ ] **Tropas defensoras / Castelo do Clã**: o gancho `defenders` existe e é
      código morto (`combat_sim.py:127,140`); `buildings.csv` tem
      `DefenderCharacter`/`DefenderCount`.
- [ ] Trajetória curva real em vez da reta usada hoje para calcular exposição a
      defesas (`combat_sim.py:16-20`) — só se as métricas mostrarem que importa.

---

## Etapa 6 — Devolver ao RL

- [ ] Corrigir `grid_size` de 50 → **44** em `clash_env.py` e `hppo_network.py`
      (a fonte da verdade é `battle_grid.GRID_SIZE`).
- [ ] Popular `global_state`, hoje alocado e sempre zerado
      (`clash_env.py:98→120`).
- [ ] Trocar o `self._episode_time += 1.0  # placeholder` (`clash_env.py:184`)
      por espaçamento de deploy real.
- [ ] Substituir `DEFAULT_ARMY_COMPOSITION` (placeholder, `clash_env.py:42`) por
      exército real lido da telemetria/acampamentos.
- [ ] `utils/tactical_analysis.py` (mapa de ameaça de `pesquisa/09`) e plugar
      como canais de observação — o renderizador da Etapa 2 já mostra isso, o
      que torna o debug do prior espacial visual.
- [ ] Só então o laço de treino H-PPO. Com o simulador validado, dá para treinar
      **inteiramente offline** contra bases capturadas, milhares de episódios
      por minuto, sem tocar no jogo — e o atuador (Fase 1) vira só o canal de
      execução da política já treinada.

Este é o maior ganho estratégico do plano: **fidelidade de simulação
desacopla o treino do jogo**. O gargalo hoje (uma batalha real leva 3 min e
exige o atuador funcionando) desaparece.

---

## Ordem recomendada e por quê

```
E0 dados  →  E1 log  →  E2 render  →  E4 validação  →  E5 refino  →  E6 RL
                             ↘ E3 viewer (a qualquer momento depois de E2)
```

- **E0 primeiro**: refinar física sobre HP=100 e nível 1 é otimizar ruído.
- **E2 antes de E5**: não se depura um simulador que não se pode ver.
- **E4 antes de E5**: sem métrica, "melhorar o motor" é preferência pessoal.
- **E3 é opcional/paralelo**: o GIF da E2 já resolve 80% da depuração.

## Verificação (como saber que cada etapa funcionou)

| Etapa | Verificação |
|---|---|
| E0 | `troop_stats.stats_at_level(4000004,1)["preferred_target_damage_mod"] == 40`; nenhum prédio com HP 100.0 no `CombatSim`; velocidade medida do Dragão bate com a constante gravada |
| E1 | `replay.state_at(t)` no instante de um evento bate exatamente com o estado interno do sim naquele evento |
| E2 | GIF de uma batalha sobre base real capturada; conferir a olho: sem tropa dentro de prédio, funil visível na muralha, prédios somem na ordem certa |
| E3 | Slider percorre a batalha inteira sem travar; clique numa tropa mostra alvo e HP coerentes |
| E4 | MAE de destruição % e mediana do erro de tempo-de-morte reportados sobre ≥5 ataques gravados; números registrados como baseline |
| E5 | Cada mudança reduz uma métrica específica do conjunto de regressão |
| E6 | Episódio completo de treino roda offline, recompensa cresce, política supera a heurística de baseline |
