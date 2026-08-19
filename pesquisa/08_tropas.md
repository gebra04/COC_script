# 08 — Referência de Tropas (stats por nível)

> **Status:** dados de referência, gerados dos gamefiles do CoC (`characters.csv`).
> Consulte via `utils/troop_stats.py`; dados em `utils/troop_data.json`.
> `data-id = 4000000 + índice` (confirmado por RE — ver [02](02_ponteiro_raiz_e_structs.md)).
> Unidades: **alcance/splash em tiles**, velocidade de movimento em unidades do jogo, AttackSpeed em ms.
> `VOA` = tropa aérea (só Defesa Aérea / Torre de Mago / Arqueira etc. acertam). `alvo` = classe de prédio preferida.
> Última atualização: 2026-07-22.

## Tropas principais (vila principal)

| data-id | Tropa | Espaço | Camada | Ataca | Alcance | Alvo pref. | Splash | Vel.mov | Níveis |
|---|---|---|---|---|---|---|---|---|---|
| 4000000 | **Bárbaro** | 1 | Terra | Terra | 0.4 | — | — | 200 | 10 |
| 4000001 | **Arqueira** | 1 | Terra | Ar+Terra | 3.5 | — | — | 300 | 10 |
| 4000002 | **Goblin** | 1 | Terra | Terra | 0.4 | Resource | — | 400 | 8 |
| 4000003 | **Gigante** | 5 | Terra | Terra | 1.0 | Defense | — | 150 | 10 |
| 4000004 | **Quebra-Muro** | 2 | Terra | Terra | 0.5 | Wall | 0.8 | 300 | 10 |
| 4000005 | **Balão** | 5 | VOA | Terra | 0.5 | Defense | 1.2 | 130 | 10 |
| 4000006 | **Mago** | 4 | Terra | Ar+Terra | 3.0 | — | 0.3 | 200 | 10 |
| 4000007 | **Curandeira** | 14 | VOA | Terra | 5.0 | — | 1.5 | 200 | 7 |
| 4000008 | **Dragão** | 20 | VOA | Ar+Terra | 3.0 | — | 0.3 | 200 | 9 |
| 4000009 | **P.E.K.K.A** | 25 | Terra | Terra | 0.8 | — | — | 200 | 9 |
| 4000010 | **Servo (Minion)** | 2 | VOA | Ar+Terra | 2.75 | — | — | 400 | 10 |
| 4000011 | **Gigante-Porco (Hog Rider)** | 5 | Terra | Terra | 0.6 | Defense | — | 300 | 11 |
| 4000012 | **Valquíria** | 8 | Terra | Terra | 0.5 | — | 1.0 | 300 | 9 |
| 4000013 | **Golem** | 30 | Terra | Terra | 1.0 | Defense | — | 150 | 11 |
| 4000015 | **Bruxa (Witch)** | 12 | Terra | Ar+Terra | 4.0 | — | 0.3 | 150 | 5 |
| 4000022 | **Boliche (Bowler)** | 6 | Terra | Terra | 3.0 | — | 0.3 | 175 | 6 |
| 4000023 | **Bebê Dragão** | 10 | VOA | Ar+Terra | 2.75 | — | 0.3 | 250 | 8 |
| 4000024 | **Mineiro** | 6 | Terra | Terra | 0.6 | — | — | 400 | 8 |
| 4000045 | **Aríete de Batalha** | 4 | Terra | Terra | 1.0 | Wall | — | 375 | 1 |
| 4000047 | **Fantasma Real** | 8 | Terra | Terra | 0.5 | — | — | 200 | 7 |
| 4000050 | **Esqueleto Gigante** | 20 | Terra | Terra | 1.0 | Defense | — | 150 | 8 |
| 4000051 | **Destruidor de Muralha** | 1 | Terra | Terra | 1.5 | Wall | 1.5 | 150 | 4 |
| 4000052 | **Aeronave de Batalha** | 1 | VOA | Terra | 2.0 | — | 3.0 | 225 | 4 |
| 4000053 | **Yeti** | 18 | Terra | Terra | 0.8 | — | — | 150 | 4 |
| 4000058 | **Golem de Gelo** | 15 | Terra | Terra | 1.0 | Defense | — | 150 | 6 |
| 4000059 | **Dragão Elétrico** | 30 | VOA | Ar+Terra | 3.0 | — | — | 150 | 5 |
| 4000063 | **Dragão Infernal** | 15 | VOA | Ar+Terra | 4.0 | — | — | 225 | 3 |
| 4000065 | **Cavaleiro Dragão** | 25 | VOA | Ar+Terra | 4.0 | Defense | — | 250 | 3 |
| 4000080 | **Super Boliche** | 30 | Terra | Terra | 3.0 | — | 0.6 | 175 | 3 |
| 4000082 | **Caçadora** | 6 | Terra | Ar+Terra | 3.0 | — | — | 300 | 3 |
| 4000083 | **Super Mago** | 10 | Terra | Ar+Terra | 3.5 | — | — | 250 | 2 |
| 4000084 | **Super Servo** | 12 | VOA | Ar+Terra | 4.0 | — | — | 200 | 3 |

