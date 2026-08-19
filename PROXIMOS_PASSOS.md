# Próximos Passos — Bot de RL para Clash of Clans

> Status consolidado do projeto e roadmap. Atualizado em 2026-07-22.
> Detalhes técnicos nos docs de `pesquisa/` e no `mapeamento_arquivos.md`.

---

## Onde estamos (o que já funciona)

**Arquitetura escolhida: B — Leitor Externo** (a injeção/Frida é detectada pelo
anti-tamper do CoC; ver `pesquisa/06`). Tudo é feito **de fora**, passivo.

| Bloco | Status | Onde |
|---|---|---|
| Ambiente (Waydroid + jogo + root) | ✅ | Lista B do `mapeamento_arquivos.md` |
| Engenharia reversa do modelo de entidades | ✅ | `pesquisa/02` |
| Leitor externo de memória (`/proc/pid/mem`) | ✅ | `~/.local/share/coc-digital-twin/mem_reader.py` |
| Observação → ambiente RL (adaptador) | ✅ | `utils/external_receiver.py` |
| HP em combate (`current_hp`) | ✅ | `pesquisa/02` |
| Referência de defesas (stats/nível) | ✅ | `utils/defense_stats.py`, `pesquisa/07` |
| Referência de tropas (stats/nível) | ✅ | `utils/troop_stats.py`, `pesquisa/08` |

**Resumo:** o bot já **enxerga** a vila (sua ou inimiga em scout) em tempo real
— classe, tipo, nível, posição e HP de cada entidade — e tem o **quadro tático
completo** (o que cada defesa e cada tropa fazem). Falta ele **agir** e **decidir**.

---

## O que falta (por fase)

### Fase 1 — Atuador: agir no jogo 🎯 (em andamento)
Fechar o único canal que falta: transformar decisão em toque na tela.
- [x] Calibrar a conversão **tile → pixel** (v1) — projeção 2:1 `(origin_x=620,
      origin_y=-248, tile_w=46)` a **1366×739**, zoom da vila-casa. Método:
      overlay dos 52 prédios + 175 muralhas da memória sobre o screenshot,
      ajuste pelos centros-de-chão. Gravado em `utils/cam_calib.json`; é o
      default do `CameraState`. **Validado por toque** via `adb input tap`:
      Prefeitura e broca selecionaram no tile projetado (dentro de ~1 tile).
      *Quirk:* tocar o centro de uma defesa cercada por muralha seleciona a
      **muralha** (hit-test por sprite) — não afeta deploy (tropa pisa no chão).
- [x] `utils/adb_actuator.py`: `ADBInput.tap` + `Actuator.deploy` via
      `adb shell input tap`; jitter espacial/temporal embutido.
- [ ] **Validação precisa de deploy** (depende da Fase 2): soltar tropa e ler o
      tile onde ela nasce → medir erro real da projeção em ataque.
- [~] **Câmera a partir da memória** (`--cam-hunt`/`--cam-probe`): tentativa via
      diff de heap (snapshot antes/depois de pan controlado por `adb swipe`,
      subtraindo ruído de um probe idle). **Resultado parcial**: o motor tem
      milhares de floats mutantes por conta própria (física/partículas/cache de
      render por-entidade) que sobrevivem à subtração de ruído; os candidatos
      com assinatura isométrica correta (delta_horiz ≈ ±delta_vert) aparecem em
      **clusters repetidos** (cache de posição de tela por prédio visível), não
      um singleton limpo — não isolado com confiança no tempo investido.
      **Decisão pragmática**: como só o atuador (nós) move a câmera durante
      nossa operação, não precisamos LER a câmera ao vivo — basta **não
      panorâmicar** durante o ataque e **calibrar o `origin` uma vez no início
      de cada ataque** (mesmo método overlay memória×screenshot da vila,
      usando os prédios da base inimiga como referência). Ferramentas
      `--cam-probe`/`--troop-hunt` ficam no `mem_reader.py` para retomar a
      RE depois, se valer a pena.
- [ ] **Calibração de origin por ataque**: no início de cada ataque (câmera
      ainda parada), rodar `--json` + screenshot, overlay dos prédios inimigos,
      resolver `origin_x/origin_y` (tile_w pode reusar o valor da vila se o
      zoom inicial for igual).
