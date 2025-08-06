import pyautogui
import time
import random
import os


delay = 0.3

cantos = {
    # Baixo
    'EB' : (66, 181),
    'B' : (445, 443),
    'DB' : (834, 183),
    # Cima
    'EC' : (42, 338),
    'C' : (433, 54),
    'DC' : (810, 339)
}

retas = {
    'EB' : (cantos['EB'], cantos['B']),
    'DB' : (cantos['DB'], cantos['B']),
    'EC' : (cantos['EC'], cantos['C']),
    'DC' : (cantos['DC'], cantos['C'])
}


def var ():
    """
    Função para adicionar uma variação aleatória às coordenadas dos botões.
    Isso ajuda a simular um comportamento humano e evitar detecções de automação.
    """
    return random.randint(-2, 2)


def gerar_pontos_na_reta(xi, yi, xf, yf, num_pontos=8):
    """
    Gera uma lista de pontos inteiros aleatórios que se encontram no segmento
    de reta entre (xi, yi) e (xf, yf).

    Args:
        xi (float): Coordenada X do ponto inicial.
        yi (float): Coordenada Y do ponto inicial.
        xf (float): Coordenada X do ponto final.
        yf (float): Coordenada Y do ponto final.
        num_pontos (int): O número de pontos a serem gerados.

    Returns:
        list: Uma lista de tuplas, onde cada tupla é um ponto (x, y) com valores inteiros.
    """
    pontos = []
    
    for _ in range(num_pontos):
        fator_aleatorio = random.uniform(0, 1)
        x = int(round(xi + (xf - xi) * fator_aleatorio))
        y = int(round(yi + (yf - yi) * fator_aleatorio))
        pontos.append((x, y))
        
    return pontos


botoes = {
    'atacar': (45 + var(), 473 + var()),
    'encontrar': (660 + var(), 350 + var()),
    'selecionar_tropa_0': (152 + var(), 470 + var()),
    'selecionar_tropa_1': (212 + var(), 470 + var()),
    'selecionar_tropa_2': (272 + var(), 470 + var()),
    'selecionar_tropa_3': (332 + var(), 470 + var()),
    'selecionar_tropa_4': (392 + var(), 470 + var()),
    'selecionar_tropa_5': (452 + var(), 470 + var()),
    'selecionar_tropa_6': (512 + var(), 470 + var()),
    'selecionar_tropa_7': (572 + var(), 470 + var()),
    'selecionar_tropa_8': (632 + var(), 470 + var()),
    'posicionar_tropa': (866 + var(), 276 + var()),
    'render_se': (55 + var(), 420 + var()),
    'ok': (522 + var(), 338 + var()),
    'voltar': (442 + var(), 449 + var()),
    'arrastar_inicio': (779 + var(), 264 + var()),
    'arrastar_fim': (779 + var(), 400 + var()),
    'carrinho': (614 + var(), 98 + var()),
    'coletar': (650 + var(), 450 + var()),
    'fechar': (740 + var(), 80 + var()),
    'posicao_dragao_1' : (470 + var(), 420 + var()),
    'posicao_dragao_2' : (480 + var(), 415 + var()),
    'posicao_dragao_3' : (495 + var(), 405 + var()),
    'posicao_dragao_4' : (570 + var(), 400 + var()),
    'posicao_dragao_5' : (585 + var(), 332 + var()),
    'posicao_dragao_6' : (600 + var(), 324 + var()),
    'posicao_dragao_7' : (615 + var(), 316 + var()),
    'posicao_dragao_8' : (625 + var(), 306 + var()),
    'posicao_dragao_9' : (640 + var(), 296 + var()),
    'posicao_dragao_10' : (655 + var(), 283 + var()),
    'posicao_dragao_11' : (665 + var(), 278 + var()),
    'posicao_dragao_12' : (680 + var(), 269 + var()),
    'posicao_dragao_13' : (730 + var(), 230 + var()),
    'posicao_dragao_14' : (745 + var(), 213 + var()),
    'posicao_dragao_15' : (765 + var(), 198 + var()),
    'pocao_de_furia_1' : (478 + var(), 270 + var()),
    'pocao_de_furia_2' : (557 + var(), 225 + var()),
    'pocao_de_furia_3' : (633 + var(), 167 + var()),
    'pocao_de_furia_4' : (430 + var(), 211 + var()),
    'pocao_de_furia_5' : (508 + var(), 161 + var()),

    'arrastar_cima' : (441, 37),
    'arrastar_baixo' : (441, 323),
}