**Leitura:**
- **Espaço** = espaço de acampamento. **Camada VOA** = tropa voadora (imune a defesas só-terra como Canhão/Morteiro).
- **Ataca** = o que a tropa consegue atingir (ar/terra). **Alvo pref.** = prioridade (Defense=defesas, Wall=muralhas, Resource=recursos); vazio = ataca o mais próximo.
- **Alcance** ~0.4–1 = corpo-a-corpo; >2 = à distância. **Splash** = dano em área.

## HP e DPS por nível (tropas principais)

### Bárbaro (data-id 4000000) — Terra, terrestre, espaço 1

| Nível | HP | DPS |
|---|---|---|
| 1 | 45 | 8 |
| 2 | 54 | 11 |
| 3 | 65 | 14 |
| 4 | 78 | 18 |
| 5 | 95 | 23 |
| 6 | 110 | 26 |
| 7 | 145 | 30 |
| 8 | 205 | 34 |
| 9 | 230 | 38 |
| 10 | 250 | 42 |

### Arqueira (data-id 4000001) — Ar+Terra, terrestre, espaço 1

| Nível | HP | DPS |
|---|---|---|
| 1 | 20 | 7 |
| 2 | 23 | 9 |
| 3 | 28 | 12 |
| 4 | 33 | 16 |
| 5 | 40 | 20 |
| 6 | 44 | 22 |
| 7 | 48 | 25 |
| 8 | 52 | 28 |
| 9 | 56 | 31 |
| 10 | 60 | 34 |

### Goblin (data-id 4000002) — Terra, terrestre, espaço 1, alvo Resource

| Nível | HP | DPS |
|---|---|---|
| 1 | 25 | 11 |
| 2 | 30 | 14 |
| 3 | 36 | 19 |
| 4 | 46 | 24 |
| 5 | 56 | 32 |
| 6 | 76 | 42 |
| 7 | 101 | 52 |
| 8 | 126 | 62 |

### Gigante (data-id 4000003) — Terra, terrestre, espaço 5, alvo Defense

| Nível | HP | DPS |
|---|---|---|
| 1 | 300 | 11 |
| 2 | 360 | 14 |
| 3 | 430 | 19 |
| 4 | 520 | 24 |
| 5 | 720 | 31 |
| 6 | 940 | 43 |
| 7 | 1280 | 50 |
| 8 | 1500 | 57 |
| 9 | 1850 | 64 |
| 10 | 2000 | 72 |

### Quebra-Muro (data-id 4000004) — Terra, terrestre, espaço 2, alvo Wall

| Nível | HP | DPS |
|---|---|---|
| 1 | 20 | 6 |
| 2 | 24 | 10 |
| 3 | 29 | 15 |
| 4 | 35 | 20 |
| 5 | 53 | 43 |
| 6 | 72 | 55 |
| 7 | 82 | 66 |
| 8 | 92 | 75 |
| 9 | 112 | 86 |
| 10 | 130 | 94 |

### Balão (data-id 4000005) — Terra, voadora, espaço 5, alvo Defense