- [ ] Calibrar `TROOP_SLOTS` (slots da barra de tropas) — **só aparece em ataque**.
- [ ] Migrar para `minitouch` se a latência/rajada de `input tap` for insuficiente.
- [ ] **TODO (pausado 2026-07-23): calibração de câmera é por CONTEXTO DE TELA,
      não uma constante única.** Medido com 2 pontos reais (cabana no centro do
      mapa 44×44 + a mesma cabana arrastada 10 tiles) que o **War Base Edit
      Mode** tem seu próprio `origin_x/origin_y/tile_w` (≈586,-612,81),
      **bem diferente** da vila normal (620,-248,46) e do que se viu em ataque
      (~832,-218,46). O ajuste bateu quase perfeito nas 2 imagens (`debug/
      village_overlay.py`, `debug/tile_tracer.py`, `utils/cam_calib_editmode.
      json`). Falta: (a) mapear que outras telas têm calib própria (scout view,
      photo mode, etc.), (b) uma forma de **detectar em qual contexto/zoom a
      câmera está** antes de aplicar a projeção certa, em vez de assumir uma
      calib fixa. Ver `debug/` pra ferramentas de anotação manual já prontas.
- [ ] **TODO (pausado 2026-07-23): confiabilidade de posição (tx,ty) por
      instância, fora a Town Hall.** Comparando telemetria (`--json`) contra
      screenshot real pixel-a-pixel (não "no olho" — via detecção de cor), a
      Town Hall bate sempre exata, mas outras construções (testado com Cannon)
      mostraram erros de ~10-25px por instância, sem padrão de direção
      consistente (não é rotação nem erro de fórmula — parece ruído por
      instância). Não confirmado se é limitação real do heap-scan
      (`_scan_instances_fast`/`_collect_instances` do `mem_reader.py`, pegando
      objetos obsoletos/duplicados) ou artefato da minha própria medição.
      Precisa de um teste controlado (tipo o da Edit Mode acima, mas em vila/
      ataque de verdade) antes de confiar cegamente na posição de qualquer
      construção que não seja a Town Hall.

> ✅ **Rótulos data-id→prédio conferidos:** o `BUILDING_INFO` do `mem_reader.py`
> bate exatamente com `buildings.csv` (1000000=Army Camp, 1000004=Gold Mine,
> 1000012=Air Defense, 1000014=Clan Castle). O engano anterior era só num dict
> auxiliar de scratchpad; o repositório está correto. Tiles confirmados por
> toque: (26,20)=Clan Castle (com anel de muralha), (38,20)=Gold Mine.

### Fase 1.5 — Gamefiles reais extraídos (2026-08-19) ✅

Mudança de escopo do usuário: o combate passa a ser **simulado**, não lido da
tela/memória em tempo real. Logo a Fase 2 (tropas em campo ao vivo) sai do
caminho crítico — basta ler a **base inimiga** (defesas), que já funciona.

- [x] **Extração dos gamefiles do jogo rodando.** Método: `/proc/<pid>/root/`
      do processo do CoC (root via sudo), copiando `data/data/com.supercell.
      clashofclans/`. Salvos em `~/.local/share/coc-digital-twin/gamefiles/`
      (comprimidos) e `gamefiles_decoded/` (legíveis).
- [x] **Formato decifrado**: `Sig:` (4B) + assinatura (64B) + **LZMA com campo
      de tamanho truncado para 4 bytes** (o padrão usa 8). Para descomprimir:
      `props(5B) + struct.pack('<Q', usize) + resto` → `FORMAT_ALONE`.
- [x] **`spells.csv` obtido** (149.827 B) → `utils/gen_spell_data.py` +
      `utils/spell_data.json` + `utils/spell_stats.py`. **23 feitiços reais**
      do jogador (de 143 entradas; o resto são efeitos internos do motor:
      auras de herói, spells de defesa, projéteis sazonais). `STANDARD_SPELL_IDS`
      tem os 14 permanentes. data-id vem da coluna **`GlobalID`** (26000000+),
      que **não é posicional** (Freeze é a 5ª linha mas id 26000005).
      Validado: Relâmpago lv1 = 150 dano/raio 2t; Fúria = raio 5t/+130%;
      Congelamento lv1 = 2.5s/raio 3.5t; Cura = dano **negativo** (-15).
