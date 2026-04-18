# COC Bot - Automação de Ataques em Clash of Clans

Bot inteligente para automação de ataques em Clash of Clans com interface gráfica moderna, sistema de presets e execução assíncrona.

## 🚀 Instalação

### Pré-requisitos
- Python 3.12 ou superior (conforme `pyproject.toml`)
- [uv](https://docs.astral.sh/uv/) (recomendado) ou pip

### Passos de Instalação

1. **Clonar ou extrair o repositório:**
   ```bash
   cd COC_script
   ```

2. **Instalar dependências com uv (recomendado):**
   ```bash
   uv sync
   ```

   Com ambiente virtual clássico e pip, após `python -m venv venv` e ativar o venv:
   ```bash
   pip install -e .
   ```

## 📱 Como Usar

### Iniciar a Aplicação

```bash
uv run python gui.py
```

A interface gráfica será aberta com duas abas principais.

### Aba 1: Executar Ataque

1. **Selecionar Preset:** Use o menu suspenso para selecionar um tipo de ataque pré-configurado
2. **Ver Informações:** Visualize os detalhes completos do preset (modo, tropas, heróis, etc.)
3. **Iniciar:** Clique no botão `▶ Iniciar Ataque` para começar a automação
4. **Parar:** Use o botão `⏹ Parar` para interromper a execução (se necessário)
5. **Recarregar:** Clique em `🔄 Recarregar Presets` para atualizar a lista de presets

### Aba 2: Criar/Editar Presets

1. **Nome do Preset:** Escolha um nome descritivo (ex: `Farm_Rapido`, `Ataque_Dragao_Full`)
2. **Modo:** Selecione entre 5 opções:
   - **1 - Perder:** Inicia e perde imediatamente (farm de ouro/elixir)
   - **2 - Ganhar:** Derrota inimigo com 1 ou 2 vilas do construtor
   - **3 - Híbrido:** Combina vitória e derrota na mesma rodada
   - **4 - Dragão:** Ataque especializado com dragões na base principal
   - **5 - Goblin:** Ataque especializado com goblins na base principal

3. **Configurar Tropas:**
   - Quantidade de tropas regulares
   - Quantidade de poções

4. **Selecionar Heróis:** Marque quais heróis deseja usar:
   - ✓ Rei Bárbaro
   - ✓ Rainha Arqueira
   - ✓ Guardião
   - ✓ Campeã

5. **Opções Extras:**
   - Máquina de Cerco
   - Abastecer Castelo

6. **Salvar:** Clique em `💾 Salvar Preset` para guardar a configuração
7. **Deletar:** Use `🗑️ Deletar` para remover um preset existente
8. **Limpar:** Clique em `🔄 Limpar` para resetar o formulário

## 📋 Estrutura de Presets

Os presets são salvos em formato JSON no arquivo `presets.json`. Exemplo:

```json
{
  "Farm_Goblin_Rapido": {
    "modo": 5,
    "iteracoes": 10,
    "espera_carrinho": 5,
    "castelo": 1,
    "army": {
      "troops": {"quantidade": 50, "sel": 0},
      "rei": {"ativo": 1, "sel": 0},
      "rainha": {"ativo": 0, "sel": 0},
      "guardiao": {"ativo": 0, "sel": 0},
      "campea": {"ativo": 0, "sel": 0},
      "pocao": {"quantidade": 5, "sel": 0},
      "siege_machine": {"ativo": 0, "sel": 0}
    }
  }
}
```

## 🎮 Modos de Ataque

### Modo 1: Perder
- Inicia uma batalha e se rende imediatamente
- Ideal para farmar ouro e elixir sem risco
- Rápido e eficiente

### Modo 2: Ganhar
- Derrota o inimigo completamente
- Oferece melhor recompensa que perder
- Pode usar 1 ou 2 vilas

### Modo 3: Híbrido
- Combina ganho e perda
- Maximiza os resultados em farmings contínuos
- Flexível e estratégico

### Modo 4: Dragão
- Ataque especializado com dragões
- Excelente para bases principais fortes
- Suporta todos os 4 heróis
- Requer máquina de cerco para maior eficiência

### Modo 5: Goblin
- Ataque especializado com goblins
- Ótimo para farms de ouro e elixir
- Rápido e de baixo custo militar
- Ideal para repetições contínuas

## ⚙️ Características Técnicas

### Execução Assíncrona
- O bot executa em thread separada
- A interface não congela durante os ataques
- Você pode parar a execução a qualquer momento

### Sistema de Presets
- Salve suas configurações favoritas
- Reutilize presets frequentemente
- Edite e delete presets conforme necessário

### Interface Moderna
- Design escuro/claro nativo
- Responsivo e intuitivo
- MenusTabs para organização clara

## 📁 Estrutura do Projeto

```
COC_script/
├── main.py                 # Lógica principal do bot
├── gui.py                  # Interface gráfica
├── presets.json            # Banco de dados de presets
├── pyproject.toml          # Metadados e dependências do projeto
├── uv.lock                 # Lockfile do uv (reprodutível)
├── attacks/
│   ├── attack_utils.py     # Funções auxiliares
│   ├── builder_base.py     # Ataques na base do construtor
│   └── home_base.py        # Ataques na base principal
├── utils/
│   ├── mouse_actions.py    # Controle de mouse
│   ├── image_recognition.py # Reconhecimento de imagens
│   └── stop_handler.py     # Tratamento de parada
└── config/
    └── constants.py        # Constantes globais
```

## 🛠️ Troubleshooting

### Erro: "Can't connect to display ":0""
Este erro significa que não há servidor X11 disponível. **Mas não se preocupe!** A GUI foi otimizada com lazy loading.

**Solução 1: Se você tem um display X11 disponível**
```bash
DISPLAY=:0 python gui.py
```

**Solução 2: Se não tem display (servidor/SSH sem X11)**
- Você ainda pode usar a GUI para criar presets (isso funciona sem X11!)
- Para executar o bot com ataques, use Xvfb:
```bash
sudo apt install xvfb
xvfb-run -a python gui.py
```

Veja [RESOLUCAO_X11.md](RESOLUCAO_X11.md) para mais detalhes técnicos.

### "CustomTkinter não está instalado"
```bash
uv sync
```
ou, com pip: `pip install -e .`

### Interface congelada
- Isso não deve acontecer com threading. Se acontecer, a execução pode estar em deadlock.
- Tente parar e reiniciar a aplicação.

### Preset não aparece na lista
- Certifique-se de que o arquivo `presets.json` existe no diretório raiz
- Clique em `🔄 Recarregar Presets` para atualizar

### Erro ao salvar preset
- Verifique se todos os campos têm valores válidos (números inteiros onde esperado)
- Certifique-se de que o nome do preset não contém caracteres especiais

## 📝 Notas Importantes

- **A aplicação controla o mouse e teclado.** Certifique-se de que o Clash of Clans está aberto e visível.
- **Não interrompa o programa com força** enquanto ataques estão em execução. Use o botão `⏹ Parar` da GUI.
- **Presets são salvos em tempo real** no arquivo JSON.
- **Backups são recomendados:** Copie o arquivo `presets.json` regularmente.

## 🔄 Melhorias Futuras

- [ ] Suporte a logs detalhados de execução
- [ ] Histórico de ataques e estatísticas
- [ ] Agendamento automático de ataques
- [ ] Integração com OCR para melhor reconhecimento
- [ ] Perfis customizáveis por vilas

## 📄 Licença

Este projeto é fornecido como está, apenas para fins educacionais.