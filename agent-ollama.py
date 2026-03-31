import sys
import subprocess
import re
import json
import os
import shutil


def install_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if not os.path.exists(requirements_path):
        print("Arquivo requirements.txt não encontrado. Instalação automática impossível.")
        sys.exit(1)

    python_exe = sys.executable or "python"
    in_venv = hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    print("Instalando dependências no Python do sistema...")
    try:
        if in_venv:
            subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
            subprocess.check_call([python_exe, "-m", "pip", "install", "-r", requirements_path])
        else:
            subprocess.check_call([python_exe, "-m", "pip", "install", "--user", "--upgrade", "pip"])
            subprocess.check_call([python_exe, "-m", "pip", "install", "--user", "-r", requirements_path])
        print("Dependências instaladas com sucesso.")
    except subprocess.CalledProcessError as e:
        print(f"Erro durante a instalação de dependências: {e}")
        sys.exit(1)

    os.environ["AGENT_OLLAMA_BOOTSTRAPPED"] = "1"
    os.execv(python_exe, [python_exe] + sys.argv)


import importlib
import platform

PLATFORM = platform.system()
IS_WINDOWS = PLATFORM == "Windows"
if not IS_WINDOWS and not os.getenv("DISPLAY"):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

try:
    import ollama
    import pygame
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.live import Live
    from rich.text import Text
except ModuleNotFoundError as e:
    if os.environ.get("AGENT_OLLAMA_BOOTSTRAPPED") != "1":
        missing = e.name
        print(f"Erro: módulo '{missing}' não encontrado neste Python.")
        print("Tentando instalar dependências automaticamente...\n")
        install_requirements()
    else:
        print(f"Erro: módulo '{e.name}' não encontrado mesmo após instalar dependências.")
        print("Tente rodar o setup do projeto novamente:")
        print("  .\\agent-setup.ps1  (Windows)")
        print("  ./agent-setup.sh   (Linux)")
        print("Ou use o comando global após o setup: agent-ollama")
        sys.exit(1)


def import_elevenlabs_tts():
    try:
        import elevenlabs
        return elevenlabs
    except ImportError:
        raise ImportError("Não foi possível importar o pacote elevenlabs. Instale-o com pip e verifique se o ambiente está correto.")

