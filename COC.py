import pyautogui
import time
import random
import os

delay = 0.3


def var ():
    """
    Função para adicionar uma variação aleatória às coordenadas dos botões.
    Isso ajuda a simular um comportamento humano e evitar detecções de automação.
    """
    return random.randint(-4, 4)


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
    'render_se': (50 + var(), 400 + var()),
    'ok': (522 + var(), 338 + var()),
    'voltar': (442 + var(), 449 + var()),
    'arrastar_inicio': (779 + var(), 264 + var()),
    'arrastar_fim': (769 + var(), 383 + var()),
    'carrinho': (614 + var(), 98 + var()),
    'coletar': (650 + var(), 450 + var()),
    'fechar': (740 + var(), 80 + var())
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
        clicar('selecionar_tropa_q')
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
    time.sleep(35)
    ataque()
    time.sleep(40)
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

    
# Executar a sequência de automação
if __name__ == "__main__":
    # Dê um tempo para você mudar para a janela do jogo
    modo = input("Qual modo deseja executar?\n 1 - Perder\n 2 - Ganhar\n 3 - Híbrido\n")
    iter = int(input("Quantas vezes você deseja executar o script?"))

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

        if i % 2 == 0:
            coletar_carrinho()
        time.sleep(3)
        print(f"{i + 1}a iteração concluída.")