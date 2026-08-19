# main.py

import time
import json
import os


def carregar_presets():
    """Carrega os presets do arquivo JSON."""
    if os.path.exists('presets.json'):
        with open('presets.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def salvar_presets(presets):
    """Salva os presets no arquivo JSON."""
    with open('presets.json', 'w', encoding='utf-8') as f:
        json.dump(presets, f, indent=2, ensure_ascii=False)


def iniciar_bot(config):
    """
    Função principal que executa o bot baseado na configuração fornecida.

    Args:
        config (dict): Dicionário com a configuração do ataque.
            Deve conter: modo, iteracoes, espera_carrinho, castelo, army

    Nota: Os imports são feitos aqui (lazy loading) para evitar dependências
    de X11 quando a GUI é carregada sem display gráfico.
    """
    # Importações lazy - apenas quando o bot vai ser executado
    from attacks.attack_utils import coletar_carrinho, ajustar_hotbar, abastecer_castelo
    from attacks.builder_base import perder, ganhar_uma, ganhar_duas
    from attacks.home_base import ataque_goblin, ataque_dragao, ataque_rapido

    modo = config.get('modo', 1)
    iter = config.get('iteracoes', 1)
    army = config.get('army', {})
    espera_carrinho = config.get('espera_carrinho', 5)
    castelo = config.get('castelo', 0)
    num_vilas = config.get('num_vilas', 2)

    # Ajustar hotbar se aplicável
    if modo >= 4 and army:
        army = ajustar_hotbar(army)

    for i in range(0, iter):
        try:
            if modo == 1:
                perder()
                time.sleep(2)

            elif modo == 2:
                if num_vilas == 1:
                    ganhar_uma()
                else:
                    ganhar_duas()
                time.sleep(2)

            elif modo == 3:
                if num_vilas == 1:
                    ganhar_uma()
                else:
                    ganhar_duas()
                time.sleep(2)
                perder()
                time.sleep(2)

            elif modo == 4:
                if castelo:
                    abastecer_castelo()
                ataque_dragao(army)
                time.sleep(8)

            elif modo == 5:
                if castelo:
                    abastecer_castelo()
                ataque_goblin(army)
                time.sleep(8)

            elif modo == 6:
                if castelo:
                    abastecer_castelo()
                tempo_ataque = config.get('tempo_ataque', 35)
                ataque_rapido(army, tempo_ataque=tempo_ataque)

            else:
                print("Erro: modo inválido")

            if i % espera_carrinho == 0 and modo <= 3 and (i != 0):
                coletar_carrinho()

            time.sleep(3)
            print(f"{i + 1}ª iteração concluída.")

        except Exception as e:
            print(f"Erro na iteração {i + 1}: {e}")
            break


def iniciar_gemeo_digital(config):
    """
    Executa o loop de inferência do agente H-PPO sobre o Gêmeo Digital (Camada 4).

    Arquitetura B (ver `pesquisa/06`): a base inimiga é escaneada UMA VEZ
    (`utils.base_loader`, leitor externo passivo — não injeta/hooka o jogo) e
    o combate inteiro é SIMULADO por `utils.combat_sim`/`utils.attack_simulator`,
    não observado ao vivo. Modo "sombra": monta a base + o exército, roda o
    `ActorCriticHybridNetwork` amostrando ações, imprimindo ação/recompensa/
    valor estimado. Não aciona nenhum input real no jogo — a tradução da ação
    amostrada em toque real fica pro atuador (`utils/adb_actuator.py`), fora
    do escopo desta função de demonstração.

    Args:
        config (dict): Pode conter:
            base_path (str): captura de base salva (`utils.base_loader.save_base`).
            pid (str|int, padrão "auto"): se `base_path` não for dado, tenta
                escanear a base carregada ao vivo (Waydroid aberto, ver
                `utils.base_loader.read_enemy_base`).
            troop_housing_space (int, padrão 300), rage_count (int, padrão 5):
                repassados a `utils.army.dragon_attack_army` — ajuste pra vila real.
            grid_size (int, padrão `utils.battle_grid.GRID_SIZE`=44),
            passos (int, padrão 100).

    Nota: Os imports são feitos aqui (lazy loading) porque dependem de
    `torch`/`gymnasium`/`numpy`, desnecessários para o fluxo legado de
    automação visual.
    """
    from utils import base_loader
    from utils.army import dragon_attack_army
    from utils.battle_grid import GRID_SIZE
    from utils.clash_env import ClashDigitalTwinEnv
    from utils.hppo_network import ActorCriticHybridNetwork, observation_to_tensors

    grid_size = config.get('grid_size', GRID_SIZE)
    passos = config.get('passos', 100)
    army = dragon_attack_army(
        troop_housing_space=config.get('troop_housing_space', 300),
        rage_count=config.get('rage_count', 5),
    )

    base_path = config.get('base_path')
    if base_path:
        base_entities = base_loader.load_base(base_path)
    else:
        base_entities = base_loader.read_enemy_base(pid=config.get('pid', 'auto'))
    print(f"[GêmeoDigital] base: {base_loader.base_report(base_entities)}")

    env = ClashDigitalTwinEnv(base_entities=base_entities, army=army, grid_size=grid_size)
    net = ActorCriticHybridNetwork(action_dim=env.action_space["type"].n, grid_size=grid_size)

    obs, _info = env.reset()
    for passo in range(passos):
        grid_tensor, global_tensor = observation_to_tensors(obs)
        action, value = net.sample_action(grid_tensor, global_tensor)

        obs, reward, terminated, truncated, _info = env.step(action)
        print(
            f"[GêmeoDigital] passo={passo} ação={action} "
            f"V(s)={value.item():.4f} recompensa={reward:.4f}"
        )

        if terminated or truncated:
            print("[GêmeoDigital] episódio encerrado.")
            break


if __name__ == "__main__":
    # Para testes diretos via terminal (deixado para compatibilidade)
    presets = carregar_presets()
    if presets:
        primeiro_preset = list(presets.keys())[0]
        config = presets[primeiro_preset]
        iniciar_bot(config)
    else:
        print("Nenhum preset disponível.")