class ElevenLabsTTS:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.pkg = import_elevenlabs_tts()
        self.client = None
        self.text_to_speech = None
        self.voices_client = None
        self.pkg_voices_fn = None
        self.cached_voices = None
        self._setup()

    def _setup(self):
        ClientClass = getattr(self.pkg, "ElevenLabs", None) or getattr(self.pkg, "Client", None)
        if ClientClass is None:
            raise RuntimeError("Cliente ElevenLabs não encontrado no pacote elevenlabs.")

        try:
            self.client = ClientClass(api_key=self.api_key) if self.api_key else ClientClass()
        except TypeError:
            self.client = ClientClass()

        self.text_to_speech = getattr(self.client, "text_to_speech", None)
        self.voices_client = getattr(self.client, "voices", None)
        self.pkg_voices_fn = getattr(self.pkg, "voices", None)

    def _fetch_voices(self):
        if self.cached_voices is not None:
            return self.cached_voices

        voices = []
        if self.voices_client is not None:
            try:
                response = self.voices_client.get_all()
                voices = getattr(response, "voices", []) or []
            except Exception:
                voices = []

        if not voices and callable(self.pkg_voices_fn):
            try:
                voices = self.pkg_voices_fn() or []
            except Exception:
                voices = []

        self.cached_voices = voices
        return voices

    def list_voices(self):
        return self._fetch_voices()

    def voice_names(self):
        voices = self._fetch_voices()
        result = []
        for v in voices:
            if isinstance(v, dict):
                result.append(v.get("name") or v.get("voice_id") or v.get("id"))
            elif hasattr(v, "name"):
                result.append(v.name)
            elif hasattr(v, "voice_id"):
                result.append(v.voice_id)
            else:
                result.append(str(v))
        return [name for name in result if name]

    def find_voice_id(self, voice):
        if not voice:
            return None

        candidate = voice.strip()
        voices = self._fetch_voices()
        if not voices:
            return candidate

        lower_candidate = candidate.lower()
        for v in voices:
            v_id = None
            v_name = None
            if isinstance(v, dict):
                v_id = v.get("voice_id") or v.get("id")
                v_name = v.get("name")
            else:
                v_id = getattr(v, "voice_id", None) or getattr(v, "id", None)
                v_name = getattr(v, "name", None)

            if v_id and lower_candidate == str(v_id).lower():
                return v_id
            if v_name and lower_candidate == str(v_name).lower():
                return v_id or v_name

        for v in voices:
            v_id = None
            v_name = None
            if isinstance(v, dict):
                v_id = v.get("voice_id") or v.get("id")
                v_name = v.get("name")
            else:
                v_id = getattr(v, "voice_id", None) or getattr(v, "id", None)
                v_name = getattr(v, "name", None)

            if v_name and lower_candidate in str(v_name).lower():
                return v_id or v_name

        # Se não encontrarmos correspondência por nome, use a primeira voz disponível como fallback.
        if voices:
            first = voices[0]
            if isinstance(first, dict):
                return first.get("voice_id") or first.get("id") or first.get("name")
            return getattr(first, "voice_id", None) or getattr(first, "id", None) or getattr(first, "name", None)

        return candidate

    def generate_audio(self, text, voice, model):
        if self.text_to_speech is None:
            raise RuntimeError("Método de geração de áudio ElevenLabs não encontrado.")

        voice_id = self.find_voice_id(voice)
        if not voice_id:
            raise RuntimeError("Não foi possível resolver o ID da voz ElevenLabs.")

        try:
            audio_iter = self.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                output_format="mp3_22050_32",
                model_id=model,
            )
            return b"".join(audio_iter)
        except Exception as e:
            raise RuntimeError(f"Falha ao gerar áudio ElevenLabs: {e}")


def init_eleven_tts(settings=None):
    api_key = None
    if isinstance(settings, dict):
        api_key = settings.get("tts_api_key")
    api_key = api_key or os.getenv("ELEVENLABS_API_KEY")

    try:
        return ElevenLabsTTS(api_key=api_key)
    except Exception as e:
        print(f"Aviso: ElevenLabs TTS não pôde ser inicializado: {e}")
        return None


def reload_eleven_tts():
    global eleven_tts
    eleven_tts = init_eleven_tts(settings)


eleven_tts = None

# Silencia mensagem de boas-vindas do pygame
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import platform
import time
import pygame
import asyncio
import atexit

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
LOCK_FILE = os.path.join(DATA_DIR, "agent.lock")
LOG_FILE = os.path.join(DATA_DIR, "agent.log")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def is_process_running(pid):
    """Verifica se um processo com o PID fornecido está ativo."""
    if pid <= 0:
        return False
    if IS_WINDOWS:
        try:
            # No Windows, usamos tasklist para verificar se o PID existe
            output = subprocess.check_output(["tasklist", "/FI", f"PID eq {pid}", "/NH"], text=True)
            return str(pid) in output
        except:
            return False
    else:
        try:
            # No Linux/Unix, sinal 0 apenas verifica a existência do processo
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

def check_instance_lock():
    """Verifica se já existe uma instância rodando e cria o arquivo de trava."""
    pid_active = False
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            if is_process_running(pid):
                pid_active = True
                console.print(f"[bold red]Erro:[/bold red] Já existe uma instância do {AGENT_NAME} rodando (PID: {pid}).")
                console.print("[yellow]Se você tem certeza que não há outra instância, delete o arquivo 'data/agent.lock'.[/yellow]")
        except (ValueError, IOError):
            pass # Arquivo corrompido ou ilegível, vamos sobrescrever

    if pid_active:
        sys.exit(1)

    # Cria o novo lock file
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    
    # Garante a remoção ao sair
    atexit.register(remove_instance_lock)

def remove_instance_lock():
    """Remove o arquivo de trava ao encerrar."""
    if os.path.exists(LOCK_FILE):
        try:
            # Só remove se o PID no arquivo for o do processo atual
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            if pid == os.getpid():
                os.remove(LOCK_FILE)
        except:
            pass

