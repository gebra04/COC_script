"""Motor de combate por EVENTOS DISCRETOS (DES) — o coração do simulador.

Abstração central: entre dois eventos (uma tropa entra/sai do alcance de uma
defesa, um prédio morre, uma tropa termina de andar) TODAS as taxas de dano são
constantes. Logo o tempo-ate-morte dentro de um trecho e FORMA FECHADA
(`hp / dps_total`), sem precisar iterar tick a tick. O loop principal so avanca
de evento em evento.

Reaproveita: `utils.battle_grid.BattleGrid` (roteamento + distancia-por-rota,
ja trata muralha como custo caro em vez de bloqueio — funil de graca),
`utils.troop_stats` / `utils.defense_stats` (stats por nivel),
`utils.building_footprints` (classe do predio: Defense/Resource/Wall/...),
`utils.game_constants.json` (CHAR_VS_CHAR_RADIUS_FOR_ATTACKER etc.).

Simplificacoes deliberadas do v1 (documentadas, nao escondidas):
- Geometria de exposao a defesa durante o TRAJETO usa a reta troop->alvo como
  proxy (exata quando nao ha muralha no caminho; aproximada quando ha desvio —
  o TEMPO de viagem continua exato via `route_distance`/velocidade, so a forma
  da trajetoria pra calcular "quais defesas acertam durante o trajeto" e
  aproximada).
- Sem splash: dano vai só no alvo principal (dano em area fica de TODO).
- Sem tropas defensoras (Castelo do Clã/heróis) simuladas ainda — o gancho
  pra regra dos 7 tiles (`CHAR_VS_CHAR_RADIUS_FOR_ATTACKER`) existe
  (`defenders` opcional no construtor) mas fica vazio até termos esses dados.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

from utils.battle_grid import BattleGrid, DEFAULT_WALL_COST
from utils.building_footprints import footprint as bf_footprint, _load as _bf_load
from utils import building_stats, defense_stats, spell_stats, troop_stats
from utils.game_constants import CHAR_VS_CHAR_RADIUS_FOR_ATTACKER as CHAR_VS_CHAR_RADIUS


def _building_class(did: int) -> str:
    d = _bf_load().get(int(did))
    return d[3] if d else "Unknown"


@dataclass
class DefenseUnit:
    eid: int
    x: float
    y: float
    range_tiles: float
    min_range_tiles: float
    dps: float
    targets_ground: bool
    targets_air: bool


@dataclass
class TroopUnit:
    troop_id: int
    did: int
    x: float
    y: float
    hp: float
    dps: float
    speed_tiles_s: float
    range_tiles: float
    is_flying: bool
    preferred_target_class: str | None
    damage_mod: float = 1.0        # multiplicador de dps quando o alvo == preferred_target_class
    phase: str = "TRAVEL"          # TRAVEL | ENGAGE | DEAD
    target_eid: int | None = None
    alive: bool = True
    born_t: float = 0.0
    # buff ativo (feitiço de Fúria/Aceleração — ver CombatSim._apply_troop_buff).
    # Multiplicativo simples: 1.0 = sem buff. `buff_until` é o instante em que
    # expira (evento "buff_expire" reverte e reagenda).
    dps_mult: float = 1.0
    speed_mult: float = 1.0
    buff_until: float = 0.0


@dataclass
class SimEvent:
    t: float
    kind: str          # "arrive" | "engage_resolve"
    troop_id: int
    epoch: int          # descarta evento obsoleto (comparado a CombatSim._epoch)

    def __lt__(self, other):
        return self.t < other.t


@dataclass(frozen=True)
class DeployLogEntry:
    troop_id: int
    did: int
    t: float
    x: float
    y: float


@dataclass(frozen=True)
class TroopKeyframe:
    """Um ponto de virada na trajetoria de uma tropa. `phase` descreve o
    comportamento ENTRE este ponto e o proximo (nao o estado NELE): "TRAVEL"
    = anda em linha reta ate o proximo keyframe, "ENGAGE" = fica parada
    (so o hp muda, linear), "DEAD"/"IDLE" = terminal, mantem o ultimo valor.
    Ver `utils.sim_replay.BattleReplay` p/ como isso vira `state_at(t)`."""
    troop_id: int
    did: int
    t: float
    x: float
    y: float
    hp: float
    phase: str


@dataclass(frozen=True)
class BuildingKeyframe:
    eid: int
    t: float
    hp: float


@dataclass
class BattleLog:
    """Timeline completa de uma batalha simulada -- o suficiente pra
    reconstruir o estado em QUALQUER instante t por interpolacao (sem
    gravar frames). Ver `utils.sim_replay.BattleReplay`."""
    buildings: dict
    grid_size: int
    deploy_log: list = field(default_factory=list)
    troop_keyframes: list = field(default_factory=list)
    building_keyframes: list = field(default_factory=list)
    duration: float = 0.0


def _circle_interval(p0, p1, c, r):
    """s em [0,1] tal que P(s)=p0+s*(p1-p0) esta dentro do raio r de c.
    Retorna (s0,s1) ou None se nunca entra."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    fx, fy = p0[0] - c[0], p0[1] - c[1]
    a = dx * dx + dy * dy
    b = 2 * (fx * dx + fy * dy)
    cc = fx * fx + fy * fy - r * r
    if a == 0:
        return (0.0, 1.0) if (fx * fx + fy * fy) <= r * r else None
    disc = b * b - 4 * a * cc
    if disc < 0:
        return None
    sq = math.sqrt(disc)
    s0, s1 = sorted(((-b - sq) / (2 * a), (-b + sq) / (2 * a)))
    s0, s1 = max(0.0, s0), min(1.0, s1)
    return (s0, s1) if s0 < s1 else None


