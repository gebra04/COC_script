# Handoff — automação de ataque + upgrade (Clash of Clans / Waydroid)

> Escrito em 2026-08-20 no fim de uma sessão longa, pra um agente de sessão
> nova continuar. Leia inteiro antes de mexer em qualquer coisa.

## Objetivo final

**Sistema rodando sozinho: ataca em loop e, quando os depósitos enchem,
gasta o recurso em upgrade (muro primeiro).** Nada além disso é escopo.
O usuário sai e volta de manhã esperando isso funcionando — ele autorizou
gastar todos os créditos disponíveis e "fazer o que for necessário e
documentar".

## Regras invioláveis

1. **NUNCA gastar gemas.** A conta tem 352. Botões perigosos: "Boost
   ARMY"/"Boost Heroes" (topo da tela de exército), qualquer "Finish
   Now"/"Upgrade" com ícone verde de gema, "Builder's Apprentice"
   (custa 750 gemas — quase foi clicado por acidente nesta sessão).
   Confira a contagem de gemas antes/depois de sequências novas.
2. **A conta logada ("LIL Geb", nível 89) é descartável** — o usuário
   disse explicitamente que pode testar filtros e métodos à vontade nela.
   Perder batalhas não é problema. Gastar ouro/elixir não é problema.
3. **`mem_reader.py` só lê memória, nunca escreve.** É a arquitetura
   passiva (sem ptrace/injeção) escolhida em `pesquisa/06`. Não introduza
   escrita em `/proc/<pid>/mem`.
4. Ao explorar memória, use leituras pontuais (`--scan`, `--dump`).
   **Nunca** `--watch`/`--live` em loop apertado sem timeout.

## Ambiente

- Repo: `/home/gebra/COC_script` (git, branch `main`)
- Ferramenta externa (fora do repo): `~/.local/share/coc-digital-twin/mem_reader.py`
  - Roda como root via regra de sudoers **escopada só a esse caminho**:
    `sudo -n python3 /home/gebra/.local/share/coc-digital-twin/mem_reader.py <args>`
  - `sudo -n` para qualquer outro comando **falha** (pede senha).
- Fedora, sessão **Wayland**. Waydroid rodando, device ADB em
  `192.168.240.112:5555`, resolução `1366x739`, densidade `213`.
- Python: `uv run python3` dentro de `/home/gebra/COC_script` (venv com
  pytesseract, numpy, PIL, torch, gymnasium). `tesseract` 5.5.3 instalado
  no sistema. **`cv2` NÃO está instalado.**
- Como saber se o jogo está vivo:
  `adb shell dumpsys activity activities | grep topResumedActivity`
  (`pidof` é **não confiável**, dá falso positivo).
- Como abrir o jogo: `adb shell am start -n com.supercell.clashofclans/com.supercell.titan.GameApp`
  (`adb shell monkey ...` **não funciona** neste setup, falha em silêncio).
- O jogo **desconecta por inatividade** com frequência ("Anyone there?" →
  botão "Reload game" em ~(347,405)). Trate isso no loop: detectar e
  reconectar sozinho é provavelmente necessário pra rodar a noite toda.

---

## BLOQUEADOR PRINCIPAL: zoom out

**Os ataques hardcoded (`attacks/home_base.py`) só funcionam com a tela no
zoom máximo pra fora.** Todas as coordenadas de deploy
(`posicao_dragao_*`, `CANTOS`, `RETAS`) assumem isso. Sem resolver zoom,
não adianta calibrar coordenada nenhuma — elas mudam de lugar.

Isso não foi resolvido. Pistas levantadas, em ordem de custo/risco:

1. **`adb shell wm density <n>`** (hoje 213). Densidade menor = UI menor =
   mais mundo visível. É o caminho mais barato de testar
   (`adb shell wm density 160`, `wm density reset` pra voltar). **Porém:**
   muda o layout inteiro do Android → todas as coordenadas, inclusive as
   do `utils/hud_ocr.py` e `utils/upgrade_picker.py`, precisam ser
   recalibradas na densidade final escolhida. Decida a densidade **antes**
   de calibrar qualquer coisa.
2. **`adb shell input roll <dx> <dy>`** (eventos de trackball) — pode
   mapear pra scroll/zoom. Barato de testar, não testado.
3. **Pinch multitouch.** `adb shell input` não suporta. Precisaria de
   `sendevent` ou de escrever direto no FIFO do Waydroid (ver abaixo).