def load_settings():
    """Carrega as configurações e chaves da pasta data."""
    default_settings = {
        "user_name": "Usuário",
        "ollama_model": "llama3",
        "tts_voice": "alloy",
        "tts_api_key": "",
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
eleven_tts = init_eleven_tts(settings)

OLLAMA_MODEL = settings["ollama_model"]

# Inicializa mixer de áudio
pygame.mixer.init()

async def speak(text):
    """Gera áudio localmente usando ElevenLabs e reproduz o resultado."""
    if not settings.get("tts_enabled", False):
        return

    if eleven_tts is None:
        console.print("[dim red](ElevenLabs TTS não está configurado.)[/dim red]")
        return

    if not text.strip():
        return

    clean_text = re.sub(r'[*_#`]', '', text)
    voice = settings.get("tts_voice", "alloy")

    try:
        with console.status("[bold magenta]Gerando voz local com ElevenLabs...[/bold magenta]"):
            audio_bytes = await asyncio.to_thread(eleven_tts.generate_audio, clean_text, voice, "eleven_multilingual_v2")
            if not audio_bytes:
                console.print("[dim red](Nenhum áudio gerado pelo ElevenLabs local.)[/dim red]")
                return

            if hasattr(audio_bytes, 'read'):
                audio_bytes = audio_bytes.read()
            elif isinstance(audio_bytes, str):
                audio_bytes = audio_bytes.encode('utf-8')

            temp_file = os.path.join(DATA_DIR, "temp_voice.mp3")
            with open(temp_file, "wb") as f:
                f.write(audio_bytes)

            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)

            pygame.mixer.music.unload()
            if os.path.exists(temp_file):
                os.remove(temp_file)
    except Exception as e:
        console.print(f"[dim red](Erro ao gerar voz local ElevenLabs: {e})[/dim red]")

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
   - Chave ElevenLabs: Use ```bash
# CONFIG: ELEVENLABS_API_KEY=SuaChaveAqui
``` para configurar a API de voz.
# CONFIG: ELEVENLABS_API_KEY=SuaChaveAqui
# CONFIG: ELEVENLABS_API_KEY=SuaChaveAqui
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


def get_ollama_message_content(response):
    """Retorna o conteúdo do campo message.content em uma resposta Ollama."""
    if isinstance(response, dict):
        message = response.get('message', {})
    elif hasattr(response, 'message'):
        message = response.message
    else:
        message = response

    if isinstance(message, dict):
        return message.get('content', '') or ''
    elif hasattr(message, 'content'):
        return getattr(message, 'content') or ''
    return ''


def normalize_ollama_models(models_response):
    """Normaliza a lista de modelos retornada pelo Ollama."""
    if isinstance(models_response, dict) and 'models' in models_response:
        models_list = models_response['models']
    elif hasattr(models_response, 'models'):
        models_list = models_response.models
    elif isinstance(models_response, (list, tuple)):
        models_list = list(models_response)
    elif hasattr(models_response, '__iter__'):
        models_list = list(models_response)
    else:
        models_list = []

    model_names = []
    for m in models_list:
        if isinstance(m, dict):
            model_names.append(m.get('name') or m.get('model') or m.get('id') or str(m))
        elif hasattr(m, 'name'):
            model_names.append(m.name)
        elif hasattr(m, 'model'):
            model_names.append(m.model)
        else:
            model_names.append(str(m))

    return [name for name in model_names if name]


def get_ollama_connection_help():
    """Retorna uma mensagem de ajuda quando a conexão com Ollama falha."""
    help_text = [
        "[bold red]Erro:[/bold red] Não foi possível conectar ao Ollama.",
        "Certifique-se de que o Ollama esteja instalado e em execução.",
        "Inicie o servidor local com: [bold green]ollama serve[/bold green]",
        "Ou, se estiver usando outro host, defina a variável de ambiente OLLAMA_HOST.",
    ]
    if shutil.which('ollama') is None:
        help_text.append("O comando 'ollama' não foi encontrado no PATH.")
    return "\n".join(help_text)


