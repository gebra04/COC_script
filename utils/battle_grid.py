"""Mundo estático da batalha (grid 44x44) + flow field (mapa de distância de
Dijkstra) para roteamento de tropas terrestres.

Abstração (ver plano): uma batalha é um sistema determinístico por partes —
não precisamos de física contínua nem de A* por tropa. Um único campo de
distância por ALVO é compartilhado por TODAS as tropas que vão pra lá (o mesmo
truque de pathing de RTS, tipo StarCraft 2). O campo também dá, de graça, a
distância-POR-ROTA (contornando muralha) que a seleção de alvo precisa — bem
diferente da distância euclidiana ingênua.

Muralha não bloqueia o grid: é uma célula CARA de atravessar
(`wall_movement_cost`), não impossível — modela o fato de que uma tropa sem
`is_jumper` acaba quebrando a muralha no caminho se não houver rota melhor.
Prédios (e obstáculos) SÃO bloqueio: a tropa ataca da célula adjacente, não
"dentro" do prédio.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field

import numpy as np

from utils.building_footprints import footprint, is_wall

DEFAULT_WALL_COST = 128.0  # custo p/ atravessar 1 celula de muralha (ver
                           # WallMovementCost do Quebra-Muro em troop_data.json;
                           # tropas comuns nao tem esse campo -> usar este default)
GRID_SIZE = 44  # mundo ~44x44 (tiles de predio vao 0-48) — ver memoria de RE


@dataclass
class BuildingInstance:
    eid: int
    did: int
    tx: int
    ty: int
    w: int
    h: int
    name: str
    is_wall: bool
    hp: float = 1.0
    level: int = 0  # 0-indexed, como a telemetria (pesquisa/02) -- nivel real = level+1

    @property
    def cells(self) -> list[tuple[int, int]]:
        return [(self.tx + dx, self.ty + dy) for dx in range(self.w) for dy in range(self.h)]


class BattleGrid:
    """Constrói o grid estático a partir de uma lista de entidades (mesmo
    formato do `mem_reader.py --json`: dicts com classe/did/tx/ty/hp/eid)."""

    def __init__(self, entities: list[dict], size: int = GRID_SIZE):
        self.size = size
        self.buildings: dict[int, BuildingInstance] = {}   # eid -> instancia
        # occupancy: -1 = livre; caso contrario, eid do predio que ocupa a celula
        self.occupancy = np.full((size, size), -1, dtype=np.int64)
        # custo-base por celula (1.0 grama; DEFAULT_WALL_COST muralha)
        self.cost = np.ones((size, size), dtype=np.float64)
        self._fields_cache: dict[int, np.ndarray] = {}  # eid alvo -> distance field

        for e in entities:
            cls = e.get("classe")
            did = e["did"]
            eid = e["eid"]
            tx, ty = e["tx"], e["ty"]
            if cls == "Wall" or is_wall(did):
                if 0 <= tx < size and 0 <= ty < size:
                    self.cost[ty, tx] = DEFAULT_WALL_COST
                self.buildings[eid] = BuildingInstance(eid, did, tx, ty, 1, 1, "Wall", True,
                                                        hp=e.get("hp", 0) or 1.0,
                                                        level=e.get("lvl", 0) or 0)
                continue
            if cls == "Obstacle" or cls == "Trap":
                # simplificacao v1: obstaculos/armadilhas nao bloqueiam pathing
                # (a diferenca real que importa pra tatica e muralha, nao arvore)
                continue
            w, h = footprint(did)
            inst = BuildingInstance(eid, did, tx, ty, w, h,
                                     e.get("classe", "Building"), False,
                                     hp=e.get("hp", 0) or 1.0,
                                     level=e.get("lvl", 0) or 0)
            self.buildings[eid] = inst
            for cx, cy in inst.cells:
                if 0 <= cx < size and 0 <= cy < size:
                    self.occupancy[cy, cx] = eid

    def is_building_cell(self, x: int, y: int) -> bool:
        return self.occupancy[y, x] != -1

    def shell_cells(self, eid: int) -> list[tuple[int, int]]:
        """Celulas livres adjacentes (4-viz) ao predio `eid` — as 'fontes' do
        flow field (chegar numa dessas = estar em alcance de ataque corpo a corpo
        do predio; pra alcance>1 o chamador soma o range depois)."""
        inst = self.buildings[eid]
        shell = set()
        for cx, cy in inst.cells:
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if 0 <= nx < self.size and 0 <= ny < self.size and self.occupancy[ny, nx] == -1:
                    shell.add((nx, ny))
        return list(shell)

    def distance_field(self, target_eid: int, wall_cost: float | None = None) -> np.ndarray:
        """Dijkstra multi-origem a partir da 'casca' do predio `target_eid`.
        Retorna grid size x size com a distancia-por-rota (em tiles-equivalente);
        np.inf onde nao ha rota (isolado por muralha sem custo, teoricamente
        impossivel aqui pois muralha e cara mas nao infinita) ou celula de predio.
        Cacheado por eid (o mesmo campo serve pra toda tropa mirando esse alvo)."""
        cache_key = target_eid if wall_cost is None else (target_eid, wall_cost)
        if cache_key in self._fields_cache:
            return self._fields_cache[cache_key]

        cost = self.cost if wall_cost is None else np.where(self.cost > 1, wall_cost, 1.0)
        dist = np.full((self.size, self.size), np.inf)
        pq: list[tuple[float, int, int]] = []
        for x, y in self.shell_cells(target_eid):
            dist[y, x] = 0.0
            heapq.heappush(pq, (0.0, x, y))

        while pq:
            d, x, y = heapq.heappop(pq)
            if d > dist[y, x]:
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if not (0 <= nx < self.size and 0 <= ny < self.size):
                    continue
                if self.occupancy[ny, nx] != -1:
                    continue  # celula de predio: nao se anda por cima
                nd = d + cost[ny, nx]
                if nd < dist[ny, nx]:
                    dist[ny, nx] = nd
                    heapq.heappush(pq, (nd, nx, ny))

        self._fields_cache[cache_key] = dist
        return dist

    def route_distance(self, from_tx: int, from_ty: int, target_eid: int,
                        wall_cost: float | None = None) -> float:
        """Distancia-por-rota de (from_tx,from_ty) ate o alvo `target_eid`."""
        field = self.distance_field(target_eid, wall_cost)
        x = int(np.clip(from_tx, 0, self.size - 1))
        y = int(np.clip(from_ty, 0, self.size - 1))
        return float(field[y, x])

    def nearest_building(self, from_tx: int, from_ty: int, candidate_eids: list[int],
                          wall_cost: float | None = None) -> tuple[int | None, float]:
        """Entre os candidatos, o mais proximo POR ROTA (nao euclidiano).
        Usa o campo (cacheado) de cada candidato -- barato pq varios chamadores
        (outras tropas mirando o mesmo predio) reusam o mesmo campo."""
        best_eid, best_d = None, float("inf")
        for eid in candidate_eids:
            d = self.route_distance(from_tx, from_ty, eid, wall_cost)
            if d < best_d:
                best_eid, best_d = eid, d
        return best_eid, best_d