4. **FIFO de input do Waydroid** — descoberta desta sessão: o Waydroid não
   usa evdev normal, usa named pipes em `/dev/input/wl_pointer_events`,
   `wl_keyboard_events`, `wl_tablet_events`. **Confirmado que o usuário
   `shell` do ADB tem permissão de escrita neles.** Um `adb shell`
   persistente escrevendo `struct input_event` binário permitiria pinch
   real e derrubaria a latência a ~zero. Custo: engenharia reversa do
   formato exato; evento malformado pode travar o input (recuperável com
   restart de sessão do Waydroid).
5. **Ler o zoom da memória pra verificar.** `mem_reader.py` tem
   `--cam-hunt` / `--cam-probe` que acharam estado de câmera em julho, e
   existem `utils/cam_calib*.json`. Útil pra *confirmar* que o zoom chegou
   no máximo, de forma passiva. Não use pra escrever.

---

## O que já existe e funciona

### Leitura de estado (memória) — `mem_reader.py`

`KNOWN_CLASSES` re-derivado pra build **18.400.22** (se o jogo atualizar,
tudo isso invalida e precisa ser re-derivado com `--scan` + `vtable_scan.py`):

```
0x01690ba0 Building | 0x01695030 Wall | 0x01692de0 Obstacle
0x016939e0 Trap     | 0x0169fc20 BattleReport
```

- **`--battle-report`** ✅ validado em 2 ataques reais. Singleton, achado
  por scan de vtable. Campos (offset no objeto): `+0x168` % destruição,
  `+0x170/174/178` saque ouro/elixir/escuro, `+0x17c` tokens, `+0x180`
  **estrelas** (confirmado: 71%→1★, 100%→3★), `+0x190/194/198` bônus de
  liga. **Só existe enquanto a tela de resumo pós-ataque está aberta** —
  some ao sair. Não dá pra ler % ao vivo por aqui.
- **`--wallet [addr_cache] <gold> <elixir> <dark>`** ✅ Lê gems/gold/
  elixir/dark. O objeto **realoca** (mudou 3x numa sessão sem reiniciar o
  jogo) → não há endereço estável. Estratégia: tenta cache (~0.06s), senão
  rebusca numa banda de heap conhecida (~0.15s), senão heap inteiro. A
  semente vem do OCR do HUD e **tolera OCR errado** em até 2 dos 3 valores.
- Não foi achado: contador de construtores, timer de construção, % ao vivo.
  Quatro tentativas falharam (cadeia de ponteiro, campo na cabana,
  timestamp no Building, timestamp no heap). Construtores hoje vêm de OCR.

### Módulos novos no repo (todos criados nesta sessão)

| arquivo | o que faz | estado |
|---|---|---|
| `utils/adb_io.py` | screenshot/tap/swipe via adb | ✅ ok |
| `utils/input_backend.py` | backend ADB ou PyAutoGUI, via `COC_INPUT_BACKEND` | ✅ ok |
| `utils/coord_map.py` | afim host→device + overrides; `--verificar` desenha os pontos num screenshot | ⚠️ afim aproximada |
| `utils/hud_ocr.py` | construtores livres, recursos do HUD | ⚠️ perde dígito às vezes |
| `utils/upgrade_picker.py` | abre popup de construtor, rola procurando muro, senão 1ª sugestão (nunca herói) | ✅ validado ao vivo |
| `utils/live_ui_actions.py` | botões de ataque + Upgrade/Confirm por OCR | ⚠️ ver limitação |
| `utils/mem_bridge.py` | parseia saída do mem_reader | ✅ ok |
| `utils/session_loop.py` | junta tudo: lê estado → decide → age | ⚠️ testado só em dry-run |
| `utils/image_recognition.py` | template match numpy (rota ADB) | ⚠️ não testado |

`main.py` aceita `config['auto_upgrade']` e `config['input_backend']`;
a GUI tem checkbox + combo pra ambos.

**Nada disso quebrou a API antiga**: `mouse_actions.clicar/arrastar/
clicar_coordenadas` mantêm a assinatura, então `attacks/*.py` não mudou de
interface. O modo `COC_INPUT_BACKEND=pyautogui` restaura o comportamento
original (coordenadas passam sem conversão) pra Windows.

### Coordenadas verificadas ao vivo (espaço do device, densidade 213)