def get_available_voices():
    """Retorna a lista de vozes locais do ElevenLabs."""
    if eleven_tts is None:
        return []

    try:
        return eleven_tts.voice_names()
    except Exception:
        return []


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
    """Verifica se há atualizações no repositório git e retorna informações sobre elas."""
    try:
        if not os.path.exists(".git"):
            return None

        with console.status("[bold blue]Verificando atualizações...[/bold blue]"):
            subprocess.run(["git", "fetch"], capture_output=True, check=True)
            status = subprocess.run(["git", "status", "-uno"], capture_output=True, text=True, check=True)
            
            if "Your branch is behind" in status.stdout:
                # Pega o log das mudanças pendentes
                log = subprocess.run(["git", "log", "..@{u}", "--oneline"], capture_output=True, text=True).stdout
                diff = subprocess.run(["git", "diff", "..@{u}", "--stat"], capture_output=True, text=True).stdout
                return {"log": log, "diff": diff}
            else:
                console.print("[dim cyan]O projeto já está na versão mais recente.[/dim cyan]")
                return None
    except Exception as e:
        console.print(f"[dim red](Erro ao verificar atualizações: {e})[/dim red]")
        return None

async def handle_update_decision(update_info):
    """Usa o LLM como um agente separado para decidir se deve atualizar."""
    ollama_model = settings.get("ollama_model", DEFAULT_MODEL)
    
    update_agent_prompt = f"""
    Você é o 'Agente de Atualização' do projeto Agent Ollie.
    Sua única tarefa é analisar as mudanças pendentes no repositório e decidir se o projeto deve ser atualizado AGORA ou se deve AGUARDAR.

    MUDANÇAS PENDENTES (Commits):
    {update_info['log']}

    ESTATÍSTICAS DE ARQUIVOS:
    {update_info['diff']}

    DIRETRIZES:
    1. Se as mudanças parecerem críticas, melhorias de performance ou novas funcionalidades úteis, recomende ATUALIZAR.
    2. Se parecerem instáveis ou se o usuário estiver no meio de uma tarefa importante, considere sugerir AGUARDAR.
    3. Responda APENAS com um parágrafo curto justificando sua decisão e termine com 'DECISÃO: ATUALIZAR' ou 'DECISÃO: AGUARDAR'.
    4. Responda em Português (Brasil).
    """

    try:
        with console.status("[bold magenta]Update Agent analisando mudanças...[/bold magenta]"):
            response = await asyncio.to_thread(ollama.chat, model=ollama_model, messages=[{'role': 'user', 'content': update_agent_prompt}])
            content = get_ollama_message_content(response)
            
            console.print(Panel(content, title="Update Agent - Recomendação", border_style="magenta"))
            
            if "DECISÃO: ATUALIZAR" in content:
                confirm = await asyncio.to_thread(console.input, "[bold yellow]O Agente recomenda atualizar. Aplicar agora? (s/n): [/bold yellow]")
                if confirm.lower() == 's':
                    with console.status("[bold green]Aplicando atualização...[/bold green]"):
                        subprocess.run(["git", "pull"], capture_output=True, check=True)
                        console.print("[bold green]Projeto atualizado com sucesso! Reinicie o programa para aplicar as mudanças.[/bold green]")
                        sys.exit(0)
            else:
                console.print("[yellow]Atualização adiada conforme recomendação do Agente.[/yellow]")
    except Exception as e:
        console.print(f"[red]Erro na decisão de atualização: {e}[/red]")

# Configurações do Ollama
DEFAULT_MODEL = "llama3"

