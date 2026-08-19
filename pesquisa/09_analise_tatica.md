# 09 — Análise Tática: achar brechas na vila (planejamento de treino)

> **Status:** planejamento de design + algoritmos. Camada **derivada** entre a
> observação crua (posições+stats via `ExternalMemoryReceiver`) e a decisão do
> agente (Camada 4 / H-PPO). Alimenta o RL com *priors táticos* e serve de base
> para política heurística e reward shaping.
> Depende de: `utils/defense_stats.py`, `utils/troop_stats.py` (prontos) e, para
> feitiços, de um futuro `spell_stats` (extrair `spells.csv`, ver §8).
> Última atualização: 2026-07-22.

---

## 1. Por que uma camada tática (e não só jogar o grid cru no RL)

O agente H-PPO poderia, em tese, aprender tudo do tensor cru. Mas achar padrões
como "duas Defesas Aéreas no mesmo raio de um Relâmpago" a partir de pixels exige
uma quantidade enorme de episódios. Como já temos os **stats exatos** (alcance,
DPS, alvos, footprint) e as **posições exatas**, é muito mais eficiente
**pré-computar** as brechas e entregá-las ao agente como:

1. **Canais extras de observação** (mapas 2D que a CNN já consome).
2. **Política heurística de baseline / curriculum** (bootstrap: o agente começa
   imitando heurísticas boas, depois melhora).
3. **Reward shaping** (bônus por explorar a brecha certa).
4. **Máscara/prior de ação** (enviesar o deploy para os pontos bons).

Tudo abaixo é computável **por frame**, em ms, a partir dos dados que já lemos.

---

## 2. Mapa de ameaça (threat map) — a base de tudo

Para cada tile `(x,y)` do grid 44×44, quanto DPS uma tropa **ali parada** sofre.
Separado por camada, porque tropa terrestre e aérea sofrem de defesas diferentes:

```
threat_ground[x,y] = Σ  dps(d)   para cada defesa d viva tal que
                     d atinge terra E dist(d, (x,y)) ∈ [min_range(d), range(d)]
threat_air[x,y]    = idem, para defesas que atingem ar
```

- `dps(d)`, `range`, `min_range`, `targets_air/ground` vêm de `defense_stats.stats_at_level(did, lvl)`.
- `dist` = distância euclidiana em tiles (a projeção do jogo é isométrica, mas o
  grid lógico é euclidiano — ver `pesquisa/05`).
- Defesas **destruídas** (hp=0) saem do somatório → o mapa evolui durante o ataque.
- Resultado: dois mapas escalares 44×44. **Já é o "Canal 1 (Alcance de Ataque)"**
  previsto no `digital_twin.md`, agora com DPS real em vez de máscara binária.

**Uso imediato:** o inverso do threat map é o mapa de segurança. Tudo o mais
(brechas, lado fraco, exposição) deriva dele.

---

## 3. Zonas mortas e construções expostas

**Zona morta** = tile com `threat_layer[x,y] == 0` (nenhuma defesa alcança).
Toda vila tem uma "casca" externa de zonas mortas (fora do alcance das defesas).

**Construção exposta** = prédio cujo footprint pode ser atacado por uma tropa
posicionada numa zona morta (ou de baixa ameaça):

```
para cada prédio b:
    para cada tile t adjacente ao footprint de b (a ≤ range_da_tropa):
        se threat_layer[t] baixo  →  b é atacável "de graça" a partir de t
```

- Coletores/armazéns na borda caem nessa categoria → **saque barato** (bom p/
  Goblin, cujo `preferred_target_class == "Resource"`).
- Serve tanto para "sniping" de recurso quanto para achar por onde iniciar o
  ataque sem tomar dano.

---

## 4. Clusters de defesas vulneráveis a feitiço (o exemplo das Defesas Aéreas)

Objetivo: achar um ponto onde **um único feitiço de área** (Relâmpago,
Terremoto, Congelamento) atinge **várias defesas** — clássico "par de Defesas
Aéreas coladas" que um Relâmpago derruba junto, abrindo caminho aéreo.

```
entrada: lista de defesas-alvo (ex.: só Defesas Aéreas, ou todas), raio R do feitiço
para cada defesa d:                        # candidato a centro = a própria defesa
    grupo = { d' : dist(centro_de_d, centro_de_d') ≤ R }
    pontua grupo por: nº de defesas, DPS total coberto, prioridade (AD > Tesla > Canhão)
retorna os melhores centros (onde soltar o feitiço) e o que cada um desativa
```

- Refinamento: em vez do centro ser "sobre uma defesa", varrer um grid fino de
  centros candidatos e achar o disco de raio R que cobre o **maior DPS** — é um
  problema de *max-coverage por disco* (guloso já resolve bem).
- Para **Defesas Aéreas** especificamente: `defense_stats` marca `targets_air`.
  Duas ADs dentro de ~2 tiles → um Relâmpago (raio ~2) mata as duas → corredor
  aéreo. Esse é exatamente o insight que o usuário pediu.
