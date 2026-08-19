"""Camada tática: particiona a base em COMPARTIMENTOS (salas) separadas por
muralha, e monta um grafo (nó=sala, aresta=segmento de muralha com HP).

Isso responde direto as perguntas de "onde ataca":
- lado fraco: compartimento externo (onde da pra soltar tropa) com menor
  cobertura de DPS de defesa.
- funil: aresta (segmento de muralha) mais barata de romper pra entrar numa
  sala vizinha — é por ali que uma tropa sem `is_jumper` de fato entra.
- alvo de quebra-muro: mesma ideia, mas pontuando pelo valor do que a aresta
  abre (nº de prédios/DPS na sala do outro lado), no espirito do
  `WALL_BREAKER_SMART_*` (ver `game_constants.json`).

Reaproveita `utils.battle_grid.BattleGrid` (occupancy + custo de muralha) em
vez de duplicar a leitura de footprint/muralha.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from utils.battle_grid import BattleGrid, DEFAULT_WALL_COST
from utils.building_footprints import _load as _bf_load
from utils import defense_stats


def _building_class(did: int) -> str:
    d = _bf_load().get(int(did))
    return d[3] if d else "Unknown"


@dataclass
class WallEdge:
    a: int                       # id do compartimento de um lado
    b: int                       # id do compartimento do outro lado
    cells: list[tuple[int, int]] = field(default_factory=list)   # celulas de muralha da aresta
    hp: float = 0.0               # HP total da aresta (soma dos segmentos)

    def key(self) -> tuple[int, int]:
        return (self.a, self.b) if self.a <= self.b else (self.b, self.a)


class CompartmentGraph:
    def __init__(self, entities: list[dict], grid: BattleGrid | None = None):
        self.grid = grid or BattleGrid(entities, size=44)
        self.entities = entities
        size = self.grid.size
        self.comp_id = [[-1] * size for _ in range(size)]   # celula -> id do compartimento
        self.compartments: dict[int, list[tuple[int, int]]] = {}   # id -> celulas
        self._flood_fill()
        self.edges: dict[tuple[int, int], WallEdge] = {}
        self._build_edges()
        # dps por defesa viva, p/ sector_dps (mesma fonte de dados do combat_sim)
        self._defenses = self._collect_defenses()

    # ------------------------------------------------------------- flood fill
    def _is_open(self, x: int, y: int) -> bool:
        return self.grid.occupancy[y, x] == -1 and self.grid.cost[y, x] == 1.0

    def _flood_fill(self):
        size = self.grid.size
        seen = [[False] * size for _ in range(size)]
        next_id = 0
        for sy in range(size):
            for sx in range(size):
                if seen[sy][sx] or not self._is_open(sx, sy):
                    continue
                stack = [(sx, sy)]
                seen[sy][sx] = True
                cells = []
                while stack:
                    x, y = stack.pop()
                    cells.append((x, y))
                    self.comp_id[y][x] = next_id
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= nx < size and 0 <= ny < size and not seen[ny][nx] and self._is_open(nx, ny):
                            seen[ny][nx] = True
                            stack.append((nx, ny))
                self.compartments[next_id] = cells
                next_id += 1

    # ------------------------------------------------------------ arestas
    def _build_edges(self):
        size = self.grid.size
        for y in range(size):
            for x in range(size):
                if self.grid.cost[y, x] == 1.0:
                    continue  # nao e celula de muralha
                neighbor_comps = set()
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < size and 0 <= ny < size:
                        cid = self.comp_id[ny][nx]
                        if cid != -1:
                            neighbor_comps.add(cid)
                if len(neighbor_comps) < 2:
                    continue  # muralha "morta" (so um lado aberto) -- nao conecta salas
                wall_hp = self._wall_hp_at(x, y)
                comps = sorted(neighbor_comps)
                for i in range(len(comps)):
                    for j in range(i + 1, len(comps)):
                        key = (comps[i], comps[j])
                        e = self.edges.setdefault(key, WallEdge(comps[i], comps[j]))
                        e.cells.append((x, y))
                        e.hp += wall_hp

    def _wall_hp_at(self, x: int, y: int) -> float:
        for e in self.entities:
            if e.get("classe") == "Wall" and e["tx"] == x and e["ty"] == y:
                return float(e.get("hp") or 1.0) or 1.0
        return 1.0

    # --------------------------------------------------------------- defesas
    def _collect_defenses(self) -> list[dict]:
        out = []
        for eid, inst in self.grid.buildings.items():
            if _building_class(inst.did) != "Defense":
                continue
            s = defense_stats.stats_at_level(inst.did, 1)
            if not s:
                continue
            out.append({
                "eid": eid, "x": inst.tx + inst.w / 2.0, "y": inst.ty + inst.h / 2.0,
                "range": s["range"] or 0.0, "dps": s["dps"] or 0.0,
            })
        return out

    # ------------------------------------------------------------ exteriores
    def exterior_compartments(self) -> list[int]:
        """Compartimentos que tocam a borda do grid -- candidatos a zona de
        deploy / 'lado de fora' por onde a tropa entra."""
        size = self.grid.size
        ext = set()
        for cid, cells in self.compartments.items():
            if any(x == 0 or y == 0 or x == size - 1 or y == size - 1 for x, y in cells):
                ext.add(cid)
        return sorted(ext)

    # ------------------------------------------------------------ analise
    def sector_dps(self, compartment_id: int) -> float:
        """DPS total de defesas vivas cujo alcance cobre alguma celula desse
        compartimento -- a "dureza defensiva" real de quem entra por ali
        (melhor que so somar defesas QUE MORAM na sala: alcance atravessa
        paredes)."""
        cells = self.compartments.get(compartment_id, [])
        if not cells:
            return 0.0
        total = 0.0
        for d in self._defenses:
            r2 = d["range"] ** 2
            if any((x - d["x"]) ** 2 + (y - d["y"]) ** 2 <= r2 for x, y in cells):
                total += d["dps"]
        return total

    def weakest_exterior(self) -> tuple[int | None, float]:
        """Compartimento externo com MENOR cobertura de DPS -- candidato a
        'lado fraco' pra iniciar o ataque."""
        best_id, best_dps = None, float("inf")
        for cid in self.exterior_compartments():
            dps = self.sector_dps(cid)
            if dps < best_dps:
                best_id, best_dps = cid, dps
        return best_id, best_dps

    def edges_from(self, compartment_id: int) -> list[WallEdge]:
        return [e for e in self.edges.values() if compartment_id in (e.a, e.b)]

    def cheapest_entry(self, from_compartment: int) -> WallEdge | None:
        """Aresta (segmento de muralha) mais barata pra sair de
        `from_compartment` pra uma sala vizinha -- o funil real."""
        edges = self.edges_from(from_compartment)
        return min(edges, key=lambda e: e.hp) if edges else None

    def best_wallbreak_target(self, from_compartment: int) -> tuple[WallEdge | None, float]:
        """Entre as arestas que saem de `from_compartment`, a que abre acesso
        a MAIS DPS/predios do outro lado por HP-de-muralha gasto (espirito do
        WALL_BREAKER_SMART_* -- ver game_constants.json). Retorna (aresta, score)."""
        best_edge, best_score = None, -1.0
        for e in self.edges_from(from_compartment):
            other = e.b if e.a == from_compartment else e.a
            value = len(self.compartments.get(other, []))  # proxy simples: tamanho da sala
            value += self.sector_dps(other)                 # + quanto de defesa tem la
            score = value / max(e.hp, 1.0)
            if score > best_score:
                best_edge, best_score = e, score
        return best_edge, best_score