async def process_multi_step_task(messages, ollama_model):
    """Processa uma tarefa que pode envolver múltiplas etapas de execução de comandos."""
    step_count = 0
    max_steps = 10
    final_response = ""

    while step_count < max_steps:
        full_response = ""
        show_thoughts = settings.get("show_thoughts", False)
        status_text = f"{AGENT_NAME} ({ollama_model}) pensando..."

        try:
            if show_thoughts:
                with Live(Text(status_text, style="bold yellow"), refresh_per_second=10) as live:
                    response_gen = await asyncio.to_thread(ollama.chat, model=ollama_model, messages=messages, stream=True)
                    for chunk in response_gen:
                        content = get_ollama_message_content(chunk)
                        full_response += content
                        live.update(Text(f"Ollama respondendo: {full_response[-100:]}", style="italic cyan"))
            else:
                with console.status(f"[bold yellow]{status_text}[/bold yellow]"):
                    response = await asyncio.to_thread(ollama.chat, model=ollama_model, messages=messages)
                    full_response = get_ollama_message_content(response)
        except ConnectionError:
            console.print(Panel(get_ollama_connection_help(), title="Ollama indisponível", border_style="red"))
            return "", messages

        llm_response = full_response
        messages.append({'role': 'assistant', 'content': llm_response})

        # Processa configurações embutidas no texto
        if "# CONFIG: SHOW_THOUGHTS=True" in llm_response:
            settings["show_thoughts"] = True
            save_settings(settings)
            console.print("[bold magenta]Modo de visualização de pensamentos ativado.[/bold magenta]")
        elif "# CONFIG: SHOW_THOUGHTS=False" in llm_response:
            settings["show_thoughts"] = False
            save_settings(settings)
            console.print("[bold magenta]Modo de visualização de pensamentos desativado.[/bold magenta]")

        if "# CONFIG: TTS_ENABLED=True" in llm_response:
            settings["tts_enabled"] = True
            save_settings(settings)
            console.print("[bold magenta]Saída de voz (TTS) ativada.[/bold magenta]")
        elif "# CONFIG: TTS_ENABLED=False" in llm_response:
            settings["tts_enabled"] = False
            save_settings(settings)
            console.print("[bold magenta]Saída de voz (TTS) desativada.[/bold magenta]")

        tts_voice_match = re.search(r"# CONFIG: TTS_VOICE=(.*)", llm_response)
        if tts_voice_match:
            new_voice = tts_voice_match.group(1).strip()
            settings["tts_voice"] = new_voice
            save_settings(settings)
            console.print(f"[bold magenta]Voz ElevenLabs alterada para: {new_voice}[/bold magenta]")

        api_key_match = re.search(r"# CONFIG: ELEVENLABS_API_KEY=(.*)", llm_response)
        if api_key_match:
            new_api_key = api_key_match.group(1).strip()
            settings["tts_api_key"] = new_api_key
            save_settings(settings)
            reload_eleven_tts()
            console.print("[bold magenta]Chave ElevenLabs salva e recarregada.[/bold magenta]")

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
                await speak(summary)

            console.print(f"[bold cyan]Executando (Etapa {step_count}):[/bold cyan] `{command}`")
            stdout, stderr, code = execute_command(command)

            result_msg = f"RESULTADO DA ETAPA {step_count}:\nSTDOUT: {stdout}\nSTDERR: {stderr}\nEXIT_CODE: {code}"
            if len(result_msg) > 2000:
                result_msg = result_msg[:1000] + "\n... (saída truncada por ser muito longa) ...\n" + result_msg[-1000:]

            messages.append({'role': 'user', 'content': result_msg})
            continue
        else:
            final_response = llm_response
            console.print(Panel(Markdown(llm_response), border_style="green", title="Tarefa Concluída"))
            await speak(llm_response)
            break

    if step_count >= max_steps:
        console.print("[bold red]Aviso:[/bold red] Limite de etapas atingido.")

    return final_response, messages

