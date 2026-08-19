# 10 — Feitiços pendentes no motor de simulação

> **Status:** plano de implementação, não pesquisa externa — tudo aqui é
> sobre o `utils/combat_sim.py` deste repositório. Complementa a Etapa 5 do
> `PLANO_SIMULACAO.md` ("Refinar o motor").
> Última atualização: 2026-08-19.

---

## O que já existe (`_cast_spell` em `combat_sim.py`)

Duas categorias mecânicas implementadas e testadas:

1. **Dano instantâneo** (`damage > 0`, ex. Lightning): dano direto aos
   prédios no raio, no instante do cast. `_apply_instant_damage`.
2. **Buff de tropa** (`damage_boost_percent`/`speed_boost`, ex. Rage/Haste):
   multiplica dps/velocidade das tropas no raio. `_apply_troop_buff`.

Qualquer outro feitiço **consome o orçamento do exército mas não tem efeito
na simulação** — sem crash, só sem mecânica (`applied=False` no log).

### Duas limitações conhecidas no que já existe (buff de tropa)
- **`boost_time_ms` do CSV não é a duração real do feitiço.** Confirmado
  pelo usuário (2026-08-19): a Fúria dura **18s** de verdade;
  `BoostTimeMS=1000` no `spells.csv` é a duração do efeito em cada tropa
  dentro do raio, renovado continuamente enquanto ela ficar lá (zona
  persistente com reaplicação a cada tick, não um buff de tiro único).
  Corrigido via `CombatSim.REAL_ZONE_DURATION_S` — um dicionário de
  overrides (hoje só Rage=18s confirmado; Haste=18s é **hipótese**, não
  confirmada). **Se alguém confirmar a duração real de outro feitiço,
  adicionar aqui.**
- **Membership estático**: só pega tropa que já estava no raio no instante
  do cast; uma tropa que chega depois não é afetada mesmo com a zona ainda
  ativa. Ver seção "Zona persistente" abaixo — é o problema estrutural
  comum a vários feitiços desta lista, vale resolver uma vez só.

---

## Problema estrutural comum: "zona persistente"

Rage, Freeze, Poison e Haste são, na engine real, a MESMA coisa por baixo:
uma área que persiste por alguns segundos e aplica um efeito contínuo a
qualquer unidade (tropa ou defesa) que esteja dentro dela a cada instante —
não um efeito de tiro único no cast.

O motor hoje (`_apply_troop_buff`) trata isso como "aplica uma vez pra quem
está lá, aí soma um timer" — funciona bem quando a tropa **já está** parada
lutando na zona (ex.: Fúria lançada durante o engajamento), mas erra quando:
- a tropa chega **depois** do cast (não pega o buff, mesmo a zona ainda ativa);
- a tropa **sai** do raio antes da zona expirar (mantém o buff que já não
  deveria ter — hoje isso também não é corrigido, é o oposto do problema
  acima mas mesma raiz).

### Como resolver direito (uma vez, beneficia todos os feitiços de zona)
1. Criar uma estrutura `SpellZone` (centro, raio, `expires_at`, tipo de
   efeito, parâmetros) guardada em `self.active_zones: list[SpellZone]`.
2. Num ponto central de "a posição/estado de uma tropa mudou" (o candidato
   óbvio é o topo de `_schedule()`, chamado toda vez que uma tropa é
   re-avaliada — já é o hook usado pelo epoch bump), checar: pra cada zona
   ativa (`self.t < zone.expires_at`), se `dist(tropa, zona.centro) <=
   zona.raio`, aplicar/renovar o efeito; senão, se a tropa tinha o efeito
   dessa zona e saiu, removê-lo.
3. Expirar zonas (`self.active_zones = [z for z in ... if z.expires_at >
   self.t]`) e bump de epoch quando uma zona nasce/morre (mesmo padrão já
   usado por `_kill_building`/`buff_expire`).
4. Isso também abre o caminho pra Freeze e Poison sem duplicar lógica —
   ambos são "zona que afeta quem está dentro, continuamente".

**Prioridade:** alta — não é só sobre feitiços novos, é sobre a Fúria já
implementada funcionar direito em mais situações (ex.: Fúria lançada um
pouco ANTES da tropa chegar, pra já estar ativa no engajamento — tática comum
de verdade).

---

## Feitiços por prioridade (relevância pro ataque de dragão / esforço)

### 🔴 Alta prioridade

**Freeze (Congelamento, 26000005)** — o mais valioso depois da Fúria pro
ataque de dragão (neutraliza defesas antiaéreas).
- Mecânica: zera o dps das DEFESAS dentro do raio por `freeze_time_ms`
  (esse campo, ao contrário do `boost_time_ms` da Fúria, é o do próprio
  congelamento — **não confirmado** se sofre do mesmo problema de
  "zona persistente"; checar antes de assumir que está certo).
- O que falta no código: `DefenseUnit` (dataclass em `combat_sim.py`) não
  tem campo de estado mutável pra buff/debuff — precisa de um
  `dps_mult`/`frozen_until` análogo ao que `TroopUnit` já ganhou.
  Ao congelar, zerar `dps_mult` das defesas no raio, bump de epoch (mesmo
  padrão de `_kill_building`) e reagendar TODAS as tropas ativas (a
  ameaça mudou pra todo mundo, não só pra quem está perto).
- Esforço: médio (reusa toda a infraestrutura de epoch/reschedule já
  construída pra Fúria — só falta o lado "defesa" em vez de "tropa").
- Depende da resolução de "zona persistente" acima pra funcionar direito
  se congelar antes da tropa engajar.

