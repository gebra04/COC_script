# utils/stop_handler.py

import time
import keyboard

# Flag de controle global
_stop_flag = False

def set_stop_flag():
    """Ativa a flag de parada."""
    global _stop_flag
    _stop_flag = True
    print("\n--- Execução interrompida pela tecla de atalho ---")

def reset_stop_flag():
    """Reseta a flag de parada para False."""
    global _stop_flag
    _stop_flag = False

def get_stop_flag():
    """Retorna o estado atual da flag de parada."""
    global _stop_flag
    return _stop_flag

def wait_and_check(duration_s, interval_ms=100):
    """
    Espera por uma duração específica, verificando a cada intervalo
    curto se a flag de parada foi ativada.
    Retorna True se a execução foi interrompida, False caso contrário.
    """
    global _stop_flag
    if _stop_flag:
        return True
    
    start_time = time.time()
    while (time.time() - start_time) < duration_s:
        if _stop_flag:
            return True
        time.sleep(interval_ms / 1000)
    
    return False

def setup_stop_key(key):
    """Configura a tecla de atalho para interromper a execução."""
    if key:
        try:
            keyboard.add_hotkey(key, set_stop_flag)
            print(f"Tecla '{key}' configurada para interromper o ataque.")
        except ValueError:
            print(f"Erro: A tecla '{key}' não é válida. Usando a tecla padrão 'f10'.")
            keyboard.add_hotkey('f10', set_stop_flag)
    else:
        print("Nenhuma tecla de atalho configurada. O ataque não poderá ser interrompido manualmente.")

def teardown_stop_key():
    """Desabilita todas as teclas de atalho configuradas."""
    keyboard.unhook_all()