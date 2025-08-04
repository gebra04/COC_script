import pyautogui
import time
import random
import os
import pytesseract
from PIL import Image
import re


delay = 0.3

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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
    return random.randint(-4, 4)


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
    'selecionar_tropa_q': (152 + var(), 470 + var()),
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
    'arrastar_baixo_ini' : (440, 331),
    'arrastar_baixo_fim' : (443, 231),
    'posicao_dragao_1' : (460 + var(), 410 + var()),
    'posicao_dragao_2' : (470 + var(), 405 + var()),
    'posicao_dragao_3' : (485 + var(), 395 + var()),
    'posicao_dragao_4' : (560 + var(), 390 + var()),
    'posicao_dragao_5' : (575 + var(), 322 + var()),
    'posicao_dragao_6' : (590 + var(), 314 + var()),
    'posicao_dragao_7' : (605 + var(), 306 + var()),
    'posicao_dragao_8' : (615 + var(), 296 + var()),
    'posicao_dragao_9' : (630 + var(), 286 + var()),
    'posicao_dragao_10' : (645 + var(), 273 + var()),
    'posicao_dragao_11' : (655 + var(), 268 + var()),
    'posicao_dragao_12' : (670 + var(), 259 + var()),
    'posicao_dragao_13' : (720 + var(), 210 + var()),
    'posicao_dragao_14' : (735 + var(), 203 + var()),
    'posicao_dragao_15' : (755 + var(), 188 + var()),
    'pocao_de_furia_1' : (478 + var(), 270 + var()),
    'pocao_de_furia_2' : (557 + var(), 225 + var()),
    'pocao_de_furia_3' : (633 + var(), 167 + var()),
    'pocao_de_furia_4' : (430 + var(), 211 + var()),
    'pocao_de_furia_5' : (508 + var(), 161 + var()),

    'arrastar_cima_ini' : (443, 37),
    'arrastar_cima_fim' : (441, 323),
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
    arrastar(botoes['arrastar_inicio'], botoes['arrastar_fim'])
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar_por_imagem('carrinho')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('coletar')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('fechar')
    time.sleep(delay + random.uniform(0.1, 0.2))


def posicionar_tropa():
        clicar('selecionar_tropa_q')
        clicar('posicionar_tropa')
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_1')
        clicar('posicionar_tropa')
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_2')
        clicar('posicionar_tropa')
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_3')
        clicar('posicionar_tropa')
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_4')
        clicar('posicionar_tropa')
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_5')
        clicar('posicionar_tropa')
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_6')
        clicar('posicionar_tropa')
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_7')
        clicar('posicionar_tropa')
        time.sleep(random.uniform(0.1, 0.2))
        clicar('selecionar_tropa_8')
        clicar('posicionar_tropa')
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
    time.sleep(9 + random.uniform(0.1, 0.2))
    clicar('selecionar_tropa_5')
    clicar('selecionar_tropa_6')
    clicar('selecionar_tropa_q')
        

def ganhar():
    procurar_partida()
    ataque()
    time.sleep(40)
    ataque()
    time.sleep(35)
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


def ataque_dragao():
    procurar_partida()
    time.sleep(3)

    # Arrastar a tela
    arrastar(botoes['arrastar_inicio_ataque'], botoes['arrastar_fim_ataque'])
    time.sleep(delay + random.uniform(0.1, 0.2))

    # Posicionar tropas de afunilamento
    clicar('selecionar_tropa_1')
    clicar('posicao_dragao_1')
    clicar('posicao_dragao_2')
    clicar('posicao_dragao_3')
    time.sleep(delay + random.uniform(0.1, 0.2))

    # Posicionar tropas de afunilamento
    clicar('posicao_dragao_13')
    clicar('posicao_dragao_14')
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
    clicar('posicao_dragao_11')
    clicar('posicao_dragao_12')
    clicar('selecionar_tropa_q')
    clicar('posicao_dragao_12')
    time.sleep(delay + random.uniform(0.1, 0.2))

    # Esperar as tropas se afunilarem
    time.sleep(8)

    # Usar poções de fúria
    clicar('selecionar_tropa_3')
    clicar('pocao_de_furia_1')
    clicar('pocao_de_furia_2')
    clicar('pocao_de_furia_3')
    # Posicionar máquina de cerco
    clicar('selecionar_tropa_2')
    clicar('posicao_dragao_10')

    # Esperar a primeira fúria acabar
    time.sleep(12)

    # Usarúltimas poções de fúria
    clicar('selecionar_tropa_3')
    clicar('pocao_de_furia_4')
    clicar('pocao_de_furia_5')

    # Esperar o ataque terminar
    time.sleep(85)
    render()
    

def ataque_goblin():
    procurar_partida()
    time.sleep(2)

    clicar('selecionar_tropa_1')
    arrastar(botoes['arrastar_baixo_ini'], botoes['arrastar_baixo_fim'])
    i = 0
    for reta in retas:
        if i == 2:
            arrastar(botoes['arrastar_cima_ini'], botoes['arrastar_cima_fim'])

        pontos = gerar_pontos_na_reta(retas[reta][0][0], retas[reta][0][1], retas[reta][1][0], retas[reta][1][1])
        for ponto in pontos:
            pyautogui.moveTo(ponto[0], ponto[1], duration=0.1)
            clicar_coordenadas(ponto)
            clicar_coordenadas(ponto)
            clicar_coordenadas(ponto)
        i += 1

    time.sleep(5)
    render()
    

    
# Executar a sequência de automação
if __name__ == "__main__":
    modo = input("Qual modo deseja executar?\n 1 - Perder\n 2 - Ganhar\n 3 - Híbrido\n 4 - Ataque Dragão\n 5 - Ataque Goblin\n")
    iter = int(input("Quantas vezes você deseja executar o script?"))
    espera_carrinho = 5
    if modo in ["1", "2", "3"]:

        espera_carrinho = int(input("Quantas batalhas antes de coletar o carrinho?\n"))

    for i in range(0, iter):
        if modo == "1":
            perder()
            time.sleep(3)

        elif modo == "2":
            ganhar()
            time.sleep(3)

        elif modo == "3":
            ganhar()
            time.sleep(3)
            perder()
            time.sleep(3)

        elif modo == "4":
            ataque_dragao()
            time.sleep(3)
        
        elif modo == "5":
            ataque_goblin()
            time.sleep(3)

        

        if i % espera_carrinho == 0 and (modo == "1" or modo == "2" or modo == "3") and (i != 0):
            coletar_carrinho()
        time.sleep(1)
        print(f"{i + 1}a iteração concluída.")

    #     recursos = verificar_recursos()
    #     print(f"Recursos verificados: {recursos}")
        