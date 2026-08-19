# 07 — Referência de Defesas (stats por nível)

> **Status:** dados de referência, gerados dos gamefiles do CoC (`buildings.csv`). Fonte de verdade para o atuador e o agente de RL.
> Consulte via `utils/defense_stats.py`; dados em `utils/defense_data.json`.
> `data-id = 1000000 + índice do prédio` (confirmado por RE — ver [02](02_ponteiro_raiz_e_structs.md)).
> Unidades: **alcance/splash em tiles**, **velocidade em ms**, HP/DPS por nível.
> Última atualização: 2026-07-22.

## Resumo das defesas da vila principal

| data-id | Defesa | Alvos | Alcance | Alc. mín | Splash | Vel.(ms) | Tam. | Níveis |
|---|---|---|---|---|---|---|---|---|
| 1000008 | **Canhão** | Terra | 9.0 | — | — | 800 | 3x3 | 20 |
| 1000009 | **Torre Arqueira** | Ar + Terra | 10.0 | — | — | 500 | 3x3 | 20 |
| 1000011 | **Torre de Mago** | Ar + Terra | 7.0 | — | 1.0 | 1300 | 3x3 | 14 |
| 1000012 | **Defesa Aérea** | Ar | 10.0 | — | — | 1000 | 3x3 | 12 |
| 1000013 | **Morteiro** | Terra | 11.0 | 4.0 | 1.5 | 5000 | 3x3 | 14 |
| 1000019 | **Tesla Oculta** | Ar + Terra | 7.0 | — | — | 600 | 2x2 | 13 |
| 1000021 | **Besta (X-Bow)** | Terra | 14.0 | — | — | 128 | 3x3 | 9 |
| 1000027 | **Torre Infernal** | Ar + Terra | 9.0 | — | — | 128 | 2x2 | 8 |
| 1000028 | **Varredor Aéreo (Air Sweeper)** | Ar | 15.0 | 1.0 | — | 5000 | 2x2 | 7 |
| 1000031 | **Artilharia Águia (Eagle)** | Ar + Terra | 50.0 | 7.0 | 3.0 | 10000 | 4x4 | 5 |
| 1000032 | **Torre Bomba** | Terra | 6.0 | — | 1.5 | 1100 | 3x3 | 9 |
| 1000067 | **Scattershot** | Ar + Terra | 10.0 | 3.0 | 1.0 | 3228 | 3x3 | 3 |

**Notas de leitura:**
- **Alcance mín** só existe em Morteiro/Águia (ponto cego perto da defesa).
- **Splash** = raio de dano em área (tiles); vazio = alvo único.
- **Vel.(ms)** = intervalo entre ataques; DPS já é o dano por segundo.
- Nomes internos do CSV entre parênteses no loader (`Bow`=X-Bow, `Dark Tower`=Torre Infernal, `Ancient Artillery`=Águia, `Air Blaster`=Air Sweeper).

## HP e DPS por nível

### Canhão (data-id 1000008) — Terra, alcance 9.0t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 1 | 420 | 9 |
| 2 | 2 | 470 | 11 |
| 3 | 2 | 520 | 15 |
| 4 | 3 | 570 | 19 |
| 5 | 4 | 620 | 25 |
| 6 | 5 | 670 | 31 |
| 7 | 6 | 730 | 40 |
| 8 | 7 | 800 | 48 |
| 9 | 8 | 880 | 56 |
| 10 | 8 | 960 | 64 |
| 11 | 9 | 1060 | 74 |
| 12 | 10 | 1160 | 87 |
| 13 | 10 | 1260 | 100 |
| 14 | 11 | 1380 | 110 |
| 15 | 11 | 1500 | 118 |
| 16 | 12 | 1620 | 124 |
| 17 | 12 | 1740 | 130 |
| 18 | 13 | 1870 | 139 |
| 19 | 13 | 2000 | 146 |
| 20 | 14 | 2150 | 154 |

### Torre Arqueira (data-id 1000009) — Ar + Terra, alcance 10.0t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 2 | 380 | 11 |
| 2 | 2 | 420 | 15 |
| 3 | 3 | 460 | 19 |
| 4 | 4 | 500 | 25 |
| 5 | 5 | 540 | 30 |
| 6 | 5 | 580 | 35 |
| 7 | 6 | 630 | 42 |
| 8 | 7 | 690 | 48 |
| 9 | 8 | 750 | 56 |
| 10 | 8 | 810 | 63 |
| 11 | 9 | 890 | 70 |
| 12 | 10 | 970 | 75 |
| 13 | 10 | 1050 | 80 |
| 14 | 11 | 1130 | 92 |
| 15 | 11 | 1230 | 104 |
| 16 | 12 | 1330 | 116 |
| 17 | 12 | 1410 | 122 |
| 18 | 13 | 1510 | 128 |
| 19 | 13 | 1600 | 134 |
| 20 | 14 | 1700 | 140 |

### Torre de Mago (data-id 1000011) — Ar + Terra, alcance 7.0t, splash 1.0t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 5 | 620 | 11 |
| 2 | 5 | 650 | 13 |
| 3 | 6 | 680 | 16 |
| 4 | 7 | 730 | 20 |
| 5 | 8 | 840 | 24 |
| 6 | 8 | 960 | 32 |
| 7 | 9 | 1200 | 40 |
| 8 | 10 | 1440 | 45 |
| 9 | 10 | 1680 | 50 |
| 10 | 11 | 2000 | 62 |
| 11 | 12 | 2240 | 70 |
| 12 | 13 | 2480 | 78 |
| 13 | 13 | 2700 | 84 |
| 14 | 14 | 2900 | 90 |