| Nível | HP | DPS |
|---|---|---|
| 1 | 150 | 25 |
| 2 | 180 | 32 |
| 3 | 216 | 48 |
| 4 | 280 | 72 |
| 5 | 390 | 108 |
| 6 | 545 | 162 |
| 7 | 690 | 198 |
| 8 | 840 | 236 |
| 9 | 940 | 256 |
| 10 | 1040 | 276 |

### Mago (data-id 4000006) — Ar+Terra, terrestre, espaço 4

| Nível | HP | DPS |
|---|---|---|
| 1 | 75 | 50 |
| 2 | 90 | 70 |
| 3 | 108 | 90 |
| 4 | 130 | 125 |
| 5 | 156 | 170 |
| 6 | 175 | 185 |
| 7 | 190 | 200 |
| 8 | 210 | 215 |
| 9 | 230 | 230 |
| 10 | 250 | 245 |

### Curandeira (data-id 4000007) — Terra, voadora, espaço 14

| Nível | HP | DPS |
|---|---|---|
| 1 | 500 | -35 |
| 2 | 600 | -42 |
| 3 | 840 | -55 |
| 4 | 1200 | -65 |
| 5 | 1500 | -72 |
| 6 | 1600 | -72 |
| 7 | 1700 | -72 |

### Dragão (data-id 4000008) — Ar+Terra, voadora, espaço 20

| Nível | HP | DPS |
|---|---|---|
| 1 | 1900 | 140 |
| 2 | 2100 | 160 |
| 3 | 2300 | 180 |
| 4 | 2700 | 210 |
| 5 | 3100 | 240 |
| 6 | 3400 | 270 |
| 7 | 3900 | 310 |
| 8 | 4200 | 330 |
| 9 | 4500 | 350 |

### P.E.K.K.A (data-id 4000009) — Terra, terrestre, espaço 25

| Nível | HP | DPS |
|---|---|---|
| 1 | 2800 | 240 |
| 2 | 3100 | 270 |
| 3 | 3500 | 310 |
| 4 | 4000 | 360 |
| 5 | 4700 | 410 |
| 6 | 5200 | 470 |
| 7 | 5700 | 540 |
| 8 | 6300 | 610 |
| 9 | 6700 | 680 |

### Servo (Minion) (data-id 4000010) — Ar+Terra, voadora, espaço 2

| Nível | HP | DPS |
|---|---|---|
| 1 | 55 | 35 |
| 2 | 60 | 38 |
| 3 | 66 | 42 |
| 4 | 72 | 46 |
| 5 | 78 | 50 |
| 6 | 84 | 54 |
| 7 | 90 | 58 |
| 8 | 96 | 62 |
| 9 | 102 | 66 |
| 10 | 108 | 70 |

### Gigante-Porco (Hog Rider) (data-id 4000011) — Terra, terrestre, espaço 5, alvo Defense

| Nível | HP | DPS |
|---|---|---|
| 1 | 270 | 60 |
| 2 | 312 | 70 |
| 3 | 360 | 80 |
| 4 | 415 | 92 |
| 5 | 480 | 105 |
| 6 | 590 | 118 |
| 7 | 700 | 135 |
| 8 | 810 | 148 |
| 9 | 890 | 161 |
| 10 | 970 | 174 |
| 11 | 1080 | 187 |

### Valquíria (data-id 4000012) — Terra, terrestre, espaço 8

| Nível | HP | DPS |
|---|---|---|
| 1 | 750 | 94 |
| 2 | 800 | 106 |
| 3 | 850 | 119 |
| 4 | 900 | 133 |
| 5 | 1100 | 148 |
| 6 | 1200 | 163 |
| 7 | 1450 | 178 |
| 8 | 1650 | 193 |
| 9 | 1900 | 208 |

### Golem (data-id 4000013) — Terra, terrestre, espaço 30, alvo Defense