- [x] **BUG CORRIGIDO — `characters.csv` estava desatualizado.** A versão em
      `utils/` (167 KB, 92 tropas, `ProductionBuilding="Barrack"`) não é a que
      o jogo usa (452 KB, 193 entradas, `"Barracks"`). Como
      `data_id = 4000000 + índice da linha`, **84 ids apontavam para a tropa
      errada**: `4000002` era lido como Goblin quando o jogo diz **Giant**;
      `4000003` Giant → **Goblin**; `4000010` Gargoyle → **Baby Dragon**.
      Trocado pelo arquivo do jogo (backup em `characters_ANTIGO_backup.csv`),
      `troop_data.json` regenerado (102 tropas, 90 da vila principal).
      *Dragão = 4000008 nas duas versões*, então o ataque de dragão não foi
      afetado. `gen_troop_data.py` adaptado: o CSV novo não tem coluna
      `TroopLevel` — o nível é **implícito** (cada linha do grupo é o próximo).
- [ ] **`traps.csv` e `heroes.csv` continuam faltando.** Ambos existem no
      `fingerprint.json` (manifesto de 9.075 arquivos, 91 em `logic/`), mas os
      arquivos-base não estão no disco do app — só o *delta* em `update/` foi
      baixado; a base vem de CDN e fica em outro cache. Não bloqueia: a
      simulação roda sem armadilha/herói (limite conhecido, deixa a base um
      pouco mais "fácil" do que é). Retomar numa sessão com o Waydroid aberto,
      varrendo o container inteiro e não só o dir do app.

### Fase 1.6 — Implementação do Gêmeo Digital treinável (2026-08-19) ✅

Pedido do usuário: "quero começar a implementação do gêmeo digital" — base
inimiga lida (só defesas/estático), exército alterável no espírito do preset
`Ataque_Dragao_Full`, feitiços reais funcionando no motor, treino possível
sem nenhuma pista de COMO atacar (só incentivos).

- [x] `utils/army.py` (NOVO): `ArmyComposition`/`ArmySlot` — contagens
      ALTERÁVEIS de tropa/feitiço, consumidas via `try_deploy_troop/spell`
      (orçamento, não infinito). `action_slots()` gera o mapeamento
      `Discrete(N) -> (data_id, level, is_spell)` que virou o `action_space`
      do `clash_env` — nada de posição/sequência fixa entra aqui, só quais
      unidades existem. `dragon_attack_army()`: mesma organização do preset
      `Ataque_Dragao_Full` (dragões + heróis ativos + aríete + fúria), mas
      com `troop_housing_space`/`rage_count` parametrizáveis em vez de
      cliques em pixel. **Heróis são só bookkeeping** (`heroes_active` dict)
      — sem stats de combate porque `heroes.csv` não foi extraído ainda.