async def chat():
    global memory
    # Verifica atualizações ao iniciar e lida com a decisão do Agente
    update_info = check_for_updates()
    if update_info:
        await handle_update_decision(update_info)
    
    # Pega o modelo das configurações
    ollama_model = settings.get("ollama_model", DEFAULT_MODEL)

    # Verifica se o Ollama está acessível e se o modelo existe
    try:
        models_response = ollama.list()
        model_names = normalize_ollama_models(models_response)

        if ollama_model not in model_names and (ollama_model + ":latest") not in model_names:
            if model_names:
                console.print(Panel(f"[bold yellow]Aviso:[/bold yellow] O modelo '[bold cyan]{ollama_model}[/bold cyan]' não foi encontrado.\n\n[bold]Modelos disponíveis detectados:[/bold]\n" + "\n".join([f"- {m}" for m in model_names]) + "\n\nDigite o nome de um modelo acima para usar agora ou pressione Enter para sair:", title="Modelo Ausente", border_style="yellow"))
                choice = await asyncio.to_thread(console.input, "[bold blue]Sua escolha:[/bold blue] ")
                choice = choice.strip()
                if choice in model_names or (choice + ":latest") in model_names:
                    ollama_model = choice
                    settings["ollama_model"] = ollama_model
                    save_settings(settings)
                else:
                    return
            else:
                console.print(Panel(f"[bold red]Aviso:[/bold red] Nenhum modelo foi encontrado no seu Ollama.\n\nPor favor, baixe um modelo primeiro no terminal com:\n[bold green]ollama pull llama3[/bold green] (ou o modelo de sua preferência)", title="Nenhum Modelo Encontrado", border_style="red"))
                return
    except ConnectionError:
        console.print(Panel(get_ollama_connection_help(), title="Erro Crítico", border_style="red"))
        return
    except Exception as e:
        console.print(Panel(f"[bold red]Erro de conexão com o Ollama:[/bold red]\n{e}\n\nCertifique-se de que o Ollama está rodando.", title="Erro Crítico", border_style="red"))
        return

    # Exibe o logo e boas-vindas
    console.print(Panel(Text(ASCII_LOGO, style="bold cyan"), border_style="cyan"))
    console.print(Panel(f"[bold green]{AGENT_NAME} - Agent Ollama[/bold green]\nModelo atual: [bold cyan]{ollama_model}[/bold cyan]\nDigite '/model <nome>' para trocar.\nModo multi-etapa e atualizações ativados.", title="Sistema Ativo"))
    
    # Prepara prompt de sistema com a memória atual e vozes disponíveis
    current_memory_text = json.dumps(memory, indent=2, ensure_ascii=False)
    available_voices = get_available_voices()
    voice_info = "Voz atual: {}\nVozes disponíveis: {}".format(
        settings.get('tts_voice', 'alloy'),
        ", ".join(available_voices) if available_voices else "nenhuma voz encontrada"
    )
    system_message = f"{SYSTEM_PROMPT.format(user_name=settings.get('user_name', 'Usuário'))}\n\n{voice_info}\n\nMEMÓRIA ATUAL:\n{current_memory_text}"
    
    messages = [{'role': 'system', 'content': system_message}]

    while True:
        try:
            current_user = settings.get("user_name", "Usuário")
            user_input = await asyncio.to_thread(console.input, f"[bold blue]{current_user}:[/bold blue] ")
            
            if user_input.lower() in ["sair", "exit", "quit"]:
                break

            # Comando para trocar o modelo em tempo real
            if user_input.startswith("/model "):
                new_model = user_input.split(" ")[1].strip()
                try:
                    models_response = ollama.list()
                    model_names = normalize_ollama_models(models_response)
                    
                    if new_model not in model_names and (new_model + ":latest") not in model_names:
                        console.print(f"[bold red]Erro:[/bold red] O modelo '{new_model}' não está baixado.\nBaixe-o primeiro no terminal com: [bold green]ollama pull {new_model}[/bold green]")
                        continue
                    
                    ollama_model = new_model
                    settings["ollama_model"] = ollama_model
                    save_settings(settings)
                    console.print(f"[bold green]Modelo alterado para {ollama_model} e salvo![/bold green]")
                    continue
                except ConnectionError:
                    console.print(get_ollama_connection_help())
                    continue
                except Exception as e:
                    console.print(f"[bold red]Erro ao verificar modelo {new_model}: {e}[/bold red]")
                    continue

            # Comando para listar vozes locais ElevenLabs
            if user_input.strip() == "/voices":
                if eleven_tts is None:
                    console.print("[bold red]Erro:[/bold red] ElevenLabs TTS não está configurado.")
                    continue

                with console.status("[bold magenta]Buscando vozes locais ElevenLabs...[/bold magenta]"):
                    try:
                        voices_list = await asyncio.to_thread(eleven_tts.list_voices)
                        table_text = "[bold cyan]Vozes ElevenLabs locais disponíveis:[/bold cyan]\n"
                        for v in voices_list:
                            voice_name = None
                            if isinstance(v, dict):
                                voice_name = v.get('name') or v.get('voice_id') or v.get('id')
                            elif hasattr(v, 'name'):
                                voice_name = v.name
                            elif hasattr(v, 'voice_id'):
                                voice_name = v.voice_id
                            else:
                                voice_name = str(v)
                            table_text += f"- {voice_name}\n"
                        console.print(Panel(table_text, title="Vozes ElevenLabs"))
                        console.print("Use `/setvoice <nome_da_voz>` para trocar.")
                    except Exception as e:
                        console.print(f"[bold red]Erro ao listar vozes ElevenLabs:[/bold red] {e}")
                continue

            # Comando para trocar a voz
            if user_input.startswith("/setvoice "):
                new_voice = user_input.split(" ", 1)[1].strip()
                settings["tts_voice"] = new_voice
                save_settings(settings)
                console.print(f"[bold green]Voz ElevenLabs alterada para {new_voice} e salva![/bold green]")
                continue

            # Comando para configurar a chave ElevenLabs API
            if user_input.startswith("/setapikey "):
                new_key = user_input.split(" ", 1)[1].strip()
                settings["tts_api_key"] = new_key
                save_settings(settings)
                reload_eleven_tts()
                console.print("[bold green]Chave ElevenLabs salva e recarregada![/bold green]")
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
            
            # Chama o processador de tarefas multi-etapa
            ollama_model = settings.get("ollama_model", DEFAULT_MODEL)
            await process_multi_step_task(messages, ollama_model)

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Interrompido pelo usuário. Saindo...[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Erro:[/bold red] {e}")

if __name__ == "__main__":
    try:
        # Modo de configuração
        if len(sys.argv) > 1 and sys.argv[1] == "config":
            console.print(Panel("[bold cyan]Agent Ollie - Modo de Configuração[/bold cyan]", border_style="cyan"))
            
            # Menu de configuração
            while True:
                console.print("\n[bold]Selecione o que deseja configurar:[/bold]")
                console.print("1. Nome do Usuário")
                console.print("2. Modelo do Ollama")
                console.print("3. Voz ElevenLabs local")
                console.print("4. Chave ElevenLabs API")
                console.print("5. Senha Sudo (Linux)")
                console.print("0. Sair e Salvar")
                
                opcao = console.input("\n[bold yellow]Opção: [/bold yellow]").strip()
                
                if opcao == "1":
                    settings["user_name"] = console.input(f"Novo nome (atual: {settings['user_name']}): ").strip() or settings["user_name"]
                elif opcao == "2":
                    settings["ollama_model"] = console.input(f"Novo modelo (atual: {settings['ollama_model']}): ").strip() or settings["ollama_model"]
                elif opcao == "3":
                    settings["tts_voice"] = console.input(f"Nova voz ElevenLabs local (atual: {settings['tts_voice']}): ").strip() or settings["tts_voice"]
                elif opcao == "4":
                    settings["tts_api_key"] = console.input("Nova chave ElevenLabs API (não será exibida): ").strip() or settings["tts_api_key"]
                    reload_eleven_tts()
                elif opcao == "5":
                    if IS_WINDOWS:
                        console.print("[red]Sudo não é usado no Windows.[/red]")
                    else:
                        settings["sudo_password"] = console.input("Nova senha sudo: ").strip() or settings["sudo_password"]
                elif opcao == "0":
                    save_settings(settings)
                    console.print("[green]Configurações salvas![/green]")
                    sys.exit(0)

                save_settings(settings)

        # Se chegou aqui, é o modo interativo normal
        check_instance_lock()
        asyncio.run(chat())
    except KeyboardInterrupt:
        pass
    finally:
        pygame.mixer.quit()