def clicar_por_imagem(caminho_da_pasta):
    """
    Percorre todos os arquivos de imagem em uma pasta e tenta clicar na primeira
    imagem encontrada na tela.
    """
    # Lista todos os arquivos na pasta
    try:
        arquivos_na_pasta = os.listdir(caminho_da_pasta)
    except FileNotFoundError:
        print(f"Erro: A pasta '{caminho_da_pasta}' não foi encontrada.")
        return False

    for nome_do_arquivo in arquivos_na_pasta:
        # Pula arquivos que não sejam de imagem (ou de interesse)
        if not nome_do_arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            continue

        # Cria o caminho completo para o arquivo de imagem
        caminho_completo_imagem = os.path.join(caminho_da_pasta, nome_do_arquivo)
        print(f"Tentando encontrar a imagem: {caminho_completo_imagem}")

        try:
            # Tenta encontrar a imagem na tela com 80% de confiança
            localizacao = pyautogui.locateCenterOnScreen(caminho_completo_imagem, confidence=0.3)

            if localizacao:
                pyautogui.click(localizacao)
                print(f"Clicou na imagem '{nome_do_arquivo}' nas coordenadas {localizacao}.")
                return True  # Retorna True e encerra a função assim que encontrar
            
        except pyautogui.PyAutoGUIException as e:
            # O erro aqui pode ser por causa do arquivo corrompido, por exemplo
            print(f"Erro ao tentar encontrar a imagem '{nome_do_arquivo}': {e}")
        
        except IOError as e:
            # Erro de leitura de arquivo
            print(f"Erro de leitura no arquivo '{nome_do_arquivo}': {e}")
            
    # Se o loop terminar e nenhuma imagem for encontrada
    print("Nenhuma das imagens na pasta foi encontrada na tela.")
    return False


def coletar_carrinho():
    """
    Função para coletar o carrinho de recursos.
    """
    arrastar(botoes['arrastar_cima'], botoes['arrastar_baixo'])
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar_por_imagem('carrinho')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('coletar')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('fechar')
    time.sleep(delay + random.uniform(0.1, 0.2))


def posicionar_tropa():
        arrastar(botoes['arrastar_baixo'], botoes['arrastar_cima'])
        clicar('selecionar_tropa_0')
        clicar_coordenadas((444, 360))
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_1')
        clicar_coordenadas((444, 360))
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_2')
        clicar_coordenadas((444, 360))
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_3')
        clicar_coordenadas((444, 360))
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_4')
        clicar_coordenadas((444, 360))
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_5')
        clicar_coordenadas((444, 360))
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_6')
        clicar_coordenadas((444, 360))
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_7')
        clicar_coordenadas((444, 360))
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_8')
        clicar_coordenadas((444, 360))
        time.sleep(random.uniform(0.1, 0.2))


def procurar_partida():
    """ 
    Função para procurar uma partida.
    """
    clicar('atacar')
    time.sleep(delay + random.uniform(0.1, 0.2))
    
    clicar('encontrar')
    time.sleep(delay + 5 + random.uniform(0.1, 0.2))


def clicar(nome_do_botao, duracao_clique=0.1):
    """
    Função para clicar em um botão com base no seu nome no dicionário.
    Adiciona um pequeno atraso aleatório para simular um comportamento humano.
    """
    if nome_do_botao in botoes:
        x, y = botoes[nome_do_botao]
        # Adiciona uma variação aleatória para o tempo de espera
        espera_aleatoria = random.uniform(0.1, 0.2)
        time.sleep(espera_aleatoria)
        pyautogui.click(x, y, duration=duracao_clique)
        print(f"Botão '{nome_do_botao}' clicado em ({x}, {y}).")
    else:
        print(f"Erro: Botão '{nome_do_botao}' não encontrado nas coordenadas.")


def clicar_coordenadas(coordenadas, duracao_clique=0.1):
    """
    Função para clicar em coordenadas específicas.
    Adiciona um pequeno atraso aleatório para simular um comportamento humano.
    """
    x, y = coordenadas
    espera_aleatoria = random.uniform(0.1, 0.2)
    time.sleep(espera_aleatoria)
    pyautogui.click(x, y, duration=duracao_clique)
    print(f"Clicado em coordenadas ({x}, {y}).")