- [x] `utils/base_loader.py` (NOVO): `read_enemy_base()` invoca
      `mem_reader.py --json` uma vez (Arquitetura B); filtra `classe=="Troop"`
      explicitamente — só entra base ESTÁTICA (o pedido do usuário: "não leia
      tropa da tela, só defesas"). `save_base`/`load_base` pra captura
      offline; `base_report()` pra checar sanidade antes de treinar.
- [x] **Mecânica de feitiço implementada em `combat_sim.py`** (antes não
      existia — `deploy()` só sabia tropa). Cobertura DELIBERADAMENTE parcial,
      documentada no código: **dano instantâneo** (Lightning — dano direto
      aos prédios no raio) e **buff de tropa** (Rage/Haste —
      multiplica dps/velocidade das tropas no raio por `boost_time_ms`).
      Qualquer outro feitiço (Freeze, Jump, Clone, Poison, Earthquake,
      Invisibility, Heal, Recall...) consome o orçamento mas não tem efeito
      ainda — sem crash, só sem mecânica (TODO: Freeze é o próximo mais
      valioso).
- [x] **2 bugs REAIS do motor DES achados e corrigidos** ao testar o buff
      (não eram do feitiço em si — eram do reagendamento de eventos no meio
      do caminho, que `engage_kill`/morte de prédio já disparava antes, só
      não tinha sido testado nesse regime):
      1. `_schedule_travel` sempre recalculava a partir da posição de
         PARTIDA do segmento anterior — uma tropa reagendada no meio da
         viagem "voltava no tempo". Corrigido interpolando a posição atual
         (rastreada por `_travel_start_t/_travel_start_xy/_travel_total_time`
         + `_travel_target_eid` pra distinguir segmento novo de reagendado).
      2. `_schedule_engage` recalculava `kill_time` a partir do HP
         ORIGINAL do prédio-alvo, perdendo o dano parcial já causado (e o
         dano parcial já recebido pela tropa) entre o início do engajamento
         e o reagendamento. Corrigido com `_sync_engage_progress()`, chamado
         no topo de `_schedule_engage`.
      Verificado: Fúria isolada (tropa já engajada, sem viagem) foi de 3.0s
      pra 1.7s pra matar o mesmo alvo — o buff agora acelera de verdade.
- [x] **Duração da Fúria corrigida (2026-08-19), confirmada pelo usuário**:
      `BoostTimeMS=1000` do `spells.csv` NÃO é a duração total do feitiço —
      é a duração do efeito em cada tropa dentro do raio, renovada
      continuamente enquanto ela ficar lá (zona persistente com
      reaplicação). A duração real da Fúria é **18s**, confirmado pelo
      usuário. Corrigido via `CombatSim.REAL_ZONE_DURATION_S` (override por
      data-id; Haste=18s é hipótese não confirmada). Reverificado: dragão
      parado + Fúria no mesmo ponto foi de 19.25s pra **14.85s** pro alvo
      distante (antes da correção o "ganho" era só ~0.2s, imperceptível).
      **Limitação que continua aberta**: o buff só pega quem já está no raio
      NO INSTANTE do cast (`_apply_troop_buff`) — uma tropa que chega
      DEPOIS não é afetada, mesmo com a zona ainda ativa (testado: Fúria
      lançada no ponto de ataque antes do dragão chegar não teve nenhum
      efeito). Corrigir isso exige um conceito de "zona persistente" que
      cheque entrada continuamente, não só no cast — plano completo em
      `pesquisa/10_feiticos_pendentes.md`, junto com o que falta pra
      Freeze/Poison/Earthquake/Clone/Jump/etc. (nenhum implementado ainda
      além de dano instantâneo tipo-Lightning e buff tipo-Fúria/Aceleração).
- [x] `utils/clash_env.py` **reescrito**: grid 50→**44** (`battle_grid.GRID_SIZE`,
      fonte da verdade), action space derivado de `ArmyComposition.action_slots()`
      em vez do `DEFAULT_ARMY_COMPOSITION` fixo antigo, orçamento de
      tropa/feitiço aplicado em `step()` (ação sem munição = penalidade,
      não gasta tempo de simulação; exército esgotado = `truncated=True`),
      observação reconstruída via `utils.sim_replay.BattleReplay.state_at()`
      (estado real da batalha simulada até o instante da decisão, não o
      resultado final), `global_state` parcialmente populado (tempo
      decorrido, %destruição, frações de tropa/feitiço restantes — resto
      ainda zero, ver Fase 6). **Recompensa**: Δ%destruição (principal, não
      diz ONDE atacar) + bônus de cobertura de feitiço (mais prédios vivos
      sob o raio do feitiço = mais bônus — mecânica do jogo — "feitiço em
      chão vazio não faz nada" —, não tática). Removido o path antigo de
      `ipc_receiver`/`raw_entities_fn` (Arquitetura A, abandonada — ver
      `pesquisa/06`); `main.py:iniciar_gemeo_digital` reescrito pra Arquitetura
      B (`base_loader` + `dragon_attack_army` + `ActorCriticHybridNetwork`
      com `action_dim` derivado do env).
- [x] **Testado ponta a ponta** (`.venv/bin/python3`, base sintética de
      `debug/sim_viewer.py::_demo_scenario`): `reset()`→`step()` com ações
      aleatórias respeita orçamento (nega deploy sem munição, penaliza),
      episódio termina em 100% destruição; `ActorCriticHybridNetwork.
      sample_action()` roda com `action_dim` dinâmico (2 no exemplo:
      dragão+fúria) e produz ação/valor consumíveis por `env.step()`.
      Regressão do cenário legado (`sim_viewer._demo_scenario` com o plano
      fixo de 4 tropas) confirmada intacta: 100% destruição, 26.16s, 2/4
      sobreviventes — igual a antes das mudanças no motor.
- [ ] **Dados ainda faltando/não confirmados** (documentado, não bloqueia
      treino sintético, mas afeta fidelidade real):
      `troop_housing_space=300`/`rage_count=5` (defaults de
      `dragon_attack_army`) não são confirmados pra vila real do usuário —
      ajustar antes de treinar contra bases de verdade. `heroes.csv` e
      `traps.csv` continuam faltando (Fase 1.5). Mecânica de Freeze/Jump/
      Clone/etc. não implementada. `movement_speed`→tiles/s continua chute
      (Etapa 0 do `PLANO_SIMULACAO.md`, não mexido hoje).

### Fase 1.7 — Loop de treino PPO + vídeo da população (2026-08-19) ✅

Pedido do usuário: chegar ao ponto de rodar a primeira "geração" de treino
(PPO com rollout paralelo — não genético, confirmado com o usuário) e gerar
um vídeo mostrando os N ataques simulados em paralelo de uma iteração, lado
a lado, pra um vídeo explicativo. Plano revisado por um agente de design
dedicado antes de implementar (achou pontos reais: teto de passos por
episódio, ordem certa de bootstrap de valor no auto-reset, escolha de lib de
vídeo) — ver `/home/gebra/.claude/plans/agora-fa-a-o-planejamento-tingly-goose.md`.

- [x] **`utils/capture_dataset.py`** (NOVO, CLI): fica escaneando enquanto o
      usuário troca de vila manualmente no Waydroid. Salva via `base_loader.
      save_base()` e imprime confirmação clara (TH/prédios/defesas) — o
      sinal pro usuário trocar de vila, sem precisar apertar Enter a cada
      uma. **Testado offline** com sequências simuladas (detecção estável →
      salva; detecção que não bate na confirmação → rejeitada sem salvar).
- [x] **BUG REAL descoberto em uso (2026-08-19): a v1 deste script
      derrubava o jogo.** Causa provável (não Frida/anti-tamper — o
      `mem_reader.py` já é comprovadamente passivo, sem ptrace, usado antes
      com segurança via `--live` a ~200Hz): a v1 fazia polling recriando um
      processo **`sudo python3 mem_reader.py --json` NOVO a cada leitura**
      (a cada 0.7-2s) — cada invocação faz uma varredura completa do heap
      do zero, e respawnar isso em loop apertado sobrecarrega o host o
      bastante pra afetar o Waydroid, diferente de `--live`/`--watch`
      (processos de longa duração, já validados). **Corrigido**: adicionado
      `--watch-json` ao `mem_reader.py` (mesma lógica do `--watch` humano
      já existente e confiável, só que emite uma linha JSON por vila nova
      em vez do relatório de texto) — agora `capture_dataset.py` sobe **UM
      ÚNICO processo persistente**, sem respawnar nada a cada poll. Uma
      segunda leitura (uma chamada só, não um loop) confirma que a base não
      estava no meio de uma transição de tela antes de salvar.
- [x] **CAUSA RAIZ REAL confirmada (2026-08-19), via `adb logcat -d`**: a v2
      acima (processo único) **também derrubou o jogo** — a v1 tinha o
      sintoma certo (sobrecarga) mas o diagnóstico errado. Causa de verdade:
      **1)** o jogo atualizou nesse mesmo dia (`dumpsys package` →
      `lastUpdateTime=2026-08-19 11:11`, versão `18.400.22`), tornando os
      offsets de V-Table do `mem_reader.py` (levantados em 22/07) obsoletos
      — uma leitura `--json` isolada confirmou **zero entidades** encontradas
      (mas não derrubou nada sozinha). **2)** `watch_bases()` (base do
      `--watch`/`--watch-json`), quando não acha nada, tinha
      `time.sleep(2); continue` **sem backoff** — repete a varredura
      completa do heap (~1GB) a cada 2s pra sempre. Sustentado por ~25s isso
      basta pra derrubar o jogo por **pressão de memória colateral**
      (confirmado via `adb logcat -d -t <timestamp>`: cascata
      `Finsky: Memory trim` → `mem-pressure-event` → `Process ... has died`,
      não um segfault/crash isolado). **Corrigido**: backoff exponencial
      (2s→30s) em `watch_bases()`; `capture_dataset.py` agora faz uma
      leitura de sanidade antes de subir o loop e avisa claramente se vier
      vazia, em vez de ficar tentando silenciosamente. **Bloqueado até
      re-fazer a RE dos offsets pra build 18.400.22** — trabalho novo de
      engenharia reversa (repetir a metodologia de `pesquisa/01`/`02`), não
      um bug de código; ver detalhes completos na memória do projeto
      (`coc_waydroid_setup.md`).
