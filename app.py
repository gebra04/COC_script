import customtkinter as ctk
import tkinter as tk
import time
import json
import os
import keyboard
from attacks.attack_utils import coletar_carrinho, ajustar_hotbar
from attacks.builder_base import perder, ganhar_uma, ganhar_duas, hibrido
from attacks.home_base import ataque_dragao, ataque_goblin
from utils.stop_handler import wait_and_check, setup_stop_key, teardown_stop_key, reset_stop_flag, get_stop_flag

# Definindo o tema da interface
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Caminho para o arquivo de configurações
CONFIG_FILE = os.path.join('config', 'saved_configs.json')

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Script COC")
        self.geometry("550x900")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.saved_configs = {}

        self.tab_view = ctk.CTkTabview(self, command=self._on_tab_change)
        self.tab_view.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.home_tab = self.tab_view.add("Vila Principal")
        self.builder_tab = self.tab_view.add("Vila do Construtor")

        self.setup_home_tab()
        self.setup_builder_tab()
        self.setup_global_options()

        self.carregar_nomes_configs_salvas()
        
    def _on_tab_change(self):
        """Atualiza a interface com as configurações padrão ao mudar de aba."""
        self.config_selector.set("(Nenhuma)")
        current_tab = self.tab_view.get()
        if current_tab == "Vila Principal":
            self.attack_home_select.set('Ataque Dragão')
            self.heroi_rei_switch.deselect()
            self.heroi_rainha_switch.deselect()
            self.heroi_guardiao_switch.deselect()
            self.heroi_campea_switch.deselect()
            self.pocoes_select.set("4")
            self.maquina_cerco_switch.deselect()
            self.troops_select.set("2")
        elif current_tab == "Vila do Construtor":
            self.attack_builder_select.set('Perder')
            self.builder_vilas_var.set(2)
            self.carrinho_entry.delete(0, 'end')
            self.carrinho_entry.insert(0, "5")

    def setup_home_tab(self):
        ataques_home = ['Ataque Dragão', 'Ataque Goblin']
        
        ctk.CTkLabel(self.home_tab, text="Selecione o Ataque:", font=("Helvetica", 12, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        self.attack_home_select = ctk.CTkOptionMenu(self.home_tab, values=ataques_home)
        self.attack_home_select.pack(pady=5, padx=10, fill="x")

        ctk.CTkLabel(self.home_tab, text="Heróis:", font=("Helvetica", 12, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        self.frame_herois = ctk.CTkFrame(self.home_tab)
        self.frame_herois.pack(pady=5, padx=10, fill="x")
        self.heroi_rei_switch = ctk.CTkSwitch(self.frame_herois, text="Rei Bárbaro")
        self.heroi_rei_switch.pack(side="left", padx=5)
        self.heroi_rainha_switch = ctk.CTkSwitch(self.frame_herois, text="Rainha Arqueira")
        self.heroi_rainha_switch.pack(side="left", padx=5)
        self.heroi_guardiao_switch = ctk.CTkSwitch(self.frame_herois, text="Guardião")
        self.heroi_guardiao_switch.pack(side="left", padx=5)
        self.heroi_campea_switch = ctk.CTkSwitch(self.frame_herois, text="Campeã")
        self.heroi_campea_switch.pack(side="left", padx=5)

        ctk.CTkLabel(self.home_tab, text="Quantidade de Poções:", font=("Helvetica", 12, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        self.pocoes_select = ctk.CTkOptionMenu(self.home_tab, values=[str(i) for i in range(1, 11)])
        self.pocoes_select.set("4")
        self.pocoes_select.pack(pady=5, padx=10, fill="x")

        ctk.CTkLabel(self.home_tab, text="Exército:", font=("Helvetica", 12, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        self.maquina_cerco_switch = ctk.CTkSwitch(self.home_tab, text="Máquina de Cerco")
        self.maquina_cerco_switch.pack(pady=5, padx=10, anchor="w")
        
        self.troops_label = ctk.CTkLabel(self.home_tab, text="Número de tropas:", font=("Helvetica", 12, "bold"))
        self.troops_label.pack(pady=(10, 0), padx=10, anchor="w")
        self.troops_select = ctk.CTkOptionMenu(self.home_tab, values=[str(i) for i in range(1, 11)])
        self.troops_select.set("2")
        self.troops_select.pack(pady=5, padx=10, fill="x")

    def setup_builder_tab(self):
        ataques_builder = ['Perder', 'Ganhar', "Híbrido"]
        
        ctk.CTkLabel(self.builder_tab, text="Selecione o Ataque:", font=("Helvetica", 12, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        self.attack_builder_select = ctk.CTkOptionMenu(self.builder_tab, values=ataques_builder)
        self.attack_builder_select.pack(pady=5, padx=10, fill="x")

        ctk.CTkLabel(self.builder_tab, text="Vilas na Base do Construtor:", font=("Helvetica", 12, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        self.builder_vilas_var = tk.IntVar(value=2)
        self.radio_builder_1 = ctk.CTkRadioButton(self.builder_tab, text="Uma Vila", variable=self.builder_vilas_var, value=1)
        self.radio_builder_1.pack(pady=5, padx=10, anchor="w")
        self.radio_builder_2 = ctk.CTkRadioButton(self.builder_tab, text="Duas Vilas", variable=self.builder_vilas_var, value=2)
        self.radio_builder_2.pack(pady=5, padx=10, anchor="w")
        
        ctk.CTkLabel(self.builder_tab, text="Coletar Carrinho (a cada N iterações):", font=("Helvetica", 12, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        self.carrinho_entry = ctk.CTkEntry(self.builder_tab, width=50)
        self.carrinho_entry.insert(0, "5")
        self.carrinho_entry.pack(pady=5, padx=10, anchor="w")

    def setup_global_options(self):
        self.global_frame = ctk.CTkFrame(self)
        self.global_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.global_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.global_frame, text="Opções Globais:", font=("Helvetica", 12, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        
        frame_iter = ctk.CTkFrame(self.global_frame)
        frame_iter.pack(pady=5, padx=10, fill="x")
        ctk.CTkLabel(frame_iter, text="Iterações:").pack(side="left", padx=5)
        self.iter_entry = ctk.CTkEntry(frame_iter, width=50)
        self.iter_entry.insert(0, "1")
        self.iter_entry.pack(side="left", padx=5)

        ctk.CTkLabel(self.global_frame, text="Salvar/Carregar Configuração:", font=("Helvetica", 12, "bold")).pack(pady=(10, 0), padx=10, anchor="w")
        self.config_name_entry = ctk.CTkEntry(self.global_frame, placeholder_text="Nome da configuração")
        self.config_name_entry.pack(pady=5, padx=10, fill="x")

        frame_salvar = ctk.CTkFrame(self.global_frame)
        frame_salvar.pack(pady=5, padx=10, fill="x")
        ctk.CTkButton(frame_salvar, text="Salvar", command=self.salvar_config_callback).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(frame_salvar, text="Aplicar", command=self.aplicar_config_callback).pack(side="left", expand=True, padx=5)
        
        self.config_selector = ctk.CTkOptionMenu(self.global_frame, values=["(Nenhuma)"], command=self.carregar_config_selecionada)
        self.config_selector.pack(pady=5, padx=10, fill="x")

        self.run_button = ctk.CTkButton(self, text="INICIAR AUTOMAÇÃO", command=self.iniciar_automacao, fg_color="green")
        self.run_button.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.key_selector_label = ctk.CTkLabel(self, text="Tecla de atalho para encerrar o ataque:")
        self.key_selector_label.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
        self.key_selector_entry = ctk.CTkEntry(self, width=50, placeholder_text="F10")
        self.key_selector_entry.grid(row=3, column=0, padx=(230, 20), pady=(10, 20), sticky="w")
        self.key_selector_entry.insert(0, "f10")

    def log_to_console(self, message):
        print(message)

    def carregar_nomes_configs_salvas(self):
        """Carrega os nomes das configurações do arquivo JSON e atualiza o seletor global."""
        if os.path.exists(CONFIG_FILE) and os.path.getsize(CONFIG_FILE) > 0:
            with open(CONFIG_FILE, 'r') as f:
                self.saved_configs = json.load(f)
        else:
            self.saved_configs = {"Vila Principal": {}, "Vila do Construtor": {}}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.saved_configs, f, indent=4)
        
        config_keys = list(self.saved_configs.get("Vila Principal", {}).keys()) + \
                      list(self.saved_configs.get("Vila do Construtor", {}).keys())

        if not config_keys:
            self.config_selector.configure(values=["(Nenhuma)"])
            self.config_selector.set("(Nenhuma)")
        else:
            self.config_selector.configure(values=config_keys)
            self.config_selector.set(config_keys[0])

    def _get_config_data(self):
        """Retorna os dados da configuração da aba ativa."""
        current_tab = self.tab_view.get()
        config_data = {'iteracoes': self.iter_entry.get()}

        if current_tab == "Vila Principal":
            config_data.update({
                'tipo_ataque': self.attack_home_select.get(),
                'heroi_rei': {'ativo': self.heroi_rei_switch.get()},
                'heroi_rainha': {'ativo': self.heroi_rainha_switch.get()},
                'heroi_guardiao': {'ativo': self.heroi_guardiao_switch.get()},
                'heroi_campea': {'ativo': self.heroi_campea_switch.get()},
                'num_pocoes': self.pocoes_select.get(),
                'maquina_cerco': self.maquina_cerco_switch.get(),
                'num_tropas': self.troops_select.get(),
                'stop_key': self.key_selector_entry.get()
            })
        elif current_tab == "Vila do Construtor":
            config_data.update({
                'tipo_ataque': self.attack_builder_select.get(),
                'num_vilas': self.builder_vilas_var.get(),
                'espera_carrinho': self.carrinho_entry.get(),
                'stop_key': self.key_selector_entry.get()
            })
        return config_data

    def _set_config_data(self, config_data):
        """Aplica os dados de uma configuração à aba ativa."""
        current_tab = self.tab_view.get()

        self.iter_entry.delete(0, 'end')
        self.iter_entry.insert(0, str(config_data.get('iteracoes', 1)))
        
        self.key_selector_entry.delete(0, 'end')
        self.key_selector_entry.insert(0, config_data.get('stop_key', 'f10'))

        if current_tab == "Vila Principal":
            self.attack_home_select.set(config_data.get('tipo_ataque', 'Ataque Dragão'))
            
            if config_data.get('heroi_rei', {}).get('ativo', False): self.heroi_rei_switch.select()
            else: self.heroi_rei_switch.deselect()

            if config_data.get('heroi_rainha', {}).get('ativo', False): self.heroi_rainha_switch.select()
            else: self.heroi_rainha_switch.deselect()

            if config_data.get('heroi_guardiao', {}).get('ativo', False): self.heroi_guardiao_switch.select()
            else: self.heroi_guardiao_switch.deselect()

            if config_data.get('heroi_campea', {}).get('ativo', False): self.heroi_campea_switch.select()
            else: self.heroi_campea_switch.deselect()
            
            self.pocoes_select.set(config_data.get('num_pocoes', "4"))
            
            if config_data.get('maquina_cerco', False): self.maquina_cerco_switch.select()
            else: self.maquina_cerco_switch.deselect()

            self.troops_select.set(config_data.get('num_tropas', "2"))
            
        elif current_tab == "Vila do Construtor":
            self.attack_builder_select.set(config_data.get('tipo_ataque', 'Perder'))
            self.builder_vilas_var.set(config_data.get('num_vilas', 2))
            self.carrinho_entry.delete(0, 'end')
            self.carrinho_entry.insert(0, str(config_data.get('espera_carrinho', 5)))

    def salvar_config_callback(self):
        nome_config = self.config_name_entry.get()
        if not nome_config:
            self.log_to_console("Erro: Insira um nome para a configuração.")
            return

        current_tab = self.tab_view.get()
        config_data = self._get_config_data()
        
        if current_tab not in self.saved_configs:
            self.saved_configs[current_tab] = {}
        
        self.saved_configs[current_tab][nome_config] = config_data
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.saved_configs, f, indent=4)
        
        self.log_to_console(f"Configuração '{nome_config}' para '{current_tab}' salva com sucesso!")
        self.carregar_nomes_configs_salvas()
        
    def carregar_config_selecionada(self, choice):
        if choice == "(Nenhuma)":
            return

        current_tab = self.tab_view.get()
        if choice in self.saved_configs.get(current_tab, {}):
            config = self.saved_configs[current_tab][choice]
            self._set_config_data(config)
            self.log_to_console(f"Configuração '{choice}' para '{current_tab}' aplicada.")
        else:
            self.log_to_console(f"Erro: Configuração '{choice}' não encontrada para '{current_tab}'.")
    
    def aplicar_config_callback(self):
        choice = self.config_selector.get()
        self.carregar_config_selecionada(choice)
        
    def iniciar_automacao(self):
        self.log_to_console("--- INICIANDO AUTOMAÇÃO ---")
        reset_stop_flag()
        
        stop_key = self.key_selector_entry.get().strip().lower()
        setup_stop_key(stop_key)
        
        try:
            num_iteracoes = int(self.iter_entry.get())
        except ValueError:
            self.log_to_console("Erro: Insira números válidos para Iterações.")
            teardown_stop_key()
            return

        current_tab = self.tab_view.get()
        
        if current_tab == "Vila Principal":
            num_pocoes = int(self.pocoes_select.get())
            maquina_cerco = self.maquina_cerco_switch.get()
            num_tropas = int(self.troops_select.get())
            self._executar_ataque_vila_principal(num_iteracoes, num_pocoes, maquina_cerco, num_tropas)
        elif current_tab == "Vila do Construtor":
            try:
                espera_carrinho = int(self.carrinho_entry.get())
            except ValueError:
                self.log_to_console("Erro: Insira um número válido para a coleta do carrinho.")
                teardown_stop_key()
                return
            self._executar_ataque_vila_construtor(num_iteracoes, espera_carrinho)
        
        teardown_stop_key()
        if not get_stop_flag():
            self.log_to_console("--- AUTOMAÇÃO CONCLUÍDA ---")

    def _executar_ataque_vila_principal(self, num_iteracoes, num_pocoes, maquina_cerco, num_tropas):
        tipo_ataque = self.attack_home_select.get()
        
        army = {
            'rei': {'ativo': self.heroi_rei_switch.get(), 'sel': None},
            'rainha': {'ativo': self.heroi_rainha_switch.get(), 'sel': None},
            'guardiao': {'ativo': self.heroi_guardiao_switch.get(), 'sel': None},
            'campea': {'ativo': self.heroi_campea_switch.get(), 'sel': None},
            'pocoes': {'quantidade': num_pocoes, 'sel': None},
            'maquina_cerco': {'ativo': maquina_cerco, 'sel': None},
            'tropas': {'quantidade': num_tropas, 'sel': None}
        }

        army = ajustar_hotbar(army)

        for i in range(num_iteracoes):
            if get_stop_flag(): return
            
            if tipo_ataque == 'Ataque Dragão':
                ataque_dragao(army)
            elif tipo_ataque == 'Ataque Goblin':
                ataque_goblin(army)
            
            self.log_to_console(f"Vila Principal: {i + 1}a iteração concluída.")
            wait_and_check(1)

    def _executar_ataque_vila_construtor(self, num_iteracoes, espera_carrinho):
        tipo_ataque = self.attack_builder_select.get()
        num_vilas = self.builder_vilas_var.get()

        for i in range(num_iteracoes):
            if get_stop_flag(): return
                
            if tipo_ataque == 'Perder':
                perder()
            elif tipo_ataque == 'Ganhar':
                if num_vilas == 1:
                    ganhar_uma()
                else:
                    ganhar_duas()
            elif tipo_ataque == "Híbrido":
                hibrido(num_vilas)
            
            if espera_carrinho > 0 and (i + 1) % espera_carrinho == 0 and (i + 1) < num_iteracoes:
                self.log_to_console("Coletando carrinho...")
                coletar_carrinho()
            
            self.log_to_console(f"Vila do Construtor: {i + 1}a iteração concluída.")
            wait_and_check(1)

if __name__ == "__main__":
    app = App()
    app.mainloop()