```
atacar       (85, 655)    Attack! na vila            ✅ testado agora
encontrar    (223, 548)   Find a Match               ✅ testado agora
attack_army  (1200, 667)  Attack! verde (exército)   ✅ testado agora
voltar       (683, 632)   Return Home                ✅ conferido no --verificar
badge construtores (700, 42)                         ✅ usado o tempo todo
```

`attack_army` **não existia** em `config/constants.BOTOES` — era um bug
antigo: `attack_utils.procurar_partida()` clicava num nome inexistente e
falhava em silêncio. Agora existe como override em `coord_map.py`.

---

## Problemas conhecidos, em ordem de importância

1. **Zoom** (acima). Bloqueia tudo.
2. **~35 coordenadas não verificadas** — `selecionar_tropa_1..9`,
   `posicao_dragao_*`, `pocao_de_furia_*`, `render_se`, `ok`, `CANTOS`,
   `RETAS`. Vêm da transformação afim
   (`x≈1.483x+30.3`, `y≈1.165y+106.1`), que é **aproximada** porque a
   janela original (~900x500) tinha aspecto diferente do device
   (1366x739) e o Android re-diagrama, não só escala. Use
   `uv run python3 -m utils.coord_map --verificar` **dentro da tela certa**
   (as de batalha só dá pra conferir em batalha) e corrija ponto a ponto em
   `OVERRIDES_DEVICE` ou no JSON `~/.local/share/coc-digital-twin/coord_map.json`.
   Há uma janela de ~30s de reconhecimento no início de cada batalha, antes
   do timer começar — é o momento ideal pra rodar `--verificar`.
3. **OCR perde dígito** em números do HUD quando dois "1" ficam colados
   (ex.: "115465"→"15465"). Reproduzível em todo psm/escala testado nessa
   fonte. Tentativa de segmentar por coluna de pixel piorou (dígitos dentro
   do mesmo grupo colam também) e foi revertida. Mitigado no lado do
   `mem_reader --wallet`, que tolera semente errada. **Não afeta** o
   contador de construtores ("N/M", que lê certo).
4. **`live_ui_actions.confirm_selected_upgrade`** — quando o item tem duas
   formas de pagamento (muro em nível alto mostra "Upgrade" em ouro E em
   elixir negro lado a lado), pega o primeiro que o tesseract listar, sem
   desambiguar moeda. Verificado ao vivo pegando o de elixir negro por
   acaso. Resolver antes de deixar rodando sozinho.
5. **`upgrade_picker.pick_upgrade(dry_run=True)` não fecha o popup** —
   duas chamadas seguidas em dry-run fazem a segunda ler lixo.
6. **Estado de UI entre iterações não é garantido limpo.** O
   `session_loop` assume vila principal sem nada selecionado. Durante esta
   sessão, toques imprecisos levaram a: tela de compra, Aldeia do
   Construtor, diálogo de sair do jogo, decoração selecionada. Precisa
   detectar e se recuperar sozinho pra rodar a noite toda.
7. **Limiar de depósito cheio é número fixo** (`DEFAULT_THRESHOLDS` em
   `session_loop.py`), não a capacidade real do armazém — não achamos
   leitura confiável da capacidade. Ajuste por conta.
8. `coletar_carrinho()` provavelmente nunca funcionou no Linux: usava
   `pyautogui.locateCenterOnScreen(confidence=...)`, que exige OpenCV, e
   `cv2` não está instalado. Reescrito com numpy, **não testado**.

---

## Caminho sugerido

1. Resolver zoom. Decidir a configuração final (densidade? pinch?) e
   **congelá-la** — tudo depende disso.
2. Com o zoom final travado, recalibrar as coordenadas de batalha usando
   `--verificar` durante os 30s de reconhecimento. Um ataque de teste por
   rodada de correção.
3. Rodar `ataque_rapido` (o mais simples, e ele já se autocorrige no tempo)
   ponta a ponta. Depois `ataque_dragao` (o exército atual é 13 dragões +
   5 poções de fúria + 3 heróis, então o modo 4 é o natural).
4. Ligar `auto_upgrade` e deixar rodando algumas iterações supervisionadas.
5. Tratar desconexão por inatividade e recuperação de estado de UI.
6. Só então deixar rodando sozinho.

**Comece por um `git status`** — há bastante coisa não commitada desta
sessão. E não confie em nenhum "✅" acima sem re-verificar: a maioria foi
testada uma vez, em uma tela, numa densidade.
