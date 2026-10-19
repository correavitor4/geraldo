# Geraldo - Assistente de Voz Local Desktop

Assistente de voz desktop inteligente, rápido, modular e 100% local (sem dependência de nuvem), com suporte a controle por voz (*wake word* "Geraldo"), interface gráfica moderna (Desktop GUI via Tauri 2.0 / Webview), interface rica de terminal (TUI via Textual) e barramento IPC assíncrono em tempo real.

---

## 📑 Sumário

1. [Visão Geral e Arquitetura](#1-visão-geral-e-arquitetura)
2. [Documentação e Diagramas Técnicos (docs/)](#2-documentação-e-diagramas-técnicos-docs)
3. [Requisitos de Sistema e Hardware](#3-requisitos-de-sistema-e-hardware)
4. [Como Rodar o Ollama (Local ou Docker)](#4-como-rodar-o-ollama-local-ou-docker)
5. [Como Configurar o Container do Ollama no Geraldo](#5-como-configurar-o-container-do-ollama-no-geraldo)
6. [Instalação e Como Rodar o Geraldo](#6-instalação-e-como-rodar-o-geraldo)
   - [Instalação das Dependências](#61-instalação-das-dependências)
   - [Execução do Daemon de Voz (Backend)](#62-execução-do-daemon-de-voz-backend)
   - [Execução da Interface de Terminal (TUI)](#63-execução-da-interface-de-terminal-tui)
   - [Execução da Interface Desktop (GUI)](#64-execução-da-interface-desktop-gui)
   - [Serviço em Segundo Plano (Systemd no Linux)](#65-serviço-em-segundo-plano-systemd-no-linux)
7. [Atalhos e Comandos Úteis](#7-atalhos-e-comandos-úteis)
8. [Estrutura do Repositório](#8-estrutura-do-repositório)

---

## 1. Visão Geral e Arquitetura

O **Geraldo** opera através de um pipeline local otimizado para baixíssima latência:

```
[Microfone] ➔ [Silero VAD] ➔ [Faster-Whisper Tiny (Wake Word 'Geraldo')]
                                    │
                                    ▼
[Gravação até Silêncio] ➔ [Faster-Whisper Small (STT)]
                                    │
                                    ▼
                     [Classificador NLU Scikit-Learn]
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
[Comandos Determinísticos]                         [Conversação Geral]
(Timers, Alarmes, Pomodoro,                        (Ollama: qwen2.5:3b)
 Clima, Agenda, Mídia, Janelas)                              │
           │                                                 │
           └────────────────────────┬────────────────────────┘
                                    ▼
                     [Fonetização & Limpeza de Texto]
                                    │
                                    ▼
                     [Piper TTS Neural (voz_faber.onnx)]
                                    │
                                    ▼
                   [AudioPlayer / PipeWire / PulseAudio]
```

- **Zero Cloud / Privacidade Total:** Todo o áudio e texto são processados no seu computador.
- **Roteamento Híbrido:** Comandos do dia a dia (timers, alarmes, relógio, clima, YouTube Music) não chamam LLM, executando em menos de **1ms**.
- **Perguntas Abertas:** Consultas e bate-papo são encaminhados para o container ou instância do **Ollama** (`qwen2.5:3b` por padrão).

---

## 2. Documentação e Diagramas Técnicos (docs/)

Os diagramas de arquitetura e o roteiro detalhado do projeto estão organizados na pasta [`docs/`](file:///home/vitor/projects/geraldo/docs/):

- [`docs/arquitetura_atual_geraldo.excalidraw`](file:///home/vitor/projects/geraldo/docs/arquitetura_atual_geraldo.excalidraw): Diagrama visual do estado e fluxo atual do assistente.
- [`docs/arquitetura_geraldo.excalidraw`](file:///home/vitor/projects/geraldo/docs/arquitetura_geraldo.excalidraw): Especificação arquitetural dos subsistemas (áudio, NLU, IPC, ferramentas).
- [`docs/roteiro.excalidraw`](file:///home/vitor/projects/geraldo/docs/roteiro.excalidraw): Roteiro de evolução, sidecar packaging, empacotamento desktop e roadmap multiplataforma.

> **Dica:** Você pode abrir e editar os arquivos `.excalidraw` diretamente no VS Code / IDE com a extensão oficial do Excalidraw ou pelo site [excalidraw.com](https://excalidraw.com).

---

## 3. Requisitos de Sistema e Hardware

| Componente | Ferramenta / Modelo | Uso de Hardware | Precisa de GPU? |
| :--- | :--- | :--- | :--- |
| **Wake Word & STT** | `faster-whisper` (`tiny` + `small`) | CPU com quantização `int8` | **Não** (CPU puro) |
| **NLU / Roteamento** | Scikit-Learn (TF-IDF + Logistic Regression) | CPU (< 1ms) | **Não** (CPU puro) |
| **Síntese de Voz (TTS)** | Piper TTS (`voz_faber.onnx`) | ONNX Runtime otimizado para CPU | **Não** (CPU puro) |
| **Barramento IPC** | WebSocket assíncrono (Python `websockets`) | CPU / Memória leve (< 20MB) | **Não** |
| **LLM (Conversação)** | Ollama (`qwen2.5:3b`) | 3 bilhões de parâmetros quantizados | **Opcional** (Roda em CPU ou com aceleração CUDA/ROCm/Metal) |

---

## 4. Como Rodar o Ollama (Local ou Docker)

O Geraldo utiliza o **Ollama** para responder perguntas abertas e conversação geral. Você pode executá-lo diretamente no sistema operacional ou em um **container Docker**.

### Opção A: Rodando o Ollama via Docker (Recomendado para Containers)

Execute o container mapeando a porta padrão `11434` e persistindo os modelos em um volume:

```bash
# 1. Iniciar o container do Ollama (modo CPU)
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  --restart always \
  ollama/ollama

# Caso possua placa de vídeo NVIDIA com nvidia-container-toolkit instalado:
docker run -d \
  --name ollama \
  --gpus=all \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  --restart always \
  ollama/ollama
```

Depois de subir o container, baixe o modelo recomendado (`qwen2.5:3b`):

```bash
# 2. Baixar o modelo no container
docker exec -it ollama ollama pull qwen2.5:3b
```

### Opção B: Rodando o Ollama Nativo (sem Docker)

Se preferir instalar o Ollama nativamente no seu sistema operacional:

```bash
# Linux / macOS
curl -fsSL https://ollama.com/install.sh | sh

# Iniciar o serviço e baixar o modelo
ollama serve
ollama pull qwen2.5:3b
```

---

## 5. Como Configurar a IA do Geraldo (Ollama Local ou LLM Externa com API Key)

O Geraldo oferece liberdade total de escolha para o motor de conversação e raciocínio. O usuário pode alternar facilmente entre o **Ollama local/container** (privacidade absoluta e offline) e **Provedores Externos via API Key** (ultra velocidade e raciocínio avançado):

### 🌟 Provedores Suportados e Modelos Recomendados

| Provedor | Tipo | Base URL Padrão | Modelos Recomendados | Onde Obter Chave |
| :--- | :--- | :--- | :--- | :--- |
| **🦙 Ollama** | 100% Local / Container | `http://localhost:11434` | `qwen2.5:3b`, `llama3.2:3b`, `mistral:latest` | Não requer chave |
| **⚡ Groq** | Nuvem Ultra Rápida (LPU) | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant` | [console.groq.com/keys](https://console.groq.com/keys) |
| **🤖 OpenAI** | Nuvem Proprietária | `https://api.openai.com/v1` | `gpt-4o-mini`, `gpt-4o` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| **🌐 OpenRouter** | Agregador Multi-Modelo | `https://openrouter.ai/api/v1` | `meta-llama/llama-3.3-70b-instruct`, `deepseek/deepseek-chat` | [openrouter.ai/keys](https://openrouter.ai/keys) |
| **✨ Google Gemini** | Nuvem Google AI | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.0-flash`, `gemini-1.5-flash` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| **🔌 Custom** | Self-Hosted / Outro | `http://localhost:8000/v1` | Qualquer modelo compatível com OpenAI API | Definido pelo seu servidor |

---

### 🖥️ 1. Na Interface Desktop (GUI / Tauri)

1. Com a interface gráfica aberta, clique no botão **⚙️ Ollama / IA** no topo da barra de navegação.
2. No modal **Configurar IA & Modelo LLM**, escolha o provedor desejado nas abas:
   - **Ollama:** exibe o campo de Host/URL com botões de atalho (*Localhost*, *Docker Host*, *Container 'ollama'*, *Bridge 172.17.0.1*) e dropdown de modelos detectados no container.
   - **Groq, OpenAI, OpenRouter, Gemini ou Custom:** exibe o campo para inserir a **API Key** (com botão 👁️ para exibir/ocultar a chave com segurança), atalho para a página de geração de chaves do provedor e campo de endpoint base.
3. Escolha o modelo digitando ou clicando nos **chips de sugestão rápida** adaptados para cada provedor.
4. Clique em **🔍 Testar Conexão**:
   - O Geraldo testa a conectividade e a validade da API key em tempo real, exibindo feedback claro (*CONECTADO* ou o motivo da falha, como cota esgotada ou chave inválida).
5. Clique em **💾 Salvar Configurações**:
   - As credenciais e preferências são aplicadas instantaneamente no daemon ativo e salvas em disco de forma segura.

---

### 📟 2. Na Interface de Terminal Rica (TUI)

1. Com a TUI aberta (`python ui/tui.py`), pressione a tecla de atalho **`o`**.
2. O modal **`⚙️ Configurações de IA (Ollama / LLM Externa)`** será exibido sobre a tela.
3. Alterne o campo **`Provedor`** para o nome do provedor desejado (ex: `ollama`, `groq`, `openai`, `openrouter`, `gemini` ou `custom`).
4. Caso use um provedor externo, insira a **`API Key`** e o **`Host / URL do Endpoint`** se necessário.
5. Pressione **`[ 🔍 Testar ]`** para verificar se o serviço e credenciais estão válidos.
6. Pressione **`[ 💾 Salvar ]`** para aplicar imediatamente.

---

### ⚙️ 3. Via Variáveis de Ambiente ou Arquivo de Configuração

Você também pode configurar suas preferências através de variáveis de ambiente:

```bash
# Exemplo 1: Usando Groq (resposta instantânea para conversação por voz)
export LLM_PROVIDER="groq"
export LLM_API_KEY="gsk_suaChaveGroqAqui"
export LLM_MODEL="llama-3.3-70b-versatile"

# Exemplo 2: Usando Google Gemini via AI Studio
export LLM_PROVIDER="gemini"
export LLM_API_KEY="AIzaSySuaChaveGeminiAqui"
export LLM_MODEL="gemini-2.0-flash"

# Exemplo 3: Usando Ollama local ou em container Docker
export LLM_PROVIDER="ollama"
export OLLAMA_HOST="http://localhost:11434"
export LLM_MODEL="qwen2.5:3b"
```

As configurações salvas ficam gravadas de forma persistente no arquivo `settings.json`:
- **Linux:** `~/.config/geraldo/settings.json`
- **Windows:** `%APPDATA%\Geraldo\settings.json`
- **macOS:** `~/Library/Application Support/Geraldo/settings.json`

---

## 6. Instalação e Como Rodar o Geraldo

### 6.1. Instalação das Dependências

Clone o repositório e configure o ambiente virtual Python (recomendado Python 3.11 ou 3.12+):

```bash
# 1. Clonar repositório
git clone https://github.com/correavitor4/geraldo.git
cd geraldo

# 2. Criar e ativar o ambiente virtual
python3 -m venv venv
source venv/bin/activate  # No Windows: .\venv\Scripts\activate

# 3. Atualizar pip e instalar dependências
pip install --upgrade pip
pip install -r requirements.txt
```

> **Modelos de Voz:** Certifique-se de que o modelo Piper neural (`voz_faber.onnx` e `voz_faber.onnx.json`) esteja presente na raiz do projeto ou na pasta `models/`.

---

### 6.2. Execução do Daemon de Voz (Backend)

O daemon é o coração do assistente. Ele escuta a *wake word* no microfone, executa as ferramentas e hospeda o barramento IPC WebSocket local (`127.0.0.1:8765`):

```bash
# Execução direta pelo Python
python main.py

# Ou pelo script shell
./run.sh
```

Ao iniciar, você verá:
```
[Geraldo] Inicializando assistente...
[Geraldo] Treinando classificador NLU (Scikit-Learn)...
[Geraldo] Barramento IPC local escutando em ws://127.0.0.1:8765
[Geraldo] Dormindo... Diga 'Geraldo' para acordar.
```

---

### 6.3. Execução da Interface de Terminal (TUI nos 3 Sistemas Operacionais)

A TUI do Geraldo é multiplataforma e funciona nativamente no **Linux**, **macOS** e **Windows**.

#### 🚀 Comando Global após Instalação (Windows e macOS)
Nos instaladores do Windows e macOS, o comando `geraldo_tui` (e `geraldo-tui`) é **configurado automaticamente no PATH do seu sistema**. Você pode simplesmente abrir qualquer terminal e digitar:

```bash
# Funciona no Windows (PowerShell/CMD/Windows Terminal) e no macOS (Zsh/Bash/Terminal.app):
geraldo_tui
```

---

#### 💻 Modo de Desenvolvimento / Repositório:

##### 🐧 No Linux:
```bash
./bin/geraldo_tui
# ou:
./run_tui.sh
```

##### 🍏 No macOS:
```bash
./bin/geraldo_tui
# ou:
./run_tui.sh
```

##### 🪟 No Windows (Windows Terminal ou PowerShell):
```powershell
.\bin\geraldo_tui.cmd
# ou:
.\run_tui.bat
```

> **Dica Windows:** Recomendamos executar no **Windows Terminal** (já padrão no Windows 11 ou disponível na Microsoft Store) para melhor renderização de fontes e cores.

A TUI se conecta automaticamente ao barramento WebSocket local (`127.0.0.1:8765`) e oferece controle total:
- Histórico de mensagens com cores ricas.
- Painéis laterais de **Pomodoro**, **Timers ativos** e **Alarmes programados**.
- Caixa de digitação de texto para comandos silenciosos (ex: *"timer de 10 minutos"*, *"minha agenda de hoje"*).

---

### 6.4. Execução da Interface Desktop (GUI)

A interface gráfica do Geraldo pode ser executada de duas formas:

#### Modo A: Aplicativo Nativo de Desktop (Tauri 2.0 / Rust)

Com o binário compilado pelo Cargo / Tauri:

```bash
# Executando o binário de desenvolvimento
./src-tauri/target/debug/geraldo-desktop

# Ou executando via CLI do Tauri
npm run tauri dev
```

#### Modo B: Modo Webview / Navegador (Desenvolvimento Rápido)

Como a interface é construída em Vanilla HTML5/CSS/JavaScript sem necessidade de node_modules pesados, você pode rodá-la com qualquer servidor HTTP estático:

```bash
python -m http.server 3000 --directory desktop-ui
```
Em seguida, abra seu navegador em `http://localhost:3000`.

---

### 6.5. Serviço em Segundo Plano (Systemd no Linux)

Para iniciar o Geraldo automaticamente com a sua sessão do usuário no Linux:

```bash
# 1. Copiar arquivo de serviço para a pasta systemd do usuário
mkdir -p ~/.config/systemd/user
cp geraldo.service ~/.config/systemd/user/

# 2. Habilitar e iniciar
systemctl --user daemon-reload
systemctl --user enable --now geraldo.service

# 3. Verificar status e logs
systemctl --user status geraldo.service
journalctl --user -u geraldo.service -f
```

---

## 7. Atalhos e Comandos Úteis

### Atalhos na TUI (Terminal)
| Tecla | Ação |
| :---: | :--- |
| **`m`** | Ativar / Mutar Microfone |
| **`p`** | Iniciar / Pausar Pomodoro |
| **`c`** | Cancelar fala ou alarmes ativos |
| **`o`** | Abrir Configurações do Ollama / Container |
| **`t`** | Focar no campo de digitação de comando |
| **`Ctrl+L`** | Limpar histórico da tela |
| **`q`** | Sair da TUI |

### Exemplos de Comandos de Voz / Texto
- *"Que horas são?"* (Zero LLM, < 1ms)
- *"Timer de 5 minutos para o café"* (Zero LLM, cria timer)
- *"Alarme para às 7 da manhã"* (Zero LLM, agenda alarme)
- *"Inicie o pomodoro"* (Zero LLM, ciclo de foco)
- *"Como está o clima hoje?"* (Zero LLM, consulta previsão)
- *"Qual a minha agenda de hoje?"* (Zero LLM, consulta Google Calendar)
- *"Toque música lo-fi"* (Zero LLM, toca no YouTube Music)
- *"Fechar janela"* / *"Próximo workspace"* (Zero LLM, controle do Hyprland)
- *"Por que o céu é azul?"* (Conversação geral enviada ao Ollama)

---

## 8. Estrutura do Repositório

```
geraldo/
├── docs/                        # Diagramas de arquitetura e roteiro
│   ├── arquitetura_atual_geraldo.excalidraw
│   ├── arquitetura_geraldo.excalidraw
│   └── roteiro.excalidraw
├── desktop-ui/                  # Interface Gráfica Desktop (HTML5 / CSS / JS)
│   ├── index.html               # Layout principal e modal de configurações do Ollama
│   ├── styles.css               # Design system dark com glassmorphism e animações
│   └── app.js                   # Controlador WebSocket e cliente da GUI
├── src-tauri/                   # Wrapper de Janela Nativa e System Tray (Rust / Tauri 2.0)
│   ├── Cargo.toml
│   ├── tauri.conf.json          # Configuração de empacotamento (Windows MSI/EXE e macOS DMG)
│   └── src/main.rs              # Inicialização nativa e IPC
├── ui/
│   └── tui.py                   # Interface Rica de Terminal em Textual (TUI)
├── brain/                       # Inteligência e Processamento de Linguagem
│   ├── llm.py                   # Roteamento NLU vs Ollama com host/modelo dinâmicos
│   ├── nlu.py                   # Classificador de intenções Scikit-Learn (< 1ms)
│   ├── stt.py                   # Transcrição de voz via Faster-Whisper
│   └── tts.py                   # Síntese neural via Piper TTS (ONNX)
├── audio/                       # Captura, Gravação e Reprodução de Áudio
│   ├── recorder.py              # Gravador com Voice Activity Detection (VAD)
│   ├── wakeword.py              # Detector da palavra-chave 'Geraldo'
│   └── player.py                # Reprodutor de áudio e bipes
├── core/                        # Núcleo de Infraestrutura do Sistema
│   ├── ipc.py                   # Servidor WebSocket RPC bidirecional
│   ├── paths.py                 # Gerenciador universal de caminhos multiplataforma
│   └── onboarding.py            # Verificador de saúde e teste de conexão do Ollama
├── tools/                       # Ferramentas Determinísticas
│   ├── timer.py                 # Gerenciamento de Timers, Alarmes, Pomodoro e Cronômetro
│   ├── calendar.py              # Google Calendar
│   ├── hyprland.py              # Automação de janelas do Hyprland
│   ├── system.py                # Clima, horário e volume
│   └── ytmusic.py               # YouTube Music Player
├── tests/                       # Suíte de testes automatizados (Pytest)
├── config.py                    # Configurações globais e persistência de settings
├── main.py                      # Ponto de entrada do daemon de voz
├── run.sh                       # Script de inicialização para background/systemd
└── requirements.txt             # Dependências Python com compatibilidade multiplataforma
```

---

## 9. Testes e Validação

Para executar toda a suíte de testes automatizados com cobertura completa:

```bash
pytest
```

---

## Licença

Distribuído sob a licença MIT. Consulte `LICENSE` para mais informações.
