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
    from attacks.home_base import ataque_goblin, ataque_dragao

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

            else:
                print("Erro: modo inválido")

            if i % espera_carrinho == 0 and modo <= 3 and (i != 0):
                coletar_carrinho()

            time.sleep(3)
            print(f"{i + 1}ª iteração concluída.")

        except Exception as e:
            print(f"Erro na iteração {i + 1}: {e}")
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
