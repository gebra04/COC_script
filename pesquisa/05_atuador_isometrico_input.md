# 05 — Atuador: projeção isométrica + input via ADB/Waydroid

> **Status:** fórmulas + comandos verificáveis; os **parâmetros numéricos** (origem, escala,
> DPI) você calibra na sua tela do Waydroid.
> Última atualização: 2026-07-22.

---

## O problema
O agente decide uma ação `(tipo_tropa, tile_x, tile_y)`. Para executá-la, precisamos:
1. Converter `(tile_x, tile_y)` do grid → `(pixel_x, pixel_y)` na tela isométrica.
2. Tocar o slot da tropa e depois o ponto de deploy, via input no Waydroid.

Hoje **todo o lado Python é somente leitura** — o atuador é a lacuna registrada desde o Passo 5.

---

## 1. Projeção isométrica (grid → tela)

O CoC usa projeção **isométrica 2:1** (o mapa é um losango; tiles são rotacionados 45°) — confirmado como técnica padrão do gênero ([GameDeveloper: isometric games like CoC](https://www.gamedeveloper.com/business/quickly-learn-to-create-isometric-games-like-clash-of-clans-or-aoe), [TheAppGuruz](http://www.theappguruz.com/blog/create-isometric-games-like-clash-of-clans-crossy-roads-age-of-empire-etc)).

### Fórmula de transformação
Para grid → tela isométrica (diamond/2:1):
```
screen_x = origin_x + (tile_x - tile_y) * (TILE_W / 2)
screen_y = origin_y + (tile_x + tile_y) * (TILE_H / 2)
```
onde:
- `TILE_W` = largura de um tile em pixels na tela; `TILE_H = TILE_W / 2` (projeção 2:1).
- `origin_x`, `origin_y` = pixel na tela correspondente ao tile (0,0), i.e., o offset da câmera.

Inverso (tela → grid), útil para calibrar:
```
a = (screen_x - origin_x) / (TILE_W / 2)
b = (screen_y - origin_y) / (TILE_H / 2)
tile_x = (a + b) / 2
tile_y = (b - a) / 2
```

### Como descobrir os 3 parâmetros (`origin_x`, `origin_y`, `TILE_W`)
Calibração empírica na resolução do Waydroid:
1. Entre numa batalha; identifique visualmente 2–3 tiles de referência (cantos do mapa).
2. Use `getevent`/"Show touches" para ler o pixel de cada canto.
3. Resolva o sistema linear acima com esses pares `(tile, pixel)` → obtém `origin` e `TILE_W`.
4. Se você já tiver a leitura de memória (Camadas 1–3), pode cruzar `pos_x/pos_y` reais de um prédio com onde ele aparece na tela — calibração automática.

> **Nota subtile:** se a posição em memória vier em **subtiles** (1 tile = 512 subtiles — checar em [02](02_ponteiro_raiz_e_structs.md)), divida por 512 antes de aplicar a fórmula.

---

## 2. Mecânica de deploy (sequência de toques)
Deploy de tropa numa batalha = **2 toques**:
1. **Selecionar a tropa:** toque no slot da tropa na **barra inferior** (as coords dos slots são fixas por resolução — calibre uma vez).
2. **Deployar:** toque no ponto `(pixel_x, pixel_y)` calculado. Repetir o toque = mais tropas do mesmo tipo. Deploy "em linha" = vários toques ao longo de um segmento (nosso `attacks/deploy_policy.py::_gerar_pontos_na_reta` já gera esses pontos no espaço normalizado).

Mapeie o índice `Discrete(10)` do action space → posição do slot na barra (cruzar com `troop_slot_type()`).

---

## 3. Input no Waydroid (host → guest)

### Opção A — `adb shell input` (mais simples)
```bash
adb shell input tap 500 500            # toque único
adb shell input swipe 400 800 600 400 120   # swipe (x1 y1 x2 y2 dur_ms)
```
**Limitação:** as coords valem só para a **resolução/densidade** em que foram capturadas ([mobileqablog](https://mobileqablog.wordpress.com/2016/08/20/android-automatic-touchscreen-taps-adb-shell-input-touchscreen-tap/), [Repeato](https://www.repeato.app/simulating-touch-events-on-android-devices-via-adb/)). `input` é **lento** (spawna um processo por toque) — ruim para deploy rápido em rajada.

### Opção B — `minitouch` / escrever em `/dev/input` (baixa latência)
Para rajadas rápidas de deploy, `input tap` não escala. Alternativas: **minitouch** (socket persistente) ou escrever eventos direto em `/dev/input/eventX` via `sendevent`. Maior throughput, porém mais setup.

### Descobrir resolução/DPI do Waydroid
```bash
adb shell wm size          # ex.: Physical size: 1080x2340
adb shell wm density       # ex.: Physical density: 440
```
Use esses valores para fixar `TILE_W`/origem e para validar as coords dos slots.

### Achar coordenadas de um toque
```bash
adb shell getevent -l      # mostra ABS_MT_POSITION_X/Y ao tocar
# ou: Configurações > Opções do desenvolvedor > "Mostrar toques"
```
([Igor Moura: ADB touch events](https://igor.mp/blog/2018/02/23/using-adb-simulate-touch-events.html))

---

## 4. Esboço do atuador (a codar — `utils/adb_actuator.py`)
```python
# converte ação do PAMDP -> toques ADB no Waydroid
TILE_W = 40.0        # calibrar
ORIGIN = (540.0, 300.0)
SLOTS = {0: (120, 2100), 1: (240, 2100), ...}   # pixel de cada slot de tropa

def grid_to_screen(tx, ty):
    sx = ORIGIN[0] + (tx - ty) * (TILE_W / 2)
    sy = ORIGIN[1] + (tx + ty) * (TILE_W / 4)   # TILE_H/2 = TILE_W/4
    return int(sx), int(sy)

def deploy(troop_type, tx, ty):
    slot = SLOTS[troop_type]
    _tap(*slot)                 # 1) seleciona a tropa
    _tap(*grid_to_screen(tx, ty))  # 2) deploya no ponto
```

## Decisões
- **Atuador via ADB, desacoplado da Camada 1** — não precisa injetar input pelo hook; o Waydroid já dá `adbd`.
- Começar com `adb input tap`; migrar para **minitouch** se a latência/rajada exigir.
- Calibração isométrica preferencialmente **automática**, cruzando `pos_x/pos_y` de memória com a tela.

## Fontes
- GameDeveloper — isometric games like CoC — https://www.gamedeveloper.com/business/quickly-learn-to-create-isometric-games-like-clash-of-clans-or-aoe
- TheAppGuruz — create isometric games — http://www.theappguruz.com/blog/create-isometric-games-like-clash-of-clans-crossy-roads-age-of-empire-etc
- mobileqablog — adb input tap — https://mobileqablog.wordpress.com/2016/08/20/android-automatic-touchscreen-taps-adb-shell-input-touchscreen-tap/
- Repeato — simulating touch via ADB — https://www.repeato.app/simulating-touch-events-on-android-devices-via-adb/
- Igor Moura — ADB simulate touch — https://igor.mp/blog/2018/02/23/using-adb-simulate-touch-events.html
