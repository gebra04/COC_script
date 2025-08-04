import pyautogui
import time
import random
import os

delay = 0.3
# Definindo as coordenadas dos botões
botoes = {
    'atacar': (45, 473),
    'encontrar': (660, 350),
    'selecionar_tropa': (212, 470),
    'posicionar_tropa': (866, 276),
    'render_se': (50, 400),
    'ok': (522, 338),
    'voltar': (442, 449),
    'arrastar_inicio': (779, 264),
    'arrastar_fim': (769, 383),
    'carrinho': (614, 98),  # Coordenada a ser obtida
    'coletar': (650, 450),
    'fechar': (740, 80)
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

def perder_mesmo():
    clicar('selecionar_tropa')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('posicionar_tropa')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('render_se')
    time.sleep(delay + random.uniform(0.1, 0.2))

    clicar('ok')
    time.sleep(delay + random.uniform(0.1, 0.2))

def perder():    

    procurar_partida()
    perder_mesmo()

    
# Executar a sequência de automação
if __name__ == "__main__":
    # Dê um tempo para você mudar para a janela do jogo
    modo = input("Qual modo deseja executar?\n 1 - Perder\n 2 - Ganhar\n")
    iter = int(input("Quantas vezes você deseja executar o script?"))
    # iter = 1
    # print("Você tem 3 segundos para focar na janela do jogo...")
    # time.sleep(3)
    for _ in range(0, iter):
        if modo == "1":
            perder()
        elif modo == "2":
            print("Modo ganhar não implementado.")
            # ganhar()
        if iter % 5 == 1:
            coletar_carrinho()