- [x] **`utils/base_dataset.py`** (NOVO): `BaseDataset` carrega todas as
      capturas de um diretório, `.sample()` sorteia uma por episódio (plugado
      como `base_provider=` do `ClashDigitalTwinEnv` — cada episódio ataca
      uma vila diferente do banco). Se o diretório estiver vazio, cai pro
      cenário sintético de `debug/sim_viewer.py::_demo_scenario` com aviso —
      permite testar o resto do pipeline sem o Waydroid aberto.
- [x] **`utils/clash_env.py`: teto de passos por episódio** (`max_steps`,
      padrão 50). Achado pela revisão de design: uma ação inválida (slot sem
      munição) não avança `_episode_time` nem consome orçamento — sem teto,
      uma política ainda aleatória (início do treino) podia ficar emitindo
      ações inválidas pra sempre e o episódio nunca terminar dentro de um
      rollout de N passos fixos. Testado: forçando só ações inválidas,
      trunca exatamente em `max_steps` passos, sem travar.
- [x] **`utils/hppo_network.py::observation_to_tensors` generalizado pra
      batch N>1** — antes só aceitava uma observação (`unsqueeze(0)`, usado
      pra inferência passo a passo); agora aceita também uma lista de N
      observações (`np.stack`), necessário pro forward batched do rollout
      vetorizado. Mantém compatibilidade com o uso de observação única
      (`main.py::iniciar_gemeo_digital`).