def _subtract_interval(outer, inner):
    """outer menos inner (ambos (s0,s1) ou None) -> lista de 0/1/2 intervalos."""
    if outer is None:
        return []
    if inner is None:
        return [outer]
    o0, o1 = outer
    i0, i1 = max(inner[0], o0), min(inner[1], o1)
    if i0 >= i1:
        return [outer]
    out = []
    if o0 < i0:
        out.append((o0, i0))
    if i1 < o1:
        out.append((i1, o1))
    return out


class CombatSim:
    """Simula um ataque headless: base estatica (telemetria) + plano de
    deploy -> timeline de eventos e resultado (%destruicao, mortes, tempo)."""

    def __init__(self, entities: list[dict], wall_cost: float = DEFAULT_WALL_COST,
                 defenders: list[dict] | None = None):
        self.grid = BattleGrid(entities, size=44)
        self.wall_cost = wall_cost
        self.building_hp: dict[int, float] = {}
        self.building_alive: dict[int, bool] = {}
        self.defenses: dict[int, DefenseUnit] = {}
        self.troops: dict[int, TroopUnit] = {}
        self.log: list[dict] = []
        self.t = 0.0
        self._epoch = 0            # incrementa a cada morte -> invalida eventos velhos
        self._next_troop_id = 0
        self._events: list[SimEvent] = []
        # ver docstring: gancho p/ tropas defensoras (nao usado no v1)
        self.defenders = defenders or []

        # timeline p/ replay (Etapa 1 do PLANO_SIMULACAO.md)
        self.deploy_log: list[DeployLogEntry] = []
        self.troop_keyframes: list[TroopKeyframe] = []
        self.building_keyframes: list[BuildingKeyframe] = []

        for eid, inst in self.grid.buildings.items():
            lvl = inst.level + 1  # telemetria e 0-indexed (pesquisa/02); stats_at_level e 1-indexed
            hp = None
            cls = _building_class(inst.did)
            if cls == "Defense":
                s = defense_stats.stats_at_level(inst.did, lvl)
                if s:
                    hp = s["hitpoints"]
                    cx, cy = inst.tx + inst.w / 2.0, inst.ty + inst.h / 2.0
                    self.defenses[eid] = DefenseUnit(
                        eid, cx, cy, s["range"] or 0.0, s["min_range"] or 0.0,
                        s["effective_dps"] or 0.0, s["targets_ground"], s["targets_air"])
            if hp is None:
                bs = building_stats.stats_at_level(inst.did, lvl)
                if bs:
                    hp = bs["hitpoints"]
            if hp is None:
                hp = inst.hp if inst.hp and inst.hp > 1 else 100.0  # ultimo fallback: telemetria ou constante
            self.building_hp[eid] = hp
            self.building_alive[eid] = True
            self.building_keyframes.append(BuildingKeyframe(eid, 0.0, hp))

    # ---------------------------------------------------------------- deploy
    def deploy(self, did: int, level: int, tx: float, ty: float, t: float | None = None) -> int:
        """Registra uma tropa OU um feitiço (roteado por `spell_stats.is_spell`).
        Se `t` for no futuro (> relogio atual), o deploy fica PENDENTE (evento
        "deploy" na fila) em vez de nascer na hora — necessario p/ planos de
        ataque escalonados no tempo (`attack_simulator.DeployStep`, mesmo
        espirito do `wait_after` de `attacks/deploy_policy.DeployAction`)."""
        troop_id = self._next_troop_id
        self._next_troop_id += 1
        spawn_t = t if t is not None else self.t
        self._pending_deploys = getattr(self, "_pending_deploys", {})
        self._pending_deploys[troop_id] = (did, level, tx, ty)
        if spawn_t <= self.t:
            self._resolve_deploy(troop_id)
        else:
            heapq.heappush(self._events, SimEvent(spawn_t, "deploy", troop_id, self._epoch))
        return troop_id

    def _resolve_deploy(self, troop_id: int):
        did, level, tx, ty = self._pending_deploys.pop(troop_id)
        if spell_stats.is_spell(did):
            self._cast_spell(did, level, tx, ty)
        else:
            self._spawn_troop(troop_id, did, level, tx, ty)

    def _spawn_troop(self, troop_id: int, did: int, level: int, tx: float, ty: float):
        s = troop_stats.stats_at_level(did, level)
        if not s:
            raise ValueError(f"data-id {did} nao e tropa nem feitico")
        speed = (s["movement_speed"] or 800) / 100.0   # ver measure_troop_speed.py p/ validar
        troop = TroopUnit(
            troop_id=troop_id, did=did, x=float(tx), y=float(ty),
            hp=float(s["hitpoints"]), dps=float(s["dps"]), speed_tiles_s=speed,
            range_tiles=float(s["range"] or 0.4), is_flying=bool(s["is_flying"]),
            preferred_target_class=s["preferred_target_class"],
            damage_mod=float(s.get("preferred_target_damage_mod") or 1.0),
            born_t=self.t,
        )
        self.troops[troop_id] = troop
        self.deploy_log.append(DeployLogEntry(troop_id, did, self.t, troop.x, troop.y))
        self._retarget(troop)
        self._schedule(troop)
        self.troop_keyframes.append(
            TroopKeyframe(troop_id, did, self.t, troop.x, troop.y, troop.hp, troop.phase))

    # ---------------------------------------------------------------- feitiços
    # Cobertura DELIBERADAMENTE parcial (documentada, não escondida — ver
    # PLANO_SIMULACAO.md "dados que continuam faltando" e
    # `pesquisa/10_feiticos_pendentes.md` pro plano dos que faltam): só as
    # duas categorias mecânicas que os campos do spells.csv permitem modelar
    # sem reescrever o motor DES inteiro.
    #   - DANO INSTANTÂNEO (`damage` > 0, ex. Lightning): dano direto aos
    #     prédios no raio, no instante do cast.
    #   - BUFF DE TROPA (`damage_boost_percent`/`speed_boost`, ex. Rage/Haste):
    #     multiplica dps/velocidade das tropas no raio pela DURAÇÃO REAL da
    #     zona (`REAL_ZONE_DURATION_S`, não `boost_time_ms`), com expiração
    #     via evento (não decai gradualmente).
    # Qualquer outro feitiço (Freeze, Jump, Clone, Invisibility, Poison,
    # Earthquake, Skeleton, Bat, Heal, Recall...) consome o orçamento do
    # exército mas não tem efeito na simulação ainda — sem crash, só sem
    # mecânica. Ver `pesquisa/10_feiticos_pendentes.md` pro que falta em
    # cada um e por onde começar (Freeze é o próximo mais valioso pro
    # ataque de dragão).
    #
    # `boost_time_ms` do spells.csv NÃO é a duração total do feitiço —
    # confirmado pelo usuário (2026-08-19): Fúria dura 18s de verdade;
    # `BoostTimeMS=1000` é a duração do EFEITO em cada tropa dentro do raio,
    # renovado continuamente enquanto ela ficar lá (zona persistente com
    # reaplicação, não um buff de tiro único). O motor simplifica isso pra
    # "buff dura a zona inteira, sem checar se a tropa saiu do raio no meio"
    # — ver `REAL_ZONE_DURATION_S` abaixo pros valores confirmados/hipóteses.
    REAL_ZONE_DURATION_S = {
        26000002: 18.0,   # Rage/Furia -- CONFIRMADO pelo usuario (2026-08-19)
        26000011: 18.0,   # Haste/Aceleracao -- HIPOTESE (mesma familia de zona
                           # persistente que a Furia; nao confirmado, ajustar
                           # se alguem confirmar o valor real).
    }

    def _cast_spell(self, did: int, level: int, x: float, y: float):
        s = spell_stats.stats_at_level(did, level)
        if not s:
            raise ValueError(f"data-id {did} nao e feitico conhecido")
        radius = s.get("radius_tiles") or 0.0
        dmg = s.get("damage")
        # `s` ja e level-specific (spell_stats.stats_at_level(did, level)) --
        # tanto o dano quanto a velocidade da Furia escalam por nivel (ex.:
        # nv1 dano+130%/vel+20 -> nv7 dano+190%/vel+32, confirmado 2026-08-19),
        # entao os dois abaixo ja saem no valor certo pro nivel pedido.
        boost_pct = s.get("damage_boost_percent")
        speed_boost = s.get("speed_boost")
        boost_ms = s.get("boost_time_ms")
        duration_s = self.REAL_ZONE_DURATION_S.get(did, (boost_ms or 0) / 1000.0)

        applied = False
        if dmg and dmg > 0 and radius > 0:
            self._apply_instant_damage(x, y, radius, float(dmg))
            applied = True
        if (boost_pct or speed_boost) and duration_s > 0 and radius > 0:
            self._apply_troop_buff(x, y, radius, boost_pct or 0.0, speed_boost or 0.0, duration_s)
            applied = True

        self.log.append({"t": self.t, "event": "spell_cast", "did": did, "x": x, "y": y,
                          "radius": radius, "applied": applied})

    def _apply_instant_damage(self, x: float, y: float, radius: float, dmg: float):
        for eid in list(self.building_alive.keys()):
            if not self.building_alive[eid]:
                continue
            inst = self.grid.buildings[eid]
            cx, cy = inst.tx + inst.w / 2.0, inst.ty + inst.h / 2.0
            if math.hypot(cx - x, cy - y) > radius:
                continue
            new_hp = max(0.0, self.building_hp[eid] - dmg)
            self.building_hp[eid] = new_hp
            self.building_keyframes.append(BuildingKeyframe(eid, self.t, new_hp))
            if new_hp <= 0:
                self._kill_building(eid)

    def _kill_building(self, eid: int):
        """Mata um prédio (dano instantâneo de feitiço OU golpe final de
        tropa — ver `_apply`, evento `engage_kill`) e propaga as
        consequências: invalida a fila de eventos (o conjunto de alvos/
        defesas mudou) e reagenda toda tropa ativa."""
        self.building_hp[eid] = 0.0
        self.building_alive[eid] = False
        if eid in self.defenses:
            del self.defenses[eid]
        self._epoch += 1
        for troop in self.troops.values():
            if troop.alive:
                self._schedule(troop)

    def _apply_troop_buff(self, x: float, y: float, radius: float,
                           boost_pct: float, speed_boost_pct: float, duration_s: float):
        """LIMITAÇÃO CONHECIDA (não corrigida): só afeta tropas que já
        estiverem no raio NO INSTANTE do cast (`static membership`). Uma
        tropa que entra na zona DEPOIS de lançada (ex.: chega andando 5s
        depois) não é pega, mesmo com a zona ainda ativa por `duration_s`
        (ver `REAL_ZONE_DURATION_S`). Modelar isso direito exigiria manter a
        zona como objeto vivo e checar entrada a cada reposicionamento de
        tropa (`_schedule`/`arrive`) — ver `pesquisa/10_feiticos_pendentes.md`.
        Na prática: para o buff valer, lance o feitiço DEPOIS que a tropa já
        estiver no raio (ex.: quando ela chega no alvo), não antes."""
        affected = []
        for troop in self.troops.values():
            if not troop.alive:
                continue
            if math.hypot(troop.x - x, troop.y - y) <= radius:
                troop.dps_mult = 1.0 + boost_pct / 100.0
                troop.speed_mult = 1.0 + speed_boost_pct / 100.0
                troop.buff_until = self.t + duration_s
                affected.append(troop)
                heapq.heappush(self._events, SimEvent(self.t + duration_s, "buff_expire",
                                                        troop.troop_id, self._epoch + 1))
        if not affected:
            return
        self._epoch += 1  # timing em ENGAGE/TRAVEL das tropas afetadas mudou
        for troop in self.troops.values():
            if troop.alive:
                self._schedule(troop)

    # -------------------------------------------------------------- targeting
    def _alive_buildings(self, cls: str | None = None) -> list[int]:
        out = []
        for eid, alive in self.building_alive.items():
            if not alive:
                continue
            inst = self.grid.buildings[eid]
            if cls is not None and _building_class(inst.did) != cls:
                continue
            if cls is None and _building_class(inst.did) == "Wall":
                continue  # "sem preferencia" nao mira muralha como objetivo
            out.append(eid)
        return out

    def _retarget(self, troop: TroopUnit):
        cands = self._alive_buildings(troop.preferred_target_class)
        if not cands:
            cands = self._alive_buildings(None)
        if not cands:
            # sem alvos restantes: a tropa continua VIVA (hp real preservado),
            # so nao ha mais o que atacar -- distinto de "morreu em combate".
            troop.target_eid = None
            troop.phase = "IDLE"
            return
        eid, _dist = self.grid.nearest_building(int(troop.x), int(troop.y), cands, self.wall_cost)
        if eid is None:
            # todos os candidatos existem mas sao INALCANCAVEIS (route_distance
            # = inf pra todos -- isolados pelo custo do grid). Sem isso a tropa
            # ficava com phase="TRAVEL" e target_eid=None simultaneamente, um
            # estado que _target_point()/_schedule_travel() nao sabem tratar
            # (KeyError None em self.grid.buildings). Mesmo tratamento de "sem
            # alvo": IDLE, tropa continua viva.
            troop.target_eid = None
            troop.phase = "IDLE"
            return
        troop.target_eid = eid
        troop.phase = "TRAVEL"

    # ------------------------------------------------------------- geometria
    def _target_point(self, troop: TroopUnit) -> tuple[float, float, float]:
        """Ponto de parada da tropa (proxy reta, so p/ geometria de exposicao)
        + distancia RESTANTE de viagem (essa sim usada pro tempo).

        `route_distance` do grid ja mede ate a "casca" adjacente ao predio —
        ou seja, ja e a distancia de chegar em alcance CORPO A CORPO (melee).
        Pra tropa a distancia (`range_tiles`>melee), subtrai so o range, sem
        somar de novo um raio geometrico (evita contar a aproximacao 2x)."""
        inst = self.grid.buildings[troop.target_eid]
        cx, cy = inst.tx + inst.w / 2.0, inst.ty + inst.h / 2.0
        hit_radius = 0.5 * math.hypot(inst.w, inst.h)
        stop_dist = hit_radius + max(troop.range_tiles, 0.1)
        dx, dy = cx - troop.x, cy - troop.y
        straight = math.hypot(dx, dy)
        route_dist = self.grid.route_distance(int(troop.x), int(troop.y), troop.target_eid, self.wall_cost)
        travel_dist = max(route_dist - max(troop.range_tiles, 0.1), 0.0)
        if straight <= stop_dist:
            return troop.x, troop.y, travel_dist
        frac = (straight - stop_dist) / straight
        return troop.x + dx * frac, troop.y + dy * frac, travel_dist

    def _incoming(self, x: float, y: float, is_flying: bool) -> tuple[float, list[int]]:
        total, who = 0.0, []
        for eid, d in self.defenses.items():
            if not self.building_alive.get(eid, False):
                continue
            if is_flying and not d.targets_air:
                continue
            if not is_flying and not d.targets_ground:
                continue
            dist = math.hypot(x - d.x, y - d.y)
            if d.min_range_tiles and dist < d.min_range_tiles:
                continue
            if dist <= d.range_tiles:
                total += d.dps
                who.append(eid)
        return total, who

    # --------------------------------------------------------------- eventos
    def _schedule(self, troop: TroopUnit):
        if not troop.alive:
            return
        if troop.target_eid is None or not self.building_alive.get(troop.target_eid, False):
            self._retarget(troop)
            if troop.phase == "IDLE":
                return
        if troop.phase == "TRAVEL":
            self._schedule_travel(troop)
        else:
            self._schedule_engage(troop)

    def _schedule_travel(self, troop: TroopUnit):
        # Reagendamento no MEIO do trajeto (buff aplicado/expirado, ou outro
        # predio morrendo -- `engage_kill`/`_kill_building` reagendam TODA
        # tropa ativa) precisa interpolar a posicao atual antes de recalcular;
        # sem isso, o proximo calculo reparte da posicao de PARTIDA do
        # segmento anterior, fazendo a tropa "voltar no tempo" -- e foi
        # exatamente esse bug que o buff de velocidade da Furia expos (o
        # reagendamento no expire descartava o progresso feito durante o
        # buff). Rastreado por instante+alvo do segmento em curso; se o alvo
        # mudou desde o ultimo agendamento, e um trajeto NOVO (sem interpolar).
        same_segment = (getattr(troop, "_travel_start_t", None) is not None
                         and getattr(troop, "_travel_target_eid", None) == troop.target_eid)
        # Limitacao aceita (nao corrigida agora): dano recebido de defesas
        # DURANTE a porcao ja percorrida do segmento anterior nao e debitado
        # de troop.hp aqui (só é debitado quando um segmento termina
        # naturalmente via `arrive`/`die_travel`) -- um reagendamento no meio
        # do caminho essencialmente "pula" esse trecho sem dano. Preexistente
        # a este buff (mesma simplificacao de `engage_kill` reagendando
        # tropas em TRAVEL); moldura de correcao futura, nao bloqueante pro
        # uso atual (buffs/mortes no meio do voo sao o caso raro, nao o comum).
        if same_segment:
            start_t = troop._travel_start_t              # type: ignore[attr-defined]
            start_xy = troop._travel_start_xy             # type: ignore[attr-defined]
            end_xy = getattr(troop, "_arrive_xy", None)
            total_time = getattr(troop, "_travel_total_time", None)
            if end_xy is not None and total_time and total_time > 0:
                frac = min(1.0, max(0.0, (self.t - start_t) / total_time))
                troop.x = start_xy[0] + (end_xy[0] - start_xy[0]) * frac
                troop.y = start_xy[1] + (end_xy[1] - start_xy[1]) * frac

        ex, ey, dist = self._target_point(troop)
        if dist <= 1e-6:
            troop.phase = "ENGAGE"
            self._schedule_engage(troop)
            return
        travel_time = dist / (troop.speed_tiles_s * troop.speed_mult)
        # janelas de exposicao a cada defesa ao longo da reta proxy
        windows = []  # (s0,s1,dps)
        for eid, d in self.defenses.items():
            if not self.building_alive.get(eid, False):
                continue
            if troop.is_flying and not d.targets_air:
                continue
            if not troop.is_flying and not d.targets_ground:
                continue
            outer = _circle_interval((troop.x, troop.y), (ex, ey), (d.x, d.y), d.range_tiles)
            inner = _circle_interval((troop.x, troop.y), (ex, ey), (d.x, d.y), d.min_range_tiles) if d.min_range_tiles else None
            for s0, s1 in _subtract_interval(outer, inner):
                windows.append((s0, s1, d.dps))
        # varre em ordem de tempo, HP cai por trecho de taxa constante (forma fechada)
        breakpoints = sorted({0.0, 1.0} | {s for s0, s1, _ in windows for s in (s0, s1)})
        remaining_hp = troop.hp
        for a, b in zip(breakpoints, breakpoints[1:]):
            mid = (a + b) / 2
            rate = sum(dps for s0, s1, dps in windows if s0 <= mid < s1)
            seg_time = (b - a) * travel_time
            if rate <= 0:
                continue
            dmg = rate * seg_time
            if dmg >= remaining_hp:
                dt_local = remaining_hp / rate
                death_t = self.t + a * travel_time + dt_local
                s_frac = a + dt_local / travel_time
                troop._death_xy = (troop.x + (ex - troop.x) * s_frac,  # type: ignore[attr-defined]
                                    troop.y + (ey - troop.y) * s_frac)
                heapq.heappush(self._events, SimEvent(death_t, "die_travel", troop.troop_id, self._epoch))
                return
            remaining_hp -= dmg
        troop.hp = remaining_hp
        heapq.heappush(self._events, SimEvent(self.t + travel_time, "arrive", troop.troop_id, self._epoch))
        troop._arrive_xy = (ex, ey)  # type: ignore[attr-defined]
        troop._travel_start_t = self.t          # type: ignore[attr-defined]
        troop._travel_start_xy = (troop.x, troop.y)  # type: ignore[attr-defined]
        troop._travel_target_eid = troop.target_eid  # type: ignore[attr-defined]
        troop._travel_total_time = travel_time  # type: ignore[attr-defined]

    def _engage_dps(self, troop: TroopUnit) -> float:
        """DPS efetivo contra o alvo atual: aplica `damage_mod` só quando o
        alvo e da classe preferida (ex.: Wall Breaker vs muralha = 40x), e
        `dps_mult` sempre (buff de Furia -- ver `_apply_troop_buff`)."""
        target_cls = _building_class(self.grid.buildings[troop.target_eid].did)
        base = troop.dps
        if troop.preferred_target_class and target_cls == troop.preferred_target_class:
            base = troop.dps * troop.damage_mod
        return base * troop.dps_mult

    def _sync_engage_progress(self, troop: TroopUnit):
        """Se a tropa já estava ENGAGE contra o MESMO alvo (evento anterior
        ainda não disparou -- reagendamento por buff/morte de outro prédio
        via `_apply_troop_buff`/`_kill_building`/`engage_kill`), credita o
        dano parcial já causado/recebido até AGORA em `self.building_hp` e
        `troop.hp` antes de recalcular do zero. Sem isso, todo reagendamento
        no meio de um engajamento perderia o progresso feito (mesmo problema
        que `_schedule_travel` tinha antes da interpolação de posição)."""
        start_t = getattr(troop, "_engage_start_t", None)
        target_eid = getattr(troop, "_engage_target_eid", None)
        if start_t is None or target_eid != troop.target_eid or target_eid not in self.building_hp:
            return
        dt = self.t - start_t
        if dt <= 0:
            return
        eff_dps = getattr(troop, "_engage_dps", 0.0)
        incoming = getattr(troop, "_engage_incoming", 0.0)
        start_target_hp = getattr(troop, "_engage_target_start_hp", self.building_hp[target_eid])
        start_troop_hp = getattr(troop, "_engage_start_hp", troop.hp)
        self.building_hp[target_eid] = max(0.0, start_target_hp - eff_dps * dt)
        troop.hp = max(0.0, start_troop_hp - incoming * dt)

    def _schedule_engage(self, troop: TroopUnit):
        self._sync_engage_progress(troop)
        target_hp = self.building_hp[troop.target_eid]
        eff_dps = self._engage_dps(troop)
        kill_time = target_hp / eff_dps if eff_dps > 0 else float("inf")
        incoming, _who = self._incoming(troop.x, troop.y, troop.is_flying)
        death_time = troop.hp / incoming if incoming > 0 else float("inf")
        t_next = self.t + min(kill_time, death_time)
        kind = "engage_kill" if kill_time <= death_time else "engage_die"
        heapq.heappush(self._events, SimEvent(t_next, kind, troop.troop_id, self._epoch))
        troop._engage_incoming = incoming  # type: ignore[attr-defined]
        troop._engage_start_hp = troop.hp  # type: ignore[attr-defined]
        troop._engage_start_t = self.t     # type: ignore[attr-defined]
        troop._engage_target_start_hp = target_hp  # type: ignore[attr-defined]
        troop._engage_target_eid = troop.target_eid  # type: ignore[attr-defined]
        troop._engage_dps = eff_dps        # type: ignore[attr-defined]

    # ------------------------------------------------------------------ run
    def run(self, max_time: float = 180.0):
        """Roda ate a fila esvaziar ou `max_time` (s, ver ATTACK_LENGTH_SEC)."""
        while self._events:
            ev = heapq.heappop(self._events)
            if ev.t > max_time:
                continue
            if ev.kind == "deploy":
                # deploy nao e invalidado por mudanca de epoch (morte de predio
                # em outro lugar nao cancela uma tropa/feitico agendado p/ nascer)
                self.t = ev.t
                self._resolve_deploy(ev.troop_id)
                continue
            if ev.epoch != self._epoch:
                continue
            troop = self.troops.get(ev.troop_id)
            if troop is None or not troop.alive:
                continue
            self.t = ev.t
            self._apply(troop, ev)
        self.t = min(self.t, max_time)

    def _apply(self, troop: TroopUnit, ev: SimEvent):
        if ev.kind == "arrive":
            troop.x, troop.y = troop._arrive_xy  # type: ignore[attr-defined]
            troop.phase = "ENGAGE"
            self.log.append({"t": self.t, "event": "arrive", "troop": troop.troop_id, "target": troop.target_eid})
            self._schedule(troop)
            self.troop_keyframes.append(
                TroopKeyframe(troop.troop_id, troop.did, self.t, troop.x, troop.y, troop.hp, troop.phase))
        elif ev.kind == "die_travel":
            dx, dy = getattr(troop, "_death_xy", (troop.x, troop.y))
            troop.hp = 0.0
            troop.alive = False
            self.log.append({"t": self.t, "event": "troop_died_travel", "troop": troop.troop_id})
            self.troop_keyframes.append(
                TroopKeyframe(troop.troop_id, troop.did, self.t, dx, dy, 0.0, "DEAD"))
        elif ev.kind == "engage_die":
            dt = self.t - troop._engage_start_t  # type: ignore[attr-defined]
            new_hp = max(0.0, troop._engage_target_start_hp - troop._engage_dps * dt)  # type: ignore[attr-defined]
            self.building_hp[troop.target_eid] = new_hp
            self.building_keyframes.append(BuildingKeyframe(troop.target_eid, self.t, new_hp))
            troop.hp = 0.0
            troop.alive = False
            self.log.append({"t": self.t, "event": "troop_died_engage", "troop": troop.troop_id, "target": troop.target_eid})
            self.troop_keyframes.append(
                TroopKeyframe(troop.troop_id, troop.did, self.t, troop.x, troop.y, 0.0, "DEAD"))
        elif ev.kind == "buff_expire":
            troop.dps_mult = 1.0
            troop.speed_mult = 1.0
            troop.buff_until = 0.0
            self.log.append({"t": self.t, "event": "buff_expire", "troop": troop.troop_id})
            self._epoch += 1  # timing de ENGAGE/TRAVEL desta tropa mudou (voltou ao normal)
            for other in self.troops.values():
                if other.alive:
                    self._schedule(other)
        elif ev.kind == "engage_kill":
            eid = troop.target_eid
            self.building_hp[eid] = 0.0
            self.building_alive[eid] = False
            self.building_keyframes.append(BuildingKeyframe(eid, self.t, 0.0))
            if eid in self.defenses:
                del self.defenses[eid]
            self._epoch += 1  # invalida eventos futuros de QUALQUER tropa (conjunto de defesas mudou)
            self.log.append({"t": self.t, "event": "building_destroyed", "troop": troop.troop_id, "target": eid})
            dt = self.t - troop._engage_start_t  # type: ignore[attr-defined]
            troop.hp = max(0.0, troop._engage_start_hp - troop._engage_incoming * dt)  # type: ignore[attr-defined]
            self._retarget(troop)
            if troop.phase != "IDLE":
                self._schedule(troop)
            self.troop_keyframes.append(
                TroopKeyframe(troop.troop_id, troop.did, self.t, troop.x, troop.y, troop.hp, troop.phase))
            # reagenda TODAS as tropas ativas (o conjunto de defesas/prédios mudou)
            for other in self.troops.values():
                if other.alive and other.troop_id != troop.troop_id:
                    self._schedule(other)

    # --------------------------------------------------------------- resultado
    def destruction_pct(self) -> float:
        total = sum(1 for eid in self.building_hp if _building_class(self.grid.buildings[eid].did) != "Wall")
        dead = sum(1 for eid, alive in self.building_alive.items()
                   if not alive and _building_class(self.grid.buildings[eid].did) != "Wall")
        return 100.0 * dead / total if total else 0.0

    def get_log(self) -> BattleLog:
        """Timeline completa da batalha p/ `utils.sim_replay.BattleReplay`.
        Chamar depois de `run()` (ou a qualquer momento -- reflete o que ja
        rodou ate agora)."""
        return BattleLog(
            buildings=dict(self.grid.buildings),
            grid_size=self.grid.size,
            deploy_log=list(self.deploy_log),
            troop_keyframes=list(self.troop_keyframes),
            building_keyframes=list(self.building_keyframes),
            duration=self.t,
        )