- **Dependência:** o raio R e o dano por nível do feitiço vêm do `spells.csv`
  (§8). Enquanto isso, parametrizar R (default 2.0 tiles ≈ Relâmpago).

---

## 5. Lado fraco / setores de aproximação

Dividir a vila em setores (8 fatias angulares a partir do centroide, ou 4
quadrantes) e medir a "dureza" defensiva de cada aproximação:

```
centro = centroide dos prédios (ou a Town Hall)
para cada setor s:
    dureza[s] = Σ threat_ground ao longo de um "corredor" do lado s até o centro
                (ou Σ dps das defesas cujo arco de cobertura protege o lado s)
lado_fraco = argmin(dureza)
```

- Saída: por qual borda começar o ataque (menos DPS acumulado no caminho).
- Combina com §3: o lado fraco + construções expostas = ponto de entrada ideal.

---

## 6. Pathing / funil (para onde as tropas vão)

Tropas sem alvo preferido andam até o **prédio mais próximo** (ou, se `preferred_target_class`,
até o prédio daquela classe mais próximo). Isso é previsível e explorável:

- Simular, a partir de um tile de deploy, o alvo que cada tropa buscaria
  (vizinho mais próximo respeitando `preferred_target_class` e camada VOA/terra).
- Detectar **funis**: aberturas nas muralhas por onde as tropas seriam canalizadas
  para dentro (ou desviadas para fora, o temido "trilho" que faz a tropa dar a
  volta na base). Muralhas (classe `Wall`) já são lidas com posição.
- Uso avançado (fase 2): planejar o ponto de deploy que evita o funil ruim.

---

## 7. Como integra ao treino (o pedido: "adicionar ao planejamento")

### 7.1. Canais extras de observação (feature engineering)
Estender o tensor da Camada 4 (`digital_twin.md` §2.1) com canais derivados,
normalizados em [0,1]:

| Canal (novo) | Conteúdo | Fonte |
|---|---|---|
| threat_ground | DPS terrestre por tile (§2) | defense_stats |
| threat_air | DPS aéreo por tile (§2) | defense_stats |
| coverage_gap | 1 onde nenhuma defesa alcança (§3) | §2 |
| exposed_targets | prédios atacáveis de zona morta (§3) | §3 |
| spell_value | valor de cobertura de feitiço por tile (§4) | §4 |

Isso dá ao CNN/GNN o "mapa de calor" pronto — acelera muito a convergência.

### 7.2. Política heurística de baseline (curriculum / bootstrap)
Antes de treinar do zero, uma **política scriptada** que já joga razoável:
- Goblin → construção de recurso exposta mais barata (§3).
- Gigante/Hog → entrar pelo lado fraco (§5) mirando defesas.
- Feitiço → melhor cluster (§4), priorizando Defesas Aéveas se o ataque for aéreo.
Serve para (a) **behavior cloning** inicial, (b) baseline de comparação, (c)
gerar dados de episódio para acelerar o RL (curriculum: começa fácil).

### 7.3. Reward shaping
Somar termos à recompensa (`digital_twin.md` §4) que premiem *usar* as brechas:
- `+` por destruir defesa dentro de um cluster identificado com poucos recursos.
- `+` por saque de recurso exposto por tropa barata.
- `+` por progredir pelo lado fraco (dano recebido baixo por % destruído).
Cuidado com over-shaping (enviesar demais); usar pesos pequenos, decaindo ao
longo do treino para o agente eventualmente confiar no aprendido.

### 7.4. Máscara / prior de ação (PAMDP)
No espaço de ação `(tropa, x, y)`, enviesar `(x,y)` para tiles bons:
- prior espacial = softmax(−threat + valor_de_brecha) como distribuição inicial
  de deploy, que a rede refina. Reduz o espaço de busca contínuo drasticamente.

---

## 8. Dependências de dados ainda a extrair
- **`spells.csv` → `utils/spell_stats.py`** (data-id 26000000+): raio, dano por
  nível, duração (Congelamento), para §4 quantificar o que cada feitiço desativa.
  Extrair no mesmo padrão de `defense_stats`/`troop_stats`.
- **Footprint/atributos de muralha** para §6 (já temos posição; falta se há
  "porta"/abertura — derivável da grade de muralhas).

---

## 9. Ordem de implementação sugerida
1. `utils/tactical_analysis.py`: threat map (§2) + zonas mortas/expostos (§3) +
   clusters de feitiço (§4) + lado fraco (§5). Tudo função pura sobre a lista de
   entidades + os `*_stats`. **Maior valor, sem depender de mais RE.**
2. Plugar os canais derivados no `_get_observation` do `clash_env`.
3. `spell_stats` (§8) para dar raio/dano reais aos clusters.
4. Política heurística de baseline (§7.2) — vira também o "modo demo" jogável.
5. Reward shaping (§7.3) e prior de ação (§7.4) no laço de treino H-PPO.
6. Pathing/funil (§6) — fase 2, mais complexa.

> Toda a §1–§6 é **somente leitura + matemática** sobre dados que já extraímos;
> não precisa de nova engenharia reversa nem de tocar no jogo. É o próximo grande
> incremento de "inteligência" do projeto depois do atuador.