- [x] **`utils/ppo_train.py`** (NOVO): PPO em PyTorch puro (sem
      stable-baselines3 — o `action_space` híbrido Dict discreto+contínuo
      não é first-class no SB3). Rollout vetorizado MANUALMENTE (loop Python
      sobre N `ClashDigitalTwinEnv`, sem `gymnasium.vector.SyncVectorEnv`,
      que tem fricção com espaços `Dict`) com auto-reset no meio do rollout
      (padrão CleanRL). `collect_rollout` (coleta pura, sem treino) →
      `compute_gae` (bootstrap de valor correto na fronteira de episódio,
      máscara `1-done` cortando os dois usos — delta TD e acumulador
      lambda) → `ppo_update` (clip 0.2, 4 épocas, Adam) → `save_checkpoint`
      (`state_dict` + `optimizer_state_dict`). Testado em sub-passos
      isolados (como o plano pedia): 5.1 só coleta (episódios completando,
      orçamento respeitado), 5.2/5.3 GAE+update sem NaN e com os pesos
      mudando de fato, laço completo de 3 iterações com `value_loss` caindo
      de 3392→1638→264 (sinal real de aprendizado, não só "não quebrou").
- [x] **BUG REAL pré-existente encontrado e corrigido** (exposto pela
      exploração aleatória extensiva do rollout PPO — meus testes manuais
      anteriores nunca bateram nesse caso): `CombatSim._retarget()` podia
      deixar uma tropa com `phase="TRAVEL"` e `target_eid=None`
      simultaneamente quando TODOS os prédios candidatos existiam mas eram
      INALCANÇÁVEIS (`nearest_building` devolve `eid=None` quando toda rota
      é `inf`) — crashava com `KeyError: None` em `_target_point`. Corrigido
      tratando esse caso igual a "sem candidatos": tropa vai pra `IDLE`
      (viva, sem alvo) em vez de tentar viajar pra lugar nenhum.
- [x] **`utils/population_viz.py`** (NOVO): vídeo mosaico da população —
      100% reuso de `sim_render.render_frame`/`sim_replay.BattleReplay`
      (nenhum renderizador novo), só cola N frames pequenos numa grade
      (`ceil(√N)×ceil(√N)`) e escreve como `.mp4` via `imageio`+
      `imageio-ffmpeg` (dependência nova, mas leve — binário ffmpeg
      embutido no pacote, sem instalar nada no sistema; escolhido em vez de
      moviepy por decisão do usuário — mais controle de layout, menos
      dependências transitivas). `BattleReplay.state_at(t)` já clampa
      `t` à duração do replay, então indivíduos que terminam mais cedo só
      congelam no estado final — não precisou de tratamento especial.
      HUD por indivíduo desligado (ilegível numa grade pequena); um HUD
      agregado único no topo (geração, reward médio, destruição média).
      **Testado**: vídeo de verdade gerado e relido com `imageio` — fps e
      dimensões do frame batem exatamente com o esperado (6 indivíduos →
      grade 3×2 → 660×480px).
