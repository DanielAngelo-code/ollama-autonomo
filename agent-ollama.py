import ollama
import subprocess
import sys
import re
import requests
import json
import os
import platform
import time
import pygame
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.text import Text

console = Console()

AGENT_NAME = "Ollie"

ASCII_LOGO = r"""
   _____                             __     ____   ____
  /  _  \    ____   ____   ____    _/  |_  \   \ /   /
 /  /_\  \  / ___\_/ __ \ /    \   \   __\  \   Y   / 
/    |    \/ /_/  >  ___/|   |  \   |  |     \     /  
\____|__  /\___  / \___  >___|  /   |__|      \___/   
        \//_____/      \/     \/                      
"""

# Detecção de Plataforma
PLATFORM = platform.system()
IS_WINDOWS = PLATFORM == "Windows"
SHELL_TYPE = "PowerShell" if IS_WINDOWS else "Bash"

# Configurações Persistentes (Localizadas na pasta /data)
DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def load_settings():
    """Carrega as configurações e chaves da pasta data."""
    default_settings = {
        "user_name": "Usuário",
        "murf_api_key": "",
        "ollama_model": "llama3",
        "voice_id": "pt-BR-benício",
        "voice_style": "Conversational",
        "sudo_password": "",
        "show_thoughts": False,
        "tts_enabled": False
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # Garante que todos os campos padrão existam
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except:
            pass
    return default_settings

def save_settings(settings):
    """Salva as configurações na pasta data."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def load_memory():
    """Carrega a memória de longo prazo da pasta data."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"notes": [], "last_interaction": ""}

def save_memory(memory):
    """Salva a memória de longo prazo na pasta data."""
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=4)

# Inicializa configurações e memória
settings = load_settings()
memory = load_memory()

# Solicita a chave Murf.ai se não estiver presente
if not settings["murf_api_key"]:
    console.print(Panel("[bold yellow]Configuração Inicial do Murf.ai[/bold yellow]\nNenhuma chave de API encontrada na pasta /data.\n\nVocê pode colar sua chave agora ou pressionar Enter para continuar sem voz.", title="Ação Necessária"))
    key = console.input("[bold cyan]Chave Murf.ai (ap2_...): [/bold cyan]").strip()
    if key:
        settings["murf_api_key"] = key
        save_settings(settings)
        console.print("[bold green]Chave salva com sucesso em data/settings.json![/bold green]")

# Configurações Murf.ai
MURF_API_KEY = settings["murf_api_key"]
MURF_VOICE_ID = "pt-BR-benício" # ID exato encontrado na biblioteca da API (com acento)
MURF_STYLE = "Conversational"
MURF_MODEL_VERSION = "GEN2"
OLLAMA_MODEL = settings["ollama_model"]

# Inicializa mixer de áudio
pygame.mixer.init()

def speak(text):
    """Envia o texto para murf.ai e reproduz o áudio resultante."""
    # Verifica se o TTS está habilitado nas configurações
    if not settings.get("tts_enabled", False):
        return

    if not text.strip() or not MURF_API_KEY:
        return

    # Limpa markdown simples para a fala ser mais natural
    clean_text = re.sub(r'[*_#`]', '', text)
    
    url = "https://api.murf.ai/v1/speech/generate"
    headers = {
        "Content-Type": "application/json",
        "api-key": MURF_API_KEY # Header correto para a API Murf.ai
    }
    payload = {
        "voiceId": MURF_VOICE_ID,
        "style": MURF_STYLE,
        "text": clean_text,
        "format": "MP3",
        "modelVersion": MURF_MODEL_VERSION,
        "locale": "pt-BR" # Garante que o modelo use o sotaque correto
    }

    try:
        with console.status("[bold magenta]Gerando voz (Murf.ai)...[/bold magenta]"):
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                try:
                    error_detail = response.json()
                    console.print(f"[dim red](Murf.ai Erro Detalhado: {error_detail})[/dim red]")
                except:
                    console.print(f"[dim red](Murf.ai Erro HTTP {response.status_code})[/dim red]")
                return # Sai da função se houver erro na API

            response.raise_for_status()
            data = response.json()
            # A API pode retornar a URL no campo 'audioFile' ou 'audioUrl'
            audio_url = data.get("audioUrl") or data.get("audioFile")

            if audio_url:
                # Download do áudio temporário
                audio_res = requests.get(audio_url)
                audio_res.raise_for_status()
                audio_data = audio_res.content
                
                temp_file = os.path.join(DATA_DIR, "temp_voice.mp3")
                with open(temp_file, "wb") as f:
                    f.write(audio_data)

                # Reprodução
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                
                pygame.mixer.music.unload()
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            else:
                console.print(f"[dim red](Murf.ai não retornou URL de áudio: {data})[/dim red]")
    except Exception as e:
        console.print(f"[dim red](Erro ao gerar voz: {e})[/dim red]")