**Earthquake (Terremoto, 26000010)** — dano percentual em prédios/muralha,
comum em composições de dragão pra abrir muralha ou finalizar Prefeitura.
- Mecânica: dano = % do HP MÁXIMO do alvo (campos `damage_th_percent`/
  `building_damage_permil`, não um `damage` fixo como o Lightning).
- O que falta: estender `_apply_instant_damage` (ou criar uma variante)
  pra aceitar dano percentual em vez de flat — precisa do `max_hp` de cada
  prédio (já disponível via `defense_stats`/`building_stats`, mesma fonte
  usada no `__init__` do `CombatSim`).
- Esforço: baixo — reusa quase tudo de `_apply_instant_damage`.

### 🟡 Média prioridade

**Poison (Veneno, 26000009)** — dano contínuo (DOT) em tropas E prédios na
zona (campos `troop_damage_permil`/`building_damage_permil` por segundo).
- Mecânica: dano gradual, não instantâneo — precisa de re-cálculo de
  "tempo até morte" considerando uma taxa de dano ADICIONAL enquanto a
  vítima estiver na zona (ecoa o padrão de `_engage_dps`, mas aplicado a
  quem está dentro do raio, não a quem está engajando um alvo).
- Esforço: médio-alto — é a versão "zona persistente" mais complexa porque
  afeta tropa E prédio simultaneamente, e interage com o cálculo de
  tempo-até-morte que hoje assume taxa constante por segmento (precisa
  somar a taxa do veneno ao dps recebido, recalculando via o mesmo
  mecanismo de `_sync_engage_progress`/reschedule).
- Depende da resolução de "zona persistente".

**Haste (Aceleração, 26000011)** — só velocidade, sem dano. Mecanicamente
já suportado por `_apply_troop_buff` (mesmo código do speed_mult da Fúria);
falta confirmar a duração real (hoje usa a hipótese de 18s em
`REAL_ZONE_DURATION_S`, não verificada).
- Esforço: **zero código novo** — só validar a duração com alguém que saiba
  o valor real.

**Clone (Clone, 26000016)** — duplica tropas existentes no raio com HP
cheio.
- Mecânica: para cada `TroopUnit` vivo dentro do raio, criar uma cópia
  (`_spawn_troop`-like, mas a partir dos stats da tropa original, não de
  um `data_id` de exército) com `troop_id` novo, HP/dps/etc iguais aos da
  tropa original no nível dela.
- Nuance: os clones **não consomem** o orçamento do exército
  (`utils.army.ArmyComposition`) — são criados "de graça" pelo feitiço,
  então a lógica deve ficar inteira em `combat_sim`, sem chamar `army.
  try_deploy_troop`.
- Esforço: médio.

**Skeleton Spell / Bat Spell (26000017 / 26000028)** — invocam tropas
(esqueletos/morcegos) no ponto.
- Mecânica: mais simples que Clone — é só chamar `_spawn_troop` com o
  `data_id` do `SummonTroop` do feitiço (campo já extraído em
  `spell_data.json`) e `count` vezes (checar se `characters.csv` tem uma
  entrada pra esses IDs — provavelmente sim, como tropas "secundárias").
- Esforço: baixo, condicionado a confirmar que `SummonTroop` aponta pra um
  `data_id` válido em `troop_data.json`.

### 🟢 Baixa prioridade (não relevantes pro ataque de dragão típico)

- **Jump (Salto, 26000003)** — tropas ignoram muralha no raio por uma
  duração. Esforço alto: `wall_cost` hoje é global por `CombatSim`
  (`self.wall_cost`), não por tropa — precisaria de um flag/override por
  tropa no cálculo de rota (`battle_grid.route_distance`). Mais relevante
  pra composições terrestres (Gigante/Bárbaro) que pro dragão (que já voa
  e ignora muralha).
- **Invisibility (Invisibilidade, 26000035)** — remove tropas do
  `_incoming()` (defesas não miram nelas) por uma duração. Esforço médio;
  baixa prioridade porque dragão já é resistente/ignorado por certas
  defesas por natureza do alcance, o ganho relativo é menor que Freeze.
- **Healing (Cura, 26000001)** — cura contínua (campo `damage` negativo).
  Mais relevante pra composições GoWiPe/Curandeira que pra dragão puro
  (a Curandeira já dá cura passiva, o feitiço de Cura raramente entra
  em ataques de dragão). Mecânica: DOT invertido, mesma complexidade de
  Poison.
- **Recall (Retorno, 26000053)** — teleporta tropas de volta; utilidade
  quase nula pra maximizar %destruição (métrica que o `clash_env`
  otimiza). Não vale o esforço agora.
- **Overgrowth (Crescimento, 26000070)** — feitiço escuro de Builder Base/
  evento, bloqueia prédios temporariamente. Fora do escopo do ataque de
  dragão na vila principal.

---

## Ordem sugerida de implementação
1. **Resolver "zona persistente"** (infra comum) — desbloqueia Freeze,
   Poison, e corrige a Fúria pra tropas que chegam depois do cast.
2. **Freeze** — maior ganho tático pro dragão, reusa a infra nova.
3. **Earthquake** — barato, reusa `_apply_instant_damage`.
4. **Clone** / **Skeleton/Bat** — bookkeeping, sem dependência da zona persistente.
5. **Poison** — mais caro, depois que a zona persistente já estiver madura.
6. Resto (Jump/Invisibility/Healing/Recall/Overgrowth) — conforme a
   necessidade aparecer; nenhum bloqueia o treino atual com Fúria+dragão.