- [x] **`train_ppo.py`** (NOVO, CLI de conveniência na raiz): junta tudo —
      `python3 train_ppo.py --dataset-dir ... --iterations N --n-envs N
      --video-every K`. Checkpoints e vídeos ficam juntos no mesmo
      diretório de sessão (`training_runs/<timestamp>/`, no `.gitignore`).
      **Testado ponta a ponta** (sintético, sem Waydroid): 3 iterações,
      checkpoint e vídeo salvos corretamente no mesmo diretório.
- [x] Dependências novas: `imageio`, `imageio-ffmpeg` (via `uv add`,
      `pyproject.toml` atualizado).
- [x] **Bloqueio resolvido (2026-08-19)**: o jogo atualizou pra
      **18.400.22** no mesmo dia, invalidando os offsets de V-Table
      antigos (`KNOWN_CLASSES` de julho) — leitura `--json` isolada vinha
      zerada. Pior: qualquer leitura de heap (mesmo pontual) começou a
      **derrubar o jogo** (`exit(1)` alguns segundos depois). Causa raiz
      isolada: uma arena de heap gigante (~384 MiB) fica ~98%
      NÃO-residente (páginas reservadas mas nunca escritas pelo jogo); ler
      essa região de ponta a ponta força o kernel a "faultar" centenas de
      páginas nunca tocadas, e o jogo se auto-encerra (não é OOM, não é
      detecção confirmada — ver `pesquisa/06` Seção 6 "RESOLVIDO"). Corrigido
      lendo a heap **por página** via `/proc/<pid>/pagemap` (pula páginas
      não-presentes) — `safe_read_region()` no `mem_reader.py`. Offsets
      novos re-levantados por caça estrutural (`--troop-hunt`) e
      confirmados (`--verify-chain`): Building `base+0x1690ba0` (52),
      Wall `base+0x1695030` (175), Obstacle `base+0x1692de0` (47),
      Trap `base+0x16939e0` (15) — Building/Wall/Trap batem EXATO com os
      números de julho. Pipeline `--json` validado ponta a ponta (289
      entidades, 3 leituras seguidas, jogo estável). Troop (tropa em
      campo) não re-verificado — precisa de um ataque real pra caçar de
      novo. Detalhe completo na memória do projeto
      (`coc_waydroid_setup.md`).
- [x] **Captura de bases reais concluída (2026-08-19)**: `capture_dataset.py`
      rodado de verdade, **14 vilas** salvas (TH13-15) sem o jogo cair —
      `~/.local/share/coc-digital-twin/bases/`. O treino PPO já pode usar
      `base_dataset.BaseDataset` apontando pra esse diretório em vez do
      cenário sintético de 8 prédios.
- [ ] **Próximo passo real**: ajustar `--troop-housing-space`/`--rage-count`
      do `train_ppo.py` pra capacidade real da vila (hoje são valores de
      referência não confirmados, herdados de `dragon_attack_army()`), e
      rodar o treino de fato contra as 14 bases capturadas.

### Fase 2 — Completar a observação de combate (fora do caminho crítico)
- [x] **Tropas em campo** (`LogicCharacter`): vtable = **`base+0x1681128`**,
      achada com o novo modo `mem_reader.py --troop-hunt` (varre a heap por
      objetos-entidade com data-id na faixa de tropas 4.000.000+). **Mesma
      estrutura dos prédios** (eid +0x20 na faixa 501000000+, core +0x08, pos em
      subtiles *fracionários* +0x20/+0x24, data-id pela mesma cadeia). Balão =
      data-id **4000005**. **entity_id incrementa por ordem de deploy** (bom pra
      rastrear a tropa recém-solta). Já integrada ao `KNOWN_CLASSES` (classe
      "Troop") → `--json`/`--live` leem tropas junto com prédios. Loop
      **decidir→agir→observar** demonstrado (deploy via adb → balão aparece na
      memória com posição).
