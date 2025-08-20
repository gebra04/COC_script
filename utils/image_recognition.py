# utils/image_recognition.py

import pyautogui
import os

def clicar_por_imagem(caminho_da_pasta):
    """Percorre uma pasta e tenta clicar na primeira imagem encontrada."""
    caminho_base = os.path.join(os.path.dirname(__file__), "..", "images")
    caminho_da_pasta = os.path.join(caminho_base, caminho_da_pasta)
    try:
        arquivos_na_pasta = os.listdir(caminho_da_pasta)
    except FileNotFoundError:
        print(f"Erro: A pasta '{caminho_da_pasta}' não foi encontrada.")
        return False

    for nome_do_arquivo in arquivos_na_pasta:
        if not nome_do_arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            continue

        caminho_completo = os.path.join(caminho_da_pasta, nome_do_arquivo)
        try:
            localizacao = pyautogui.locateCenterOnScreen(caminho_completo, confidence=0.8)
            if localizacao:
                pyautogui.click(localizacao)
                print(f"Clicou na imagem '{nome_do_arquivo}' em {localizacao}.")
                return True
        except pyautogui.ImageNotFoundException:
            print(f"Imagem '{nome_do_arquivo}' não encontrada na tela.")
        except Exception as e:
            print(f"Erro ao encontrar a imagem '{nome_do_arquivo}': {e}")
        
    print("Nenhuma das imagens na pasta foi encontrada.")
    return False