def arrastar(inicio, fim, duracao=1):
    """
    Função para arrastar de um ponto inicial para um ponto final.
    """
    print(f"Iniciando arrasto de {inicio} para {fim}...")
    pyautogui.moveTo(inicio[0], inicio[1], duration=0.5)
    pyautogui.mouseDown(inicio[0], inicio[1])
    pyautogui.moveTo(fim[0], fim[1], duration=duracao)
    pyautogui.mouseUp(fim[0], fim[1])
    print("Arrasto concluído.")


def ajustar_hotbar(rei, rainha_arq, guardiao, campea):
    """
    Ajusta a hotbar de acordo com os heróis selecionados.
    Retorna as coordenadas dos botões ajustados.
    """
    sel_rei, sel_rainha, sel_guardiao, sel_campea, sel_pocao = None, None, None, None, None

    if guardiao['ativo']:
        sel_guardiao = f"selecionar_tropa_{3}"
    if rainha_arq['ativo']:
        sel_rainha = f"selecionar_tropa_{3+guardiao['ativo']}"
    if rei['ativo']:
        sel_rei = f"selecionar_tropa_{3+guardiao['ativo']+rainha['ativo']}"
    if campea['ativo']:
        sel_campea = f"selecionar_tropa_{3+guardiao['ativo']+rainha['ativo']+rei['ativo']}"

    sel_pocao = f"selecionar_tropa_{3+guardiao['ativo']+rainha['ativo']+rei['ativo']+campea['ativo']}"

    return sel_rei, sel_rainha, sel_guardiao, sel_campea, sel_pocao


def render():

    clicar('render_se')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('ok')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('voltar')
    time.sleep(delay + random.uniform(0.1, 0.2))


def ataque():
    """
    Função para realizar um ataque.
    """
    posicionar_tropa()
    # Acionar habilidades ao longo do ataque
    time.sleep(8 + random.uniform(0.1, 0.2))
    clicar('selecionar_tropa_1')
    clicar('selecionar_tropa_2')
    clicar('selecionar_tropa_7')
    clicar('selecionar_tropa_8')
    time.sleep(9 + random.uniform(0.1, 0.2))
    clicar('selecionar_tropa_3')
    clicar('selecionar_tropa_4')
    time.sleep(3)
    clicar('selecionar_tropa_0')
    time.sleep(9 + random.uniform(0.1, 0.2))
    clicar('selecionar_tropa_5')
    clicar('selecionar_tropa_6')
    # clicar('selecionar_tropa_0') Para  maquina voadora


def ganhar_uma():
    procurar_partida()
    ataque()
    time.sleep(40)

    clicar('render_se')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('ok')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('voltar')
    time.sleep(delay + random.uniform(0.1, 0.2))


def ganhar_duas():
    procurar_partida()
    ataque()
    time.sleep(60)
    ataque()
    time.sleep(22)
    clicar('render_se')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('ok')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('voltar')
    time.sleep(delay + random.uniform(0.1, 0.2))


def perder():    
    procurar_partida()

    clicar('selecionar_tropa_1')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('posicionar_tropa')
    time.sleep(delay + random.uniform(0.1, 0.2))
    
    render()


