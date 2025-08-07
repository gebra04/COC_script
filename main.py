# main.py

import time
import random
from config.constants import DELAY_PADRAO
from utils.mouse_actions import clicar, arrastar
from utils.image_recognition import clicar_por_imagem
from attacks.general_attacks import perder, ganhar_uma, ganhar_duas, coletar_carrinho, ajustar_hotbar
from attacks.dragon_attack import ataque_dragao
from attacks.goblin_attack import ataque_goblin

if __name__ == "__main__":
    # Sua lógica de entrada do usuário aqui
    modo = int(input("Qual modo deseja executar?\n 1 - Perder\n 2 - Ganhar\n 3 - Híbrido\n 4 - Ataque Dragão\n 5 - Ataque Goblin\n"))
    iter = int(input("Quantas vezes você deseja executar o script?"))
    
    herois = 0
    if modo >=  4:
        herois = int(input("Deseja usar heróis no ataque?\n 0 - Não\n 1 - Sim\n"))
        # Inicialização dos dicionários de heróis
        rei = {'ativo' : 0, 'sel' : None}
        rainha = {'ativo' : 0, 'sel' : None}
        guardiao = {'ativo' : 0, 'sel' : None}
        campea = {'ativo' : 0, 'sel' : None}
        sel_pocao = None
        if herois:
            rei['ativo'] = int(input("Rei Bárbaro ativo?\n 0 - Não\n 1 - Sim\n"))
            rainha['ativo'] = int(input("Rainha Arqueira ativa?\n 0 - Não\n 1 - Sim\n"))
            guardiao['ativo'] = int(input("Guardião ativo?\n 0 - Não\n 1 - Sim\n"))
            campea['ativo'] = int(input("Campeã ativa?\n 0 - Não\n 1 - Sim\n"))
            # Agora a função ajustar_hotbar está no módulo de ataques genéricos
            rei['sel'], rainha['sel'], guardiao['sel'], campea['sel'], sel_pocao = ajustar_hotbar(rei, rainha, guardiao, campea)
            print(f"sel_rei: {rei['sel']}, rainha: {rainha['sel']}, guardiao: {guardiao['sel']}, campea: {campea['sel']}, sel_pocao: {sel_pocao}")
    
    num_vilas = 2
    espera_carrinho = 5
    if modo <= 3:
        espera_carrinho = int(input("Quantas batalhas antes de coletar o carrinho?\n"))
        num_vilas = int(input("Quantas vilas na casa do construtor?\n 1 - Uma vila\n 2 - Duas vilas\n"))

    for i in range(0, iter):
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
            ataque_dragao(herois, rei, rainha, guardiao, campea, sel_pocao)
            time.sleep(2)
        
        elif modo == 5:
            ataque_goblin(herois, rei, rainha, guardiao, campea, sel_pocao)
            time.sleep(2)

        
        if i % espera_carrinho == 0 and modo <= 3 and (i != 0):
            coletar_carrinho()
        time.sleep(1)
        print(f"{i + 1}a iteração concluída.")