| Nível | HP | DPS |
|---|---|---|
| 1 | 5100 | 35 |
| 2 | 5400 | 40 |
| 3 | 5700 | 45 |
| 4 | 6000 | 50 |
| 5 | 6300 | 55 |
| 6 | 6600 | 60 |
| 7 | 6900 | 65 |
| 8 | 7200 | 70 |
| 9 | 7500 | 75 |
| 10 | 8000 | 80 |
| 11 | 8400 | 85 |

### Bruxa (Witch) (data-id 4000015) — Ar+Terra, terrestre, espaço 12

| Nível | HP | DPS |
|---|---|---|
| 1 | 300 | 100 |
| 2 | 320 | 110 |
| 3 | 400 | 140 |
| 4 | 440 | 160 |
| 5 | 480 | 180 |

### Boliche (Bowler) (data-id 4000022) — Terra, terrestre, espaço 6

| Nível | HP | DPS |
|---|---|---|
| 1 | 290 | 60 |
| 2 | 310 | 70 |
| 3 | 350 | 80 |
| 4 | 390 | 90 |
| 5 | 430 | 96 |
| 6 | 500 | 102 |

### Bebê Dragão (data-id 4000023) — Ar+Terra, voadora, espaço 10

| Nível | HP | DPS |
|---|---|---|
| 1 | 1200 | 75 |
| 2 | 1300 | 85 |
| 3 | 1400 | 95 |
| 4 | 1500 | 105 |
| 5 | 1600 | 115 |
| 6 | 1700 | 125 |
| 7 | 1800 | 135 |
| 8 | 1900 | 145 |

### Mineiro (data-id 4000024) — Terra, terrestre, espaço 6

| Nível | HP | DPS |
|---|---|---|
| 1 | 550 | 80 |
| 2 | 610 | 88 |
| 3 | 670 | 96 |
| 4 | 730 | 104 |
| 5 | 800 | 112 |
| 6 | 900 | 120 |
| 7 | 1000 | 128 |
| 8 | 1100 | 136 |

### Aríete de Batalha (data-id 4000045) — Terra, terrestre, espaço 4, alvo Wall

| Nível | HP | DPS |
|---|---|---|
| 1 | 300 | 6000 |

### Fantasma Real (data-id 4000047) — Terra, terrestre, espaço 8

| Nível | HP | DPS |
|---|---|---|
| 1 | 110 | 200 |
| 2 | 150 | 280 |
| 3 | 170 | 360 |
| 4 | 190 | 440 |
| 5 | 210 | 520 |
| 6 | 250 | 600 |
| 7 | 270 | 680 |

### Esqueleto Gigante (data-id 4000050) — Terra, terrestre, espaço 20, alvo Defense

| Nível | HP | DPS |
|---|---|---|
| 1 | 1000 | 22 |
| 2 | 1200 | 28 |
| 3 | 1400 | 38 |
| 4 | 1700 | 48 |
| 5 | 2200 | 62 |
| 6 | 3100 | 86 |
| 7 | 3600 | 100 |
| 8 | 4100 | 114 |

### Destruidor de Muralha (data-id 4000051) — Terra, terrestre, espaço 1, alvo Wall

| Nível | HP | DPS |
|---|---|---|
| 1 | 5300 | 250 |
| 2 | 5700 | 300 |
| 3 | 6100 | 350 |
| 4 | 6500 | 400 |

### Aeronave de Batalha (data-id 4000052) — Terra, voadora, espaço 1

| Nível | HP | DPS |
|---|---|---|
| 1 | 3000 | 100 |
| 2 | 3500 | 140 |
| 3 | 4000 | 180 |
| 4 | 4500 | 220 |

### Yeti (data-id 4000053) — Terra, terrestre, espaço 18

| Nível | HP | DPS |
|---|---|---|
| 1 | 2900 | 230 |
| 2 | 3200 | 250 |
| 3 | 3500 | 270 |
| 4 | 3700 | 290 |

### Golem de Gelo (data-id 4000058) — Terra, terrestre, espaço 15, alvo Defense

| Nível | HP | DPS |
|---|---|---|
| 1 | 2600 | 24 |
| 2 | 2800 | 28 |
| 3 | 3000 | 32 |
| 4 | 3200 | 36 |
| 5 | 3400 | 40 |
| 6 | 3600 | 44 |