SYSTEM_PROMPT = f"""
Você é {AGENT_NAME}, um assistente de administração multiplataforma ("Agent Ollama").
Sua missão é ajudar o usuário com tarefas em Português (Brasil).
O nome atual do usuário é: {{user_name}}. Refira-se a ele por esse nome quando apropriado.

AMBIENTE ATUAL: {PLATFORM} ({SHELL_TYPE})

DIRETRIZES DE AMBIENTE (IMPORTANTE):
1. **Windows (PowerShell)**: Use comandos nativos do PowerShell. NUNCA tente executar "Run as Administrator" ou "sudo". Se uma tarefa exigir privilégios elevados, explique ao usuário que ele deve rodar este script em um terminal elevado (Administrador).
2. **Linux (Bash)**: Use comandos bash. Se precisar de sudo, use `sudo comando`. O script injetará a senha se disponível.
3. **Caminhos**: SEMPRE use caminhos relativos ao projeto (ex: "./data/memory.json") ou caminhos absolutos com aspas se necessário. NUNCA tente escrever na raiz C:\\ diretamente no Windows ou em pastas de sistema sem permissão.
4. **Idioma**: Responda SEMPRE em Português (Brasil).

DIRETRIZES DE ESTILO:
1. **Estilo WhatsApp**: Respostas extremamente curtas, diretas e sem formalidades.
2. **Aguarde Instruções**: Só execute comandos se solicitado.
3. **Raciocínio Multi-etapa**: Uma etapa por vez.
4. **Execução**: Use ```bash\ncomando\n``` para comandos Linux ou ```powershell\ncomando\n``` para Windows.
5. **Memória**: Localizada em ./data/memory.json. Use-a para guardar fatos importantes sobre o sistema.
6. **Controle de Interface**: 
   - Pensamentos: Use ```bash\n# CONFIG: SHOW_THOUGHTS=True\n``` ou False.
   - Voz (TTS): Use ```bash\n# CONFIG: TTS_ENABLED=True\n``` ou False.
   - Nome do Usuário: Use ```bash\n# CONFIG: USER_NAME=NovoNome\n``` para mudar como você chama o usuário.
"""

def extract_bash_command(response):
    """Extrai o comando bash/powershell de dentro de blocos de código markdown."""
    pattern = r"```(?:bash|powershell|ps1|sh)?\n(.*?)\n```"
    match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_summary(response):
    """Extrai o texto antes do bloco de código como resumo da ação."""
    text = re.sub(r"```(?:bash|powershell|ps1|sh)?\n.*?\n```", "", response, flags=re.DOTALL | re.IGNORECASE).strip()
    return text

