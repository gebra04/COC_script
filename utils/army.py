"""Composição de exército alterável (Camada 4).

Generaliza a organização de `presets.json["<preset>"]["army"]` (troops/
heroes/siege_machine/pocao) para o motor de simulação: mesma ideia — quais
unidades e QUANTAS —, mas sem os seletores de pixel (`sel`) que só faziam
sentido pro clicker legado (`attacks/home_base.py`/`attacks/attack_utils.py`).
Ver `pesquisa/08_tropas.md`/`pesquisa/09` e `PLANO_SIMULACAO.md`.

Cada slot (tropa ou feitiço) carrega uma CONTAGEM alterável, consumida
conforme o agente deploya: `try_deploy_troop`/`try_deploy_spell` decrementam
o orçamento e devolvem `False` quando esgotado — o `utils.clash_env` usa isso
pra invalidar/penalizar uma ação sem munição e pra truncar o episódio quando
o exército acaba.

`action_slots()` gera o mapeamento `Discrete(N) -> (data_id, level, is_spell)`
que vira o `ClashDigitalTwinEnv.action_space`, substituindo o
`DEFAULT_ARMY_COMPOSITION` fixo antigo (tropas 4000000..4000010 hardcoded)
por um espaço derivado da composição real passada ao ambiente.

Limitação conhecida: heróis (`heroes_active`) são só bookkeeping — sem stats
de combate porque `heroes.csv` ainda não foi extraído dos gamefiles (ver
`PROXIMOS_PASSOS.md`, Fase 1.5). Eles não entram no `action_slots()` nem no
`CombatSim` até isso ser resolvido.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from utils.spell_stats import get_spell
from utils.troop_stats import get_troop

# Rage/Fúria — o feitiço padrão do ataque de dragão (attacks/deploy_policy.py
# referencia "pocao_de_furia_1".."_5"; presets.json "Ataque_Dragao_Full" usa
# pocao.quantidade=10).
RAGE_SPELL_ID = 26000002
DRAGON_TROOP_ID = 4000008


@dataclass
class ArmySlot:
    data_id: int
    level: int
    count: int  # unidades ainda disponíveis pra deploy (alterável em runtime)

    @property
    def is_spell(self) -> bool:
        return get_spell(self.data_id) is not None

    @property
    def housing_space(self) -> int:
        d = get_spell(self.data_id) or get_troop(self.data_id)
        return int(d["housing_space"]) if d else 0


@dataclass
class ArmyComposition:
    troops: list[ArmySlot] = field(default_factory=list)
    spells: list[ArmySlot] = field(default_factory=list)
    # nome (rei/rainha/guardiao/campea) -> ativo. Sem stats de combate ainda
    # (ver docstring do módulo) — não entra em action_slots()/CombatSim.
    heroes_active: dict[str, bool] = field(default_factory=dict)

    # ------------------------------------------------------------ consumo
    @staticmethod
    def _find(slots: list[ArmySlot], data_id: int) -> ArmySlot | None:
        return next((s for s in slots if s.data_id == data_id), None)

    def try_deploy_troop(self, data_id: int) -> bool:
        s = self._find(self.troops, data_id)
        if s is None or s.count <= 0:
            return False
        s.count -= 1
        return True

    def try_deploy_spell(self, data_id: int) -> bool:
        s = self._find(self.spells, data_id)
        if s is None or s.count <= 0:
            return False
        s.count -= 1
        return True

    def try_deploy(self, data_id: int, is_spell: bool) -> bool:
        return self.try_deploy_spell(data_id) if is_spell else self.try_deploy_troop(data_id)

    def remaining(self, data_id: int) -> int:
        s = self._find(self.troops, data_id) or self._find(self.spells, data_id)
        return s.count if s else 0

    def is_exhausted(self) -> bool:
        return all(s.count <= 0 for s in self.troops) and all(s.count <= 0 for s in self.spells)

    def reset_counts(self, original: "ArmyComposition") -> None:
        """Restaura as contagens a partir de uma composição de referência
        (chamar com uma cópia "cheia" guardada à parte, no `reset()` do env)."""
        for s, o in zip(self.troops, original.troops):
            s.count = o.count
        for s, o in zip(self.spells, original.spells):
            s.count = o.count

    def clone(self) -> "ArmyComposition":
        return copy.deepcopy(self)

    # -------------------------------------------------------- espaço de ação
    def action_slots(self) -> dict[int, tuple[int, int, bool]]:
        """`Discrete(N) -> (data_id, level, is_spell)`. Ordem estável: tropas
        primeiro (ordem de inserção), depois feitiços."""
        slots: dict[int, tuple[int, int, bool]] = {}
        i = 0
        for s in self.troops:
            slots[i] = (s.data_id, s.level, False)
            i += 1
        for s in self.spells:
            slots[i] = (s.data_id, s.level, True)
            i += 1
        return slots

    @property
    def n_action_slots(self) -> int:
        return len(self.troops) + len(self.spells)

    def total_housing_used(self) -> int:
        """Espaço de tropa/feitiço ocupado pela composição CHEIA (contagem
        original, não o restante) — útil pra validar contra o orçamento."""
        return sum(s.housing_space * s.count for s in self.troops + self.spells)


def dragon_attack_army(
    dragon_level: int = 1,
    troop_housing_space: int = 300,
    rage_level: int = 1,
    rage_count: int = 5,
    spell_housing_space: int | None = None,
    include_siege_machine: bool = False,
    siege_data_id: int | None = None,
    siege_level: int = 1,
    heroes_active: dict[str, bool] | None = None,
) -> ArmyComposition:
    """Organização do ataque de dragão — mesmo espírito do preset
    `presets.json["Ataque_Dragao_Full"]` (dragões + heróis ativos + aríete +
    fúria), generalizada com contagens ALTERÁVEIS em vez de cliques em pixel
    fixo. Só dragão entra como tropa base (o objetivo declarado é o ataque de
    dragão); ajuste manualmente pra outras composições instanciando
    `ArmyComposition` direto.

    `troop_housing_space`/`spell_housing_space`: capacidade total de tropa/
    feitiço (soma dos acampamentos / fábrica de feitiços) — **valor de
    referência não confirmado para a conta do usuário**; ajuste para a vila
    real antes de treinar (ver `pesquisa/09` pra como ler isso da memória).
    Se `spell_housing_space` for None, usa `rage_count` diretamente.
    """
    dragon = get_troop(DRAGON_TROOP_ID)
    if dragon is None:
        raise RuntimeError(f"data-id {DRAGON_TROOP_ID} (Dragon) não encontrado em troop_data.json")
    dragon_count = max(0, troop_housing_space // int(dragon["housing_space"]))
    troops = [ArmySlot(DRAGON_TROOP_ID, dragon_level, dragon_count)]

    if include_siege_machine and siege_data_id is not None:
        troops.append(ArmySlot(siege_data_id, siege_level, 1))

    if spell_housing_space is not None:
        rage = get_spell(RAGE_SPELL_ID)
        rage_count = max(0, spell_housing_space // int(rage["housing_space"]))
    spells = [ArmySlot(RAGE_SPELL_ID, rage_level, rage_count)]

    return ArmyComposition(
        troops=troops,
        spells=spells,
        heroes_active=heroes_active or {"rei": True, "rainha": True, "guardiao": True, "campea": True},
    )
