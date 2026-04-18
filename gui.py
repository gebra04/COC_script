import customtkinter as ctk
import threading
import json
import os

# Importação lazy para evitar dependências de X11 na GUI
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


def importar_iniciar_bot():
    """Importação lazy de iniciar_bot para evitar carregamento de pyautogui."""
    from main import iniciar_bot
    return iniciar_bot
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class COCBotGUI(ctk.CTk):
    """Interface gráfica para o bot de Clash of Clans."""
    
    def __init__(self):
        super().__init__()
        
        self.title("COC Bot - Automação de Ataques")
        self.geometry("800x600")
        self.resizable(True, True)
        
        self.bot_rodando = False
        self.thread_bot = None
        
        # Configurar grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Criar frame de abas
        self.abas = ctk.CTkTabview(self)
        self.abas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Aba 1: Executar Ataque
        self.aba_executar = self.abas.add("Executar Ataque")
        self._criar_aba_executar()
        
        # Aba 2: Criar/Editar Presets
        self.aba_presets = self.abas.add("Criar/Editar Presets")
        self._criar_aba_presets()
    
    
    # ==================== ABA 1: EXECUTAR ATAQUE ====================
    
    def _criar_aba_executar(self):
        """Cria a aba para executar ataques."""
        
        # Configurar grid da aba  
        self.aba_executar.grid_columnconfigure(0, weight=1)
        self.aba_executar.grid_rowconfigure(1, weight=1)
        
        # ========== SEÇÃO FIXA: SELEÇÃO ==========
        # Frame para seleção de preset
        frame_selecao = ctk.CTkFrame(self.aba_executar)
        frame_selecao.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        frame_selecao.grid_columnconfigure(1, weight=1)
        
        label_preset = ctk.CTkLabel(frame_selecao, text="Selecione um Preset:", font=("Arial", 14, "bold"))
        label_preset.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.combo_presets = ctk.CTkComboBox(
            frame_selecao,
            values=self._obter_nomes_presets(),
            state="readonly",
            font=("Arial", 12)
        )
        self.combo_presets.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.combo_presets.set("Selecione um preset")
        self.combo_presets.configure(command=self._atualizar_info_preset)
        
        # ========== SEÇÃO SCROLLÁVEL: INFORMAÇÕES ==========
        scroll_frame = ctk.CTkScrollableFrame(self.aba_executar)
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=10)
        
        label_info = ctk.CTkLabel(scroll_frame, text="Informações do Preset:", font=("Arial", 12, "bold"))
        label_info.pack(anchor="w", padx=15, pady=(10, 5))
        
        self.text_info = ctk.CTkTextbox(scroll_frame, height=150, font=("Courier", 10))
        self.text_info.pack(fill="both", expand=True, padx=15, pady=5)
        self.text_info.configure(state="disabled")
        
        # Frame para status de execução (dentro do scroll)
        frame_status = ctk.CTkFrame(scroll_frame)
        frame_status.pack(fill="x", padx=15, pady=10)
        frame_status.grid_columnconfigure(1, weight=1)
        
        label_status = ctk.CTkLabel(frame_status, text="Status:", font=("Arial", 12, "bold"))
        label_status.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.label_status_valor = ctk.CTkLabel(frame_status, text="Aguardando...", text_color="gray", font=("Arial", 11))
        self.label_status_valor.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        # ========== SEÇÃO FIXA: BOTÕES ==========
        frame_botoes = ctk.CTkFrame(self.aba_executar)
        frame_botoes.grid(row=2, column=0, sticky="ew", padx=15, pady=15)
        frame_botoes.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.btn_iniciar = ctk.CTkButton(
            frame_botoes,
            text="▶ Iniciar Ataque",
            command=self._iniciar_ataque,
            font=("Arial", 13, "bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.btn_iniciar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        self.btn_parar = ctk.CTkButton(
            frame_botoes,
            text="⏹ Parar",
            command=self._parar_ataque,
            state="disabled",
            font=("Arial", 13, "bold"),
            fg_color="red",
            hover_color="darkred"
        )
        self.btn_parar.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        btn_recarregar = ctk.CTkButton(
            frame_botoes,
            text="🔄 Recarregar Presets",
            command=self._recarregar_presets,
            font=("Arial", 13, "bold"),
            fg_color="gray",
            hover_color="darkgray"
        )
        btn_recarregar.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
    
    
    def _obter_nomes_presets(self):
        """Retorna lista de nomes de presets."""
        presets = carregar_presets()
        return list(presets.keys()) if presets else []
    
    
    def _atualizar_info_preset(self, preset_nome):
        """Atualiza as informações do preset selecionado."""
        presets = carregar_presets()
        
        if preset_nome in presets:
            config = presets[preset_nome]
            texto = f"""
Preset: {preset_nome}

Modo: {self._nome_modo(config.get('modo', 1))}
Iterações: {config.get('iteracoes', 1)}
Espera entre coletas: {config.get('espera_carrinho', 5)} batalhas
Abastecer castelo: {'Sim' if config.get('castelo') else 'Não'}

Exército:
  - Tropas: {config.get('army', {}).get('troops', {}).get('quantidade', 0)} unidades
  - Rei Bárbaro: {'Ativo' if config.get('army', {}).get('rei', {}).get('ativo') else 'Inativo'}
  - Rainha Arqueira: {'Ativa' if config.get('army', {}).get('rainha', {}).get('ativo') else 'Inativa'}
  - Guardião: {'Ativo' if config.get('army', {}).get('guardiao', {}).get('ativo') else 'Inativo'}
  - Campeã: {'Ativa' if config.get('army', {}).get('campea', {}).get('ativo') else 'Inativa'}
  - Poções: {config.get('army', {}).get('pocao', {}).get('quantidade', 0)} unidades
  - Máquina de Cerco: {'Ativa' if config.get('army', {}).get('siege_machine', {}).get('ativo') else 'Inativa'}
            """
            
            self.text_info.configure(state="normal")
            self.text_info.delete("1.0", "end")
            self.text_info.insert("1.0", texto.strip())
            self.text_info.configure(state="disabled")
    
    
    def _nome_modo(self, modo):
        """Retorna o nome descritivo do modo."""
        modos = {
            1: "Perder",
            2: "Ganhar (1 vila)",
            3: "Híbrido",
            4: "Ataque Dragão",
            5: "Ataque Goblin"
        }
        return modos.get(modo, "Desconhecido")
    
    
    def _iniciar_ataque(self):
        """Inicia o ataque em thread separada."""
        preset_nome = self.combo_presets.get()
        
        if preset_nome == "Selecione um preset" or not preset_nome:
            self._mostrar_mensagem_erro("Selecione um preset válido")
            return
        
        presets = carregar_presets()
        if preset_nome not in presets:
            self._mostrar_mensagem_erro("Preset não encontrado")
            return
        
        config = presets[preset_nome]
        
        # Desabilitar botão e iniciar thread
        self.btn_iniciar.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.bot_rodando = True
        self.label_status_valor.configure(text=f"Executando: {preset_nome}...", text_color="green")
        
        # Criar e iniciar thread do bot
        self.thread_bot = threading.Thread(
            target=self._executar_ataque_thread,
            args=(config, preset_nome),
            daemon=False
        )
        self.thread_bot.start()
    
    
    def _executar_ataque_thread(self, config, preset_nome):
        """Executa o ataque em thread separada."""
        try:
            # Importação lazy aqui para evitar erro de X11 enquanto a GUI está aberta
            iniciar_bot = importar_iniciar_bot()
            iniciar_bot(config)
            if self.bot_rodando:
                self.label_status_valor.configure(text=f"Concluído: {preset_nome}", text_color="green")
        except Exception as e:
            self.label_status_valor.configure(text=f"Erro: {str(e)}", text_color="red")
        finally:
            self.bot_rodando = False
            self.btn_iniciar.configure(state="normal")
            self.btn_parar.configure(state="disabled")
    
    
    def _parar_ataque(self):
        """Para a execução do ataque."""
        self.bot_rodando = False
        self.label_status_valor.configure(text="Parado pelo usuário", text_color="orange")
        self.btn_iniciar.configure(state="normal")
        self.btn_parar.configure(state="disabled")
    
    
    def _recarregar_presets(self):
        """Recarrega a lista de presets."""
        nomes = self._obter_nomes_presets()
        self.combo_presets.configure(values=nomes)
        self.combo_presets.set("Selecione um preset")
        self.text_info.configure(state="normal")
        self.text_info.delete("1.0", "end")
        self.text_info.configure(state="disabled")
        self.label_status_valor.configure(text="Presets recarregados", text_color="green")
    
    
    def _mostrar_mensagem_erro(self, mensagem):
        """Mostra mensagem de erro no status."""
        self.label_status_valor.configure(text=f"Erro: {mensagem}", text_color="red")
    
    
    # ==================== ABA 2: CRIAR/EDITAR PRESETS ====================
    
    def _criar_aba_presets(self):
        """Cria a aba para criar/editar presets com scroll."""
        
        # Configurar grid da aba
        self.aba_presets.grid_columnconfigure(0, weight=1)
        self.aba_presets.grid_rowconfigure(1, weight=1)
        
        # ========== SEÇÃO FIXA: SELEÇÃO DE PRESET EXISTENTE ==========
        frame_selecao_preset = ctk.CTkFrame(self.aba_presets)
        frame_selecao_preset.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        frame_selecao_preset.grid_columnconfigure(1, weight=1)
        
        label_selecionar = ctk.CTkLabel(
            frame_selecao_preset,
            text="Carregar Preset Existente:",
            font=("Arial", 12, "bold"),
            text_color="cyan"
        )
        label_selecionar.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.combo_carregar_preset = ctk.CTkComboBox(
            frame_selecao_preset,
            values=self._obter_nomes_presets(),
            state="readonly",
            font=("Arial", 11)
        )
        self.combo_carregar_preset.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.combo_carregar_preset.set("Selecione um preset...")
        self.combo_carregar_preset.configure(command=self._carregar_preset_selecionado)
        
        # ========== SEÇÃO SCROLLÁVEL: EDIÇÃO ==========
        scroll_frame = ctk.CTkScrollableFrame(self.aba_presets)
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=10)
        scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Label de seção dentro do scroll
        label_edicao = ctk.CTkLabel(
            scroll_frame,
            text="Configurações do Preset",
            font=("Arial", 13, "bold")
        )
        label_edicao.pack(anchor="w", padx=15, pady=(10, 10))
        
        # Frame para nome do preset
        frame_nome = ctk.CTkFrame(scroll_frame)
        frame_nome.pack(fill="x", padx=15, pady=5)
        frame_nome.grid_columnconfigure(1, weight=1)
        
        label_nome = ctk.CTkLabel(frame_nome, text="Nome do Preset:", font=("Arial", 12, "bold"))
        label_nome.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.entry_nome = ctk.CTkEntry(frame_nome, placeholder_text="Ex: Farm_Rápido", font=("Arial", 11))
        self.entry_nome.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # Frame para modo e iterações
        frame_config = ctk.CTkFrame(scroll_frame)
        frame_config.pack(fill="x", padx=15, pady=5)
        frame_config.grid_columnconfigure((1, 3), weight=1)
        
        label_modo = ctk.CTkLabel(frame_config, text="Modo:", font=("Arial", 11, "bold"))
        label_modo.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.combo_modo = ctk.CTkComboBox(
            frame_config,
            values=["1 - Perder", "2 - Ganhar", "3 - Híbrido", "4 - Dragão", "5 - Goblin"],
            state="readonly",
            font=("Arial", 11)
        )
        self.combo_modo.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.combo_modo.set("5 - Goblin")
        
        label_iter = ctk.CTkLabel(frame_config, text="Iterações:", font=("Arial", 11, "bold"))
        label_iter.grid(row=0, column=2, sticky="w", padx=5, pady=5)
        
        self.entry_iter = ctk.CTkEntry(frame_config, placeholder_text="10", width=80, font=("Arial", 11))
        self.entry_iter.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.entry_iter.insert(0, "10")
        
        # Frame para tropas
        frame_tropas = ctk.CTkFrame(scroll_frame)
        frame_tropas.pack(fill="x", padx=15, pady=5)
        frame_tropas.grid_columnconfigure((1, 3), weight=1)
        
        label_tropas_qtd = ctk.CTkLabel(frame_tropas, text="Tropas:", font=("Arial", 11, "bold"))
        label_tropas_qtd.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        self.entry_tropas = ctk.CTkEntry(frame_tropas, placeholder_text="50", width=80, font=("Arial", 11))
        self.entry_tropas.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.entry_tropas.insert(0, "50")
        
        label_pocoes = ctk.CTkLabel(frame_tropas, text="Poções:", font=("Arial", 11, "bold"))
        label_pocoes.grid(row=0, column=2, sticky="w", padx=5, pady=5)
        
        self.entry_pocoes = ctk.CTkEntry(frame_tropas, placeholder_text="5", width=80, font=("Arial", 11))
        self.entry_pocoes.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.entry_pocoes.insert(0, "5")
        
        # Frame para heróis
        frame_herois = ctk.CTkFrame(scroll_frame)
        frame_herois.pack(fill="x", padx=15, pady=5)
        
        label_herois = ctk.CTkLabel(frame_herois, text="Heróis:", font=("Arial", 11, "bold"))
        label_herois.pack(anchor="w", padx=5, pady=5)
        
        self.check_rei = ctk.CTkCheckBox(frame_herois, text="Rei Bárbaro")
        self.check_rei.pack(anchor="w", padx=20, pady=2)
        self.check_rei.select()
        
        self.check_rainha = ctk.CTkCheckBox(frame_herois, text="Rainha Arqueira")
        self.check_rainha.pack(anchor="w", padx=20, pady=2)
        
        self.check_guardiao = ctk.CTkCheckBox(frame_herois, text="Guardião")
        self.check_guardiao.pack(anchor="w", padx=20, pady=2)
        
        self.check_campea = ctk.CTkCheckBox(frame_herois, text="Campeã")
        self.check_campea.pack(anchor="w", padx=20, pady=2)
        
        # Frame para máquinas de cerco e castelo
        frame_extra = ctk.CTkFrame(scroll_frame)
        frame_extra.pack(fill="x", padx=15, pady=5)
        
        self.check_siege = ctk.CTkCheckBox(frame_extra, text="Máquina de Cerco")
        self.check_siege.pack(anchor="w", padx=5, pady=2)
        
        self.check_castelo = ctk.CTkCheckBox(frame_extra, text="Abastecer Castelo")
        self.check_castelo.pack(anchor="w", padx=5, pady=2)
        self.check_castelo.select()
        
        # ========== SEÇÃO FIXA: BOTÕES ==========
        frame_botoes_presets = ctk.CTkFrame(self.aba_presets)
        frame_botoes_presets.grid(row=2, column=0, sticky="ew", padx=15, pady=10)
        frame_botoes_presets.grid_columnconfigure((0, 1, 2), weight=1)
        
        btn_salvar = ctk.CTkButton(
            frame_botoes_presets,
            text="💾 Salvar Preset",
            command=self._salvar_preset,
            font=("Arial", 12, "bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        btn_salvar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        btn_deletar = ctk.CTkButton(
            frame_botoes_presets,
            text="🗑️ Deletar",
            command=self._deletar_preset,
            font=("Arial", 12, "bold"),
            fg_color="red",
            hover_color="darkred"
        )
        btn_deletar.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        btn_limpar = ctk.CTkButton(
            frame_botoes_presets,
            text="🔄 Limpar",
            command=self._limpar_formulario,
            font=("Arial", 12, "bold"),
            fg_color="gray",
            hover_color="darkgray"
        )
        btn_limpar.grid(row=0, column=2, sticky="ew", padx=5, pady=5)
    
    
    def _carregar_preset_selecionado(self, preset_nome):
        """Carrega os dados de um preset selecionado para o formulário."""
        if preset_nome == "Selecione um preset..." or not preset_nome:
            return
        
        presets = carregar_presets()
        
        if preset_nome not in presets:
            return
        
        config = presets[preset_nome]
        army = config.get('army', {})
        
        # Preencher campos do formulário
        self.entry_nome.delete(0, "end")
        self.entry_nome.insert(0, preset_nome)
        
        modo = config.get('modo', 5)
        modo_str = {1: "1 - Perder", 2: "2 - Ganhar", 3: "3 - Híbrido", 4: "4 - Dragão", 5: "5 - Goblin"}
        self.combo_modo.set(modo_str.get(modo, "5 - Goblin"))
        
        self.entry_iter.delete(0, "end")
        self.entry_iter.insert(0, str(config.get('iteracoes', 10)))
        
        self.entry_tropas.delete(0, "end")
        self.entry_tropas.insert(0, str(army.get('troops', {}).get('quantidade', 50)))
        
        self.entry_pocoes.delete(0, "end")
        self.entry_pocoes.insert(0, str(army.get('pocao', {}).get('quantidade', 5)))
        
        # Checkboxes de heróis
        if army.get('rei', {}).get('ativo'):
            self.check_rei.select()
        else:
            self.check_rei.deselect()
        
        if army.get('rainha', {}).get('ativo'):
            self.check_rainha.select()
        else:
            self.check_rainha.deselect()
        
        if army.get('guardiao', {}).get('ativo'):
            self.check_guardiao.select()
        else:
            self.check_guardiao.deselect()
        
        if army.get('campea', {}).get('ativo'):
            self.check_campea.select()
        else:
            self.check_campea.deselect()
        
        if army.get('siege_machine', {}).get('ativo'):
            self.check_siege.select()
        else:
            self.check_siege.deselect()
        
        if config.get('castelo'):
            self.check_castelo.select()
        else:
            self.check_castelo.deselect()
        
        self.label_status_valor.configure(text=f"Preset '{preset_nome}' carregado", text_color="cyan")
    
    
    def _salvar_preset(self):
        """Salva o preset no arquivo JSON."""
        nome = self.entry_nome.get().strip()
        
        if not nome:
            self.label_status_valor.configure(text="Erro: Digite um nome para o preset", text_color="red")
            return
        
        try:
            modo = int(self.combo_modo.get().split()[0])
            iteracoes = int(self.entry_iter.get())
            tropas_qtd = int(self.entry_tropas.get())
            pocoes_qtd = int(self.entry_pocoes.get())
        except ValueError:
            self.label_status_valor.configure(text="Erro: Valores numéricos inválidos", text_color="red")
            return
        
        # Montar configuração
        config = {
            "modo": modo,
            "iteracoes": iteracoes,
            "espera_carrinho": 5,
            "castelo": 1 if self.check_castelo.get() else 0,
            "army": {
                "troops": {"quantidade": tropas_qtd, "sel": 0},
                "rei": {"ativo": 1 if self.check_rei.get() else 0, "sel": 0},
                "rainha": {"ativo": 1 if self.check_rainha.get() else 0, "sel": 0},
                "guardiao": {"ativo": 1 if self.check_guardiao.get() else 0, "sel": 0},
                "campea": {"ativo": 1 if self.check_campea.get() else 0, "sel": 0},
                "pocao": {"quantidade": pocoes_qtd, "sel": 0},
                "siege_machine": {"ativo": 1 if self.check_siege.get() else 0, "sel": 0}
            }
        }
        
        # Carregar presets existentes
        presets = carregar_presets()
        eh_novo = nome not in presets
        presets[nome] = config
        
        # Salvar
        salvar_presets(presets)
        
        # Atualizar combos com a nova lista
        nomes = list(presets.keys())
        self.combo_carregar_preset.configure(values=nomes)
        self.combo_presets.configure(values=nomes)
        
        mensagem = f"✓ Preset '{nome}' {'criado' if eh_novo else 'atualizado'} com sucesso"
        self.label_status_valor.configure(text=mensagem, text_color="green")
        
        self._limpar_formulario()
    
    
    def _deletar_preset(self):
        """Deleta o preset atualmente no formulário."""
        nome = self.entry_nome.get().strip()
        
        if not nome:
            self.label_status_valor.configure(text="Erro: Digite o nome do preset a deletar", text_color="red")
            return
        
        presets = carregar_presets()
        
        if nome not in presets:
            self.label_status_valor.configure(text=f"Erro: Preset '{nome}' não encontrado", text_color="red")
            return
        
        del presets[nome]
        salvar_presets(presets)
        
        # Atualizar combobox de seleção
        nomes = list(presets.keys())
        self.combo_carregar_preset.configure(values=nomes)
        self.combo_carregar_preset.set("Selecione um preset...")
        
        # Atualizar combo de presets da aba de execução
        self.combo_presets.configure(values=nomes)
        self.combo_presets.set("Selecione um preset")
        
        self.label_status_valor.configure(text=f"✓ Preset '{nome}' deletado com sucesso", text_color="green")
        self._limpar_formulario()
    
    
    def _limpar_formulario(self):
        """Limpa o formulário de presets."""
        self.combo_carregar_preset.set("Selecione um preset...")
        self.entry_nome.delete(0, "end")
        self.combo_modo.set("5 - Goblin")
        self.entry_iter.delete(0, "end")
        self.entry_iter.insert(0, "10")
        self.entry_tropas.delete(0, "end")
        self.entry_tropas.insert(0, "50")
        self.entry_pocoes.delete(0, "end")
        self.entry_pocoes.insert(0, "5")
        self.check_rei.select()
        self.check_rainha.deselect()
        self.check_guardiao.deselect()
        self.check_campea.deselect()
        self.check_siege.deselect()
        self.check_castelo.select()


def main():
    """Inicializa e executa a GUI."""
    app = COCBotGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