### Dragão Elétrico (data-id 4000059) — Ar+Terra, voadora, espaço 30

| Nível | HP | DPS |
|---|---|---|
| 1 | 3200 | 240 |
| 2 | 3700 | 270 |
| 3 | 4200 | 300 |
| 4 | 4500 | 330 |
| 5 | 4800 | 360 |

### Dragão Infernal (data-id 4000063) — Ar+Terra, voadora, espaço 15

| Nível | HP | DPS |
|---|---|---|
| 1 | 1900 | 75 |
| 2 | 2050 | 79 |
| 3 | 2200 | 83 |

### Cavaleiro Dragão (data-id 4000065) — Ar+Terra, voadora, espaço 25, alvo Defense

| Nível | HP | DPS |
|---|---|---|
| 1 | 4100 | 340 |
| 2 | 4500 | 370 |
| 3 | 4900 | 400 |

### Super Boliche (data-id 4000080) — Terra, terrestre, espaço 30

| Nível | HP | DPS |
|---|---|---|
| 1 | 1600 | 170 |
| 2 | 1800 | 185 |
| 3 | 2000 | 200 |

### Caçadora (data-id 4000082) — Ar+Terra, terrestre, espaço 6

| Nível | HP | DPS |
|---|---|---|
| 1 | 360 | 105 |
| 2 | 400 | 115 |
| 3 | 440 | 125 |

### Super Mago (data-id 4000083) — Ar+Terra, terrestre, espaço 10

| Nível | HP | DPS |
|---|---|---|
| 1 | 450 | 220 |
| 2 | 500 | 240 |

### Super Servo (data-id 4000084) — Ar+Terra, voadora, espaço 12

| Nível | HP | DPS |
|---|---|---|
| 1 | 1500 | 300 |
| 2 | 1600 | 325 |
| 3 | 1700 | 350 |

## Outras tropas (super/evento/máquinas de cerco)

O JSON inclui mais tropas da vila principal (super troops, eventos, siege machines) sem nome PT mapeado — usam o nome interno. Também as 11 tropas da base do construtor (`village: builder`).

| data-id | Nome interno | Espaço | Camada | Ataca | Alvo pref. |
|---|---|---|---|---|---|
| 4000017 | AirDefenceSeeker | 30 | VOA | Terra | — |
| 4000026 | EliteBarbarian | 5 | Terra | Terra | — |
| 4000027 | EliteArcher | 12 | Terra | Ar+Terra | — |
| 4000028 | EliteWallBreaker | 8 | Terra | Terra | Wall |
| 4000029 | EliteGiant | 10 | Terra | Terra | Defense |
| 4000030 | Ice Wizard_xmas | 4 | Terra | Ar+Terra | Defense |
| 4000048 | Pumpkin Barbarian Armored | 1 | Terra | Terra | — |
| 4000055 | EliteGoblin | 3 | Terra | Terra | Resource |
| 4000057 | HastyBalloon | 8 | VOA | Terra | Defense |
| 4000061 | Skeleton Barrel | 5 | VOA | Terra | — |
| 4000062 | Siege Bowler Balloon | 1 | VOA | Terra | Defense |
| 4000064 | EliteValkyrie | 20 | Terra | Terra | — |
| 4000066 | Head Witch | 40 | Terra | Ar+Terra | — |
| 4000067 | ElPrimo | 10 | Terra | Terra | Defense |
| 4000072 | Party_Wizard | 4 | Terra | Ar+Terra | — |
| 4000075 | Siege Machine Carrier | 1 | Terra | Terra | — |
| 4000076 | Ice Hound | 40 | VOA | Terra | — |
| 4000087 | Siege Log Launcher | 1 | Terra | Terra | Wall |

## Como consultar (código)

```python
from utils.troop_stats import stats_at_level, is_troop, is_flying

s = stats_at_level(4000003, 5)   # Gigante nível 5
# s['hitpoints'], s['dps'], s['housing_space'], s['is_flying'],
# s['preferred_target_class'], s['targets_air'], s['range'], s['splash']
```