### Defesa Aérea (data-id 1000012) — Ar, alcance 10.0t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 4 | 800 | 80 |
| 2 | 4 | 850 | 110 |
| 3 | 5 | 900 | 140 |
| 4 | 6 | 950 | 160 |
| 5 | 7 | 1000 | 190 |
| 6 | 8 | 1050 | 230 |
| 7 | 9 | 1100 | 280 |
| 8 | 10 | 1210 | 320 |
| 9 | 11 | 1300 | 360 |
| 10 | 12 | 1400 | 400 |
| 11 | 13 | 1500 | 440 |
| 12 | 14 | 1600 | 480 |

### Morteiro (data-id 1000013) — Terra, alcance 11.0t, splash 1.5t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 3 | 400 | 4 |
| 2 | 4 | 450 | 5 |
| 3 | 5 | 500 | 6 |
| 4 | 6 | 550 | 7 |
| 5 | 7 | 600 | 9 |
| 6 | 8 | 650 | 11 |
| 7 | 9 | 700 | 15 |
| 8 | 10 | 750 | 20 |
| 9 | 11 | 800 | 25 |
| 10 | 11 | 850 | 30 |
| 11 | 12 | 900 | 35 |
| 12 | 12 | 980 | 38 |
| 13 | 13 | 1100 | 42 |
| 14 | 14 | 1250 | 48 |

### Tesla Oculta (data-id 1000019) — Ar + Terra, alcance 7.0t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 7 | 600 | 34 |
| 2 | 7 | 630 | 40 |
| 3 | 7 | 660 | 48 |
| 4 | 8 | 690 | 55 |
| 5 | 8 | 730 | 64 |
| 6 | 8 | 770 | 75 |
| 7 | 9 | 810 | 87 |
| 8 | 10 | 850 | 99 |
| 9 | 11 | 900 | 110 |
| 10 | 12 | 980 | 120 |
| 11 | 13 | 1100 | 130 |
| 12 | 13 | 1200 | 140 |
| 13 | 14 | 1350 | 150 |

### Besta (X-Bow) (data-id 1000021) — Terra, alcance 14.0t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 9 | 1500 | 60 |
| 2 | 9 | 1900 | 70 |
| 3 | 9 | 2300 | 80 |
| 4 | 10 | 2700 | 95 |
| 5 | 11 | 3100 | 125 |
| 6 | 12 | 3500 | 155 |
| 7 | 13 | 3900 | 175 |
| 8 | 13 | 4200 | 185 |
| 9 | 14 | 4500 | 200 |

### Torre Infernal (data-id 1000027) — Ar + Terra, alcance 9.0t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 10 | 1500 | 30 |
| 2 | 10 | 1800 | 36 |
| 3 | 10 | 2100 | 42 |
| 4 | 11 | 2400 | 58 |
| 5 | 11 | 2700 | 70 |
| 6 | 12 | 3000 | 82 |
| 7 | 13 | 3300 | 94 |
| 8 | 14 | 3700 | 106 |

### Varredor Aéreo (Air Sweeper) (data-id 1000028) — Ar, alcance 15.0t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 6 | 750 | — |
| 2 | 6 | 800 | — |
| 3 | 7 | 850 | — |
| 4 | 8 | 900 | — |
| 5 | 9 | 950 | — |
| 6 | 10 | 1000 | — |
| 7 | 11 | 1050 | — |

### Artilharia Águia (Eagle) (data-id 1000031) — Ar + Terra, alcance 50.0t, splash 3.0t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 11 | 4000 | — |
| 2 | 11 | 4400 | — |
| 3 | 12 | 4800 | — |
| 4 | 13 | 5200 | — |
| 5 | 14 | 5600 | — |

### Torre Bomba (data-id 1000032) — Terra, alcance 6.0t, splash 1.5t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 8 | 650 | 24 |
| 2 | 8 | 700 | 28 |
| 3 | 9 | 750 | 32 |
| 4 | 10 | 850 | 40 |
| 5 | 11 | 1050 | 48 |
| 6 | 11 | 1300 | 56 |
| 7 | 12 | 1600 | 64 |
| 8 | 13 | 1900 | 72 |
| 9 | 14 | 2300 | 84 |

### Scattershot (data-id 1000067) — Ar + Terra, alcance 10.0t, splash 1.0t

| Nível | TH mín | HP | DPS |
|---|---|---|---|
| 1 | 13 | 3600 | 140 |
| 2 | 13 | 4200 | 170 |
| 3 | 14 | 4800 | 190 |

## Base do Construtor

O JSON também inclui as defesas da base do construtor (`village: builder`, 13 defesas). Filtre com `all_defense_ids('builder')`.

## Como consultar (código)

```python
from utils.defense_stats import stats_at_level, is_defense, name_pt

# a telemetria (ExternalMemoryReceiver) dá data_id e level de cada entidade
if is_defense(did):
    s = stats_at_level(did, level)
    # s['dps'], s['hitpoints'], s['range'], s['splash'],
    # s['targets_air'], s['targets_ground'], s['min_range'], ...
```