def execute_command(command):
    """Executa o comando no terminal e retorna a saída, lidando com sudo se necessário."""
    sudo_password = settings.get("sudo_password", "")
    
    # No Windows, garantimos o uso do PowerShell se o comando não for explicitamente CMD
    if IS_WINDOWS:
        # Escapa aspas duplas para o PowerShell e evita problemas de sintaxe no f-string
        escaped_command = command.replace('"', '\\"')
        final_command = f'powershell -ExecutionPolicy Bypass -Command "{escaped_command}"'
    elif command.strip().startswith("sudo ") and sudo_password:
        # No Linux, usamos 'sudo -S' para ler a senha do stdin
        final_command = command.replace("sudo ", f"echo '{sudo_password}' | sudo -S ", 1)
    else:
        final_command = command

    try:
        process = subprocess.Popen(
            final_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        # Limpa a saída do sudo -S para não poluir o log da IA
        if "[sudo] password for" in stderr:
            stderr = re.sub(r"\[sudo\] password for .*?:", "", stderr).strip()
            
        return stdout, stderr, process.returncode
    except Exception as e:
        return "", str(e), 1

def check_for_updates():
    """Verifica se há atualizações no repositório git e as aplica."""
    try:
        # Verifica se estamos em um repositório git
        if not os.path.exists(".git"):
            return False

        with console.status("[bold blue]Verificando atualizações...[/bold blue]"):
            # Faz um fetch para ver se há mudanças
            subprocess.run(["git", "fetch"], capture_output=True, check=True)
            status = subprocess.run(["git", "status", "-uno"], capture_output=True, text=True, check=True)
            
            if "Your branch is behind" in status.stdout:
                console.print("[bold yellow]Nova atualização encontrada! Aplicando...[/bold yellow]")
                subprocess.run(["git", "pull"], capture_output=True, check=True)
                console.print("[bold green]Projeto atualizado com sucesso! Reinicie para aplicar.[/bold green]")
                return True
            else:
                console.print("[dim cyan]O projeto já está na versão mais recente.[/dim cyan]")
                return False
    except Exception as e:
        console.print(f"[dim red](Erro ao verificar atualizações: {e})[/dim red]")
        return False

# Configurações do Ollama
DEFAULT_MODEL = "llama3"

def chat():
    global memory
    # Verifica atualizações ao iniciar
    check_for_updates()
    
    # Pega o modelo das configurações
    ollama_model = settings.get("ollama_model", DEFAULT_MODEL)

    # Verifica se o Ollama está acessível e se o modelo existe
    try:
        models_response = ollama.list()
        models_list = []
        if isinstance(models_response, dict) and 'models' in models_response:
            models_list = models_response['models']
        elif hasattr(models_response, 'models'):
            models_list = models_response.models
        
        model_names = []
        for m in models_list:
            if isinstance(m, dict) and 'name' in m:
                model_names.append(m['name'])
            elif hasattr(m, 'model'): 
                model_names.append(m.model)
            elif hasattr(m, 'name'):
                model_names.append(m.name)

        if ollama_model not in model_names and (ollama_model + ":latest") not in model_names:
            if model_names:
                console.print(Panel(f"[bold yellow]Aviso:[/bold yellow] O modelo '[bold cyan]{ollama_model}[/bold cyan]' não foi encontrado.\n\n[bold]Modelos disponíveis detectados:[/bold]\n" + "\n".join([f"- {m}" for m in model_names]) + "\n\nDigite o nome de um modelo acima para usar agora ou pressione Enter para sair:", title="Modelo Ausente", border_style="yellow"))
                choice = console.input("[bold blue]Sua escolha:[/bold blue] ").strip()
                if choice in model_names or (choice + ":latest") in model_names:
                    ollama_model = choice
                    settings["ollama_model"] = ollama_model
                    save_settings(settings)
                else:
                    return
            else:
                console.print(Panel(f"[bold red]Aviso:[/bold red] Nenhum modelo foi encontrado no seu Ollama.\n\nPor favor, baixe um modelo primeiro no terminal com:\n[bold green]ollama pull llama3[/bold green] (ou o modelo de sua preferência)", title="Nenhum Modelo Encontrado", border_style="red"))
                return
    except Exception as e:
        console.print(Panel(f"[bold red]Erro de conexão com o Ollama:[/bold red]\n{e}\n\nCertifique-se de que o Ollama está rodando.", title="Erro Crítico", border_style="red"))
        return

    # Exibe o logo e boas-vindas
    console.print(Panel(Text(ASCII_LOGO, style="bold cyan"), border_style="cyan"))
    console.print(Panel(f"[bold green]{AGENT_NAME} - Agent Ollama[/bold green]\nModelo atual: [bold cyan]{ollama_model}[/bold cyan]\nDigite '/model <nome>' para trocar.\nModo multi-etapa e atualizações ativados.", title="Sistema Ativo"))
    
    # Prepara prompt de sistema com a memória atual
    current_memory_text = json.dumps(memory, indent=2, ensure_ascii=False)
    system_message = f"{SYSTEM_PROMPT.format(user_name=settings.get('user_name', 'Usuário'))}\n\nMEMÓRIA ATUAL:\n{current_memory_text}"
    
    messages = [{'role': 'system', 'content': system_message}]

    while True:
        try:
            current_user = settings.get("user_name", "Usuário")
            user_input = console.input(f"[bold blue]{current_user}:[/bold blue] ")
            
            if user_input.lower() in ["sair", "exit", "quit"]:
                break

            # Comando para trocar o modelo em tempo real
            if user_input.startswith("/model "):
                new_model = user_input.split(" ")[1].strip()
                try:
                    models_response = ollama.list()
                    models_list = []
                    if isinstance(models_response, dict) and 'models' in models_response:
                        models_list = models_response['models']
                    elif hasattr(models_response, 'models'):
                        models_list = models_response.models
                    
                    model_names = []
                    for m in models_list:
                        if isinstance(m, dict) and 'name' in m:
                            model_names.append(m['name'])
                        elif hasattr(m, 'model'):
                            model_names.append(m.model)
                        elif hasattr(m, 'name'):
                            model_names.append(m.name)
                    
                    if new_model not in model_names and (new_model + ":latest") not in model_names:
                        console.print(f"[bold red]Erro:[/bold red] O modelo '{new_model}' não está baixado.\nBaixe-o primeiro no terminal com: [bold green]ollama pull {new_model}[/bold green]")
                        continue
                    
                    ollama_model = new_model
                    settings["ollama_model"] = ollama_model
                    save_settings(settings)
                    console.print(f"[bold green]Modelo alterado para {ollama_model} e salvo![/bold green]")
                    continue
                except Exception as e:
                    console.print(f"[bold red]Erro ao verificar modelo {new_model}: {e}[/bold red]")
                    continue

            # Comando para listar vozes do Murf.ai
            if user_input.strip() == "/voices":
                if not MURF_API_KEY:
                    console.print("[bold red]Erro:[/bold red] Chave API do Murf.ai não configurada.")
                    continue
                with console.status("[bold magenta]Buscando vozes...[/bold magenta]"):
                    try:
                        url = "https://api.murf.ai/v1/speech/voices"
                        headers = {"api-key": MURF_API_KEY}
                        response = requests.get(url, headers=headers)
                        response.raise_for_status()
                        voices = response.json()
                        pt_voices = [v for v in voices if v.get('locale') == 'pt-BR']
                        
                        table_text = "[bold cyan]Vozes Disponíveis (pt-BR):[/bold cyan]\n"
                        for v in pt_voices:
                            table_text += f"- Nome: {v.get('displayName')}, ID: [bold]{v.get('voiceId')}[/bold]\n"
                        
                        console.print(Panel(table_text, title="Murf.ai Voices"))
                        console.print("Use `/setvoice <ID>` para trocar.")
                    except Exception as e:
                        console.print(f"[bold red]Erro ao listar vozes:[/bold red] {e}")
                continue

            # Comando para trocar a voz
            if user_input.startswith("/setvoice "):
                new_voice = user_input.split(" ")[1].strip()
                settings["voice_id"] = new_voice
                save_settings(settings)
                global MURF_VOICE_ID
                MURF_VOICE_ID = new_voice
                console.print(f"[bold green]Voz alterada para {new_voice} e salva![/bold green]")
                continue

            # Comando para configurar a senha sudo (Linux)
            if user_input.startswith("/setsudo "):
                if IS_WINDOWS:
                    console.print("[bold yellow]Aviso:[/bold yellow] O comando sudo não é utilizado no Windows.")
                    continue
                password = user_input.split(" ", 1)[1].strip()
                settings["sudo_password"] = password
                save_settings(settings)
                console.print("[bold green]Senha sudo salva com sucesso em data/settings.json![/bold green]")
                continue

            # Comando para limpar a memória
            if user_input.strip() == "/clearmem":
                memory = {"notes": [], "last_interaction": ""}
                save_memory(memory)
                current_memory_text = json.dumps(memory, indent=2, ensure_ascii=False)
                system_message = f"{SYSTEM_PROMPT}\n\nMEMÓRIA ATUAL:\n{current_memory_text}"
                messages = [{'role': 'system', 'content': system_message}]
                console.print("[bold green]Memória persistente e histórico da conversa foram limpos![/bold green]")
                continue

            messages.append({'role': 'user', 'content': user_input})
            
            step_count = 0
            max_steps = 10

            while step_count < max_steps:
                full_response = ""
                show_thoughts = settings.get("show_thoughts", False)
                
                status_text = f"Ollama ({ollama_model}) pensando..."
                
                if show_thoughts:
                    with Live(Text(status_text, style="bold yellow"), refresh_per_second=10) as live:
                        response_gen = ollama.chat(model=ollama_model, messages=messages, stream=True)
                        for chunk in response_gen:
                            content = chunk['message']['content']
                            full_response += content
                            live.update(Text(f"Ollama respondendo: {full_response[-100:]}", style="italic cyan"))
                else:
                    with console.status(f"[bold yellow]{status_text}[/bold yellow]"):
                        response = ollama.chat(model=ollama_model, messages=messages)
                        full_response = response['message']['content']
                
                llm_response = full_response
                messages.append({'role': 'assistant', 'content': llm_response})
                
                # Verifica se a IA quer alterar a configuração de exibição de pensamentos
                if "# CONFIG: SHOW_THOUGHTS=True" in llm_response:
                    settings["show_thoughts"] = True
                    save_settings(settings)
                    console.print("[bold magenta]Modo de visualização de pensamentos ativado.[/bold magenta]")
                elif "# CONFIG: SHOW_THOUGHTS=False" in llm_response:
                    settings["show_thoughts"] = False
                    save_settings(settings)
                    console.print("[bold magenta]Modo de visualização de pensamentos desativado.[/bold magenta]")
                
                # Verifica se a IA quer alterar a configuração do TTS
                if "# CONFIG: TTS_ENABLED=True" in llm_response:
                    settings["tts_enabled"] = True
                    save_settings(settings)
                    console.print("[bold magenta]Saída de voz (TTS) ativada.[/bold magenta]")
                elif "# CONFIG: TTS_ENABLED=False" in llm_response:
                    settings["tts_enabled"] = False
                    save_settings(settings)
                    console.print("[bold magenta]Saída de voz (TTS) desativada.[/bold magenta]")
                
                # Verifica se a IA quer alterar o nome do usuário
                user_name_match = re.search(r"# CONFIG: USER_NAME=(.*)", llm_response)
                if user_name_match:
                    new_name = user_name_match.group(1).strip()
                    settings["user_name"] = new_name
                    save_settings(settings)
                    console.print(f"[bold magenta]Nome do usuário alterado para: {new_name}[/bold magenta]")

                command = extract_bash_command(llm_response)
                summary = extract_summary(llm_response)

                if command:
                    step_count += 1
                    if summary:
                        console.print(f"[italic yellow]→ {summary}[/italic yellow]")
                        speak(summary)
                    
                    console.print(f"[bold cyan]Executando (Etapa {step_count}):[/bold cyan] `{command}`")
                    stdout, stderr, code = execute_command(command)
                    
                    result_msg = f"RESULTADO DA ETAPA {step_count}:\nSTDOUT: {stdout}\nSTDERR: {stderr}\nEXIT_CODE: {code}"
                    
                    if len(result_msg) > 2000:
                        result_msg = result_msg[:1000] + "\n... (saída truncada por ser muito longa) ...\n" + result_msg[-1000:]
                    
                    messages.append({'role': 'user', 'content': result_msg})
                    continue
                else:
                    console.print(Panel(Markdown(llm_response), border_style="green", title="Tarefa Concluída"))
                    speak(llm_response)
                    break
            
            if step_count >= max_steps:
                console.print("[bold red]Aviso:[/bold red] Limite de etapas atingido.")

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Interrompido pelo usuário. Saindo...[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Erro:[/bold red] {e}")

if __name__ == "__main__":
    try:
        chat()
    finally:
        pygame.mixer.quit()