def ataque_dragao(herois, rei, rainha, guardiao, campea, sel_pocao):
    procurar_partida()
    time.sleep(3)

    # Arrastar a tela
    arrastar(botoes['arrastar_baixo'], botoes['arrastar_cima'])
    time.sleep(delay + random.uniform(0.1, 0.2))

    # Posicionar tropas de afunilamento
    if herois:
        if rei['ativo']:
            clicar(rei['sel'])
            clicar('posicao_dragao_1')
            clicar('selecionar_tropa_2')
            clicar('posicao_dragao_1')
            
    clicar('selecionar_tropa_1')
    clicar('posicao_dragao_1')
    clicar('posicao_dragao_2')
    
    time.sleep(delay + random.uniform(0.1, 0.2))

    # Posicionar tropas de afunilamento
    clicar('posicao_dragao_13')
    clicar('posicao_dragao_14')
    clicar('posicao_dragao_15')

    if herois:
        if campea['ativo']:
            clicar(campea['sel'])
            clicar('posicao_dragao_15')
    time.sleep(delay + random.uniform(0.1, 0.2))

    # Posicionar tropas centrais
    clicar('posicao_dragao_4')
    clicar('posicao_dragao_5')
    clicar('posicao_dragao_6')
    clicar('posicao_dragao_7')
    clicar('posicao_dragao_8')
    clicar('posicao_dragao_9')
    clicar('posicao_dragao_10')
    clicar('posicao_dragao_10')
    clicar('posicao_dragao_11')
    clicar('posicao_dragao_12')
    clicar('selecionar_tropa_0')
    clicar('posicao_dragao_12')
    if herois:
        if guardiao['ativo']:
            clicar(guardiao['sel'])
            clicar('posicao_dragao_6')
        if rainha['ativo']:
            clicar(rainha['sel'])
            clicar('posicao_dragao_6')
    time.sleep(delay + random.uniform(0.1, 0.2))

    # Esperar as tropas se afunilarem
    time.sleep(8)

    # Usar poções de fúria
    clicar(sel_pocao)
    clicar('pocao_de_furia_1')
    clicar('pocao_de_furia_2')
    clicar('pocao_de_furia_3')
    # Posicionar máquina de cerco
    if not rei['ativo']:
        clicar('selecionar_tropa_2')
        clicar('posicao_dragao_10')

    # Esperar a primeira fúria acabar
    time.sleep(12)

    # Usar últimas poções de fúria
    clicar(sel_pocao)
    clicar('pocao_de_furia_4')
    clicar('pocao_de_furia_5')

    time.sleep(2)
    # Ativar habilidades dos heróis
    if herois:
        clicar(guardiao['sel']) if guardiao['ativo'] else None
        clicar(rainha['sel']) if rainha['ativo'] else None
        clicar(rei['sel']) if rei['ativo'] else None
        clicar(campea['sel']) if campea['ativo'] else None

    # Esperar o ataque terminar
    time.sleep(85)
    render()
    

def ataque_goblin(herois, rei, rainha, guardiao, campea, sel_pocao):
    procurar_partida()
    time.sleep(2)

    arrastar(botoes['arrastar_cima'], botoes['arrastar_baixo'])
    if herois:
        if rei['ativo']:
            clicar(rei['sel'])
            clicar_coordenadas(cantos['C'])
        if campea['ativo']:
            clicar(campea['sel'])
            clicar_coordenadas(cantos['C'])
        if guardiao['ativo']:
            clicar(guardiao['sel'])
            clicar_coordenadas(cantos['C'])
        if rainha['ativo']:
            clicar(rainha['sel'])
            clicar_coordenadas(cantos['C'])

    clicar('selecionar_tropa_0')
    clicar_coordenadas(cantos['C'])
    clicar('selecionar_tropa_2')
    clicar_coordenadas(cantos['C'])

    arrastar(botoes['arrastar_baixo'], botoes['arrastar_cima'])
    i = 0

    clicar('selecionar_tropa_1')
    for reta in retas:
        if i == 2:                           
            arrastar(botoes['arrastar_cima'], botoes['arrastar_baixo'])
            clicar(sel_pocao)
            clicar_coordenadas((440, 200))
            clicar_coordenadas((440, 260))
            clicar_coordenadas((440, 320))
            clicar('selecionar_tropa_1')

        if i == 3:
            if herois:
                if rei['ativo']:
                    clicar(rei['sel'])
                if campea['ativo']:
                    clicar(campea['sel'])
                if guardiao['ativo']:
                    clicar(guardiao['sel'])
                if rainha['ativo']:
                    clicar(rainha['sel'])
            clicar(sel_pocao)
            clicar_coordenadas((380, 310))
            clicar_coordenadas((500, 310))
            clicar('selecionar_tropa_1')



        pontos = gerar_pontos_na_reta(retas[reta][0][0], retas[reta][0][1], retas[reta][1][0], retas[reta][1][1])
        for ponto in pontos:
            pyautogui.moveTo(ponto[0], ponto[1], duration=0.1)
            clicar_coordenadas(ponto)
            clicar_coordenadas(ponto)
            clicar_coordenadas(ponto)            
                
        i += 1

    time.sleep(15)
    render()
    

    
# Executar a sequência de automação
if __name__ == "__main__":
    modo = int(input("Qual modo deseja executar?\n 1 - Perder\n 2 - Ganhar\n 3 - Híbrido\n 4 - Ataque Dragão\n 5 - Ataque Goblin\n"))
    iter = int(input("Quantas vezes você deseja executar o script?"))
    herois = 0
    if modo >=  4:
        herois = int(input("Deseja usar heróis no ataque?\n 0 - Não\n 1 - Sim\n"))
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

    #     recursos = verificar_recursos()
    #     print(f"Recursos verificados: {recursos}")
        