- [ ] **Leitura de spawn de baixa latência**: tropa se move rápido; pra validar
      a projeção (tap→tile de spawn) e calibrar a câmera de ataque, varrer só a
      vtable "Troop" e ler o maior `eid` logo após o deploy (evita o scan lento).
- [ ] **max_hp/HP de tropa**: ler HP das próprias unidades (mesmo `+0xa8→+0xcc`?).
- [ ] **`max_hp` robusto**: hoje é o pico rastreado por entidade; opcional ler a
      tabela de HP por nível do `Logic*Data*` para ter o valor exato de cara.
- [ ] Classificar as 3 vtables de contagem baixa ainda desconhecidas (`pesquisa/02`).

### Fase 3 — Camada de análise tática (achar brechas) — ver `pesquisa/09`
Só leitura + matemática sobre dados já extraídos; sem nova RE.
- [ ] `utils/tactical_analysis.py`: **mapa de ameaça** (threat_ground/air por tile).
- [ ] Zonas mortas + **construções expostas** (saque de graça / entrada segura).
- [ ] **Clusters de defesa vulneráveis a feitiço** (ex.: Defesas Aéreas coladas → Relâmpago).
- [ ] **Lado fraco** por setor (menor DPS acumulado na aproximação).
- [ ] `utils/spell_stats.py`: extrair `spells.csv` (raio/dano/duração dos feitiços).
- [ ] Pathing/funil (fase 2 da tática): prever para onde as tropas vão.

### Fase 4 — Fechar o loop de RL (treinamento)
- [ ] Plugar os canais táticos derivados no `_get_observation` do `clash_env`.
- [ ] Ajustar `clash_env` para o grid real **44×44** (posição já vem em tiles).
- [ ] `step()` real: aplicar a ação via atuador (Fase 1), esperar, reler a
      observação, calcular a recompensa (Δdestruição, saque, baixas, tempo).
- [ ] **Política heurística de baseline** (Goblin→recurso exposto, Gigante/Hog→lado
      fraco, feitiço→melhor cluster) para bootstrap / behavior cloning / modo demo.
- [ ] **Reward shaping** + **prior de ação** espacial `softmax(−ameaça + valor_de_brecha)`.
- [ ] Laço de treino H-PPO (`utils/hppo_network.py` já tem a rede) contra o ambiente.
- [ ] Ciclo de operação: scout de bases (o `--watch`/`--scout` já varre) → escolher
      alvo → atacar → coletar recompensa → repetir.

### Fase 5 — Robustez e operação contínua
- [ ] Reconexão automática se o jogo/Waydroid reiniciar (o `auto` já reacha o PID).
- [ ] Detecção de fim de batalha / tela de resultado para segmentar episódios.
- [ ] Conta descartável e cautela com ToS/ban (`pesquisa/06`).

---

## Próximos passos imediatos (recomendação)

1. **Atuador ADB (Fase 1)** — é o que falta pro bot *agir*. Começar pela
   calibração tile→pixel: colocar uma tropa numa posição conhecida e ajustar a
   fórmula isométrica até o tap cair no tile certo.
2. Em paralelo, **tropas em campo (Fase 2)** — mesma técnica de RE já usada
   (varrer vptr durante um ataque, achar a classe `LogicCharacter` por contagem).
3. Depois, **análise tática (Fase 3)** — o grande salto de "inteligência", todo
   sobre dados que já temos.

> Dependências: Fase 4 (treino) precisa da Fase 1 (agir) e se beneficia muito da
> Fase 3 (priors). Fase 3 não depende de nada novo — pode ser feita a qualquer
> momento. Fase 2 é independente e incremental.

---

## Ferramentas já disponíveis (para consulta rápida)

`mem_reader.py` (roda com `sudo`, regra NOPASSWD): modos `--scout` (recon de
defesas), `--map` (layout ASCII), `--live` (mapa em tempo real ~5ms/frame),
`--watch` (captura toda base nova), `--json` (telemetria p/ o `external_receiver`),
`--hp-hunt` (achar campo de HP em batalha), `--village`, `--dump`, `--fields`,
`--chase`, `--comp`, `--dataid` (ferramentas de RE).
