import ollama
import subprocess
import sys
import re
import requests
import json
import os
# Silencia mensagem de boas-vindas do pygame
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import platform
import time
import pygame
import asyncio
import atexit
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
        "murf_api_key": "",
        "ollama_model": "llama3",
        "voice_id": "pt-BR-benício",
        "voice_style": "Conversational",
        "sudo_password": "",
        "show_thoughts": False,
        "tts_enabled": False,
        "discord_token": "",
        "discord_enabled": False
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

# Solicita a chave Murf.ai se não estiver presente (apenas se não estiver no modo config)
if not settings["murf_api_key"] and not (len(sys.argv) > 1 and sys.argv[1] == "config"):
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

# Variáveis globais para o bot do Discord
discord_client = None

async def run_discord_bot():
    """Lógica básica para o bot do Discord."""
    try:
        import discord
        from discord.ext import commands
    except ImportError:
        console.print("[red]Erro: Biblioteca 'discord.py' não encontrada. Instale com 'pip install discord.py'[/red]")
        return

    intents = discord.Intents.all() # Usa todas as intents para garantir captura máxima
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        console.print(f"[bold magenta][DISCORD][/bold magenta] Bot conectado como [bold]{bot.user}[/bold]!")
        # Define status do bot
        await bot.change_presence(activity=discord.Game(name="!cmd <prompt>"))

    async def handle_discord_prompt(ctx, prompt):
        """Função centralizada para processar prompts vindos do Discord."""
        console.print(f"[bold magenta][DISCORD][/bold magenta] Mensagem de [bold]{ctx.author.name}[/bold]: {prompt}")
        
        messages = [
            {'role': 'system', 'content': f"{SYSTEM_PROMPT.format(user_name=ctx.author.name)}\n\n(AVISO: Você está respondendo via Discord)"},
            {'role': 'user', 'content': prompt}
        ]
        
        try:
            async with ctx.typing():
                ollama_model = settings.get("ollama_model", DEFAULT_MODEL)
                final_response, _ = await process_multi_step_task(messages, ollama_model, is_discord=True, ctx=ctx)
                
                console.print(f"[bold magenta][DISCORD][/bold magenta] Ollie respondeu a {ctx.author.name}")
                
                if final_response:
                    if len(final_response) > 2000:
                        for i in range(0, len(final_response), 2000):
                            await ctx.send(final_response[i:i+2000])
                    else:
                        await ctx.send(final_response)
                else:
                    await ctx.send("✅ Tarefa concluída.")
        except Exception as e:
            console.print(f"[bold red][DISCORD ERROR] Erro ao processar pedido de {ctx.author.name}: {e}[/bold red]")
            await ctx.send(f"❌ Erro ao processar pedido: {e}")

    @bot.event
    async def on_message(message):
        # Ignora mensagens do próprio bot
        if message.author == bot.user:
            return

        # Log de debug para ver o que o bot está recebendo
        console.print(f"[dim magenta][DISCORD DEBUG][/dim magenta] Mensagem vista em #[bold]{message.channel}[/bold] de [bold]{message.author}[/bold]: {message.content}")

        # Se for Mensagem Direta (DM) e não for um comando (!), processa como prompt automático
        if isinstance(message.channel, discord.DMChannel) and not message.content.startswith("!"):
            await handle_discord_prompt(message.channel, message.content)
            return

        # Processa os comandos (importante para o prefixo !cmd funcionar em canais)
        await bot.process_commands(message)

    @bot.event
    async def on_command_error(ctx, error):
        # Loga erros de comando
        console.print(f"[bold red][DISCORD ERROR][/bold red] Erro no comando !{ctx.command}: {error}")
        if isinstance(error, commands.CommandNotFound):
            return # Ignora comandos não encontrados silenciosamente
        await ctx.send(f"❌ Erro: {error}")

    @bot.command(name="cmd")
    async def cmd(ctx, *, prompt):
        """Comando para enviar prompt para o Ollie via Discord."""
        await handle_discord_prompt(ctx, prompt)

    try:
        await bot.start(settings["discord_token"])
    except Exception as e:
        console.print(f"[red]Erro ao iniciar bot Discord: {e}[/red]")

async def speak(text):
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
            response = await asyncio.to_thread(requests.post, url, headers=headers, json=payload)
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
                audio_res = await asyncio.to_thread(requests.get, audio_url)
                audio_res.raise_for_status()
                audio_data = audio_res.content
                
                temp_file = os.path.join(DATA_DIR, "temp_voice.mp3")
                with open(temp_file, "wb") as f:
                    f.write(audio_data)

                # Reprodução
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.1)
                
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
            content = response['message']['content']
            
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

async def process_multi_step_task(messages, ollama_model, is_discord=False, ctx=None):
    """Processa uma tarefa que pode envolver múltiplas etapas de execução de comandos."""
    step_count = 0
    max_steps = 10
    final_response = ""

    while step_count < max_steps:
        full_response = ""
        show_thoughts = settings.get("show_thoughts", False)
        status_text = f"{AGENT_NAME} ({ollama_model}) pensando..."
        
        if is_discord:
            async with ctx.typing():
                response = await asyncio.to_thread(ollama.chat, model=ollama_model, messages=messages)
                full_response = response['message']['content']
        else:
            if show_thoughts:
                with Live(Text(status_text, style="bold yellow"), refresh_per_second=10) as live:
                    response_gen = await asyncio.to_thread(ollama.chat, model=ollama_model, messages=messages, stream=True)
                    for chunk in response_gen:
                        content = chunk['message']['content']
                        full_response += content
                        live.update(Text(f"Ollama respondendo: {full_response[-100:]}", style="italic cyan"))
            else:
                with console.status(f"[bold yellow]{status_text}[/bold yellow]"):
                    response = await asyncio.to_thread(ollama.chat, model=ollama_model, messages=messages)
                    full_response = response['message']['content']
        
        llm_response = full_response
        messages.append({'role': 'assistant', 'content': llm_response})
        
        # Processa configurações embutidas no texto
        if "# CONFIG: SHOW_THOUGHTS=True" in llm_response:
            settings["show_thoughts"] = True
            save_settings(settings)
            if not is_discord: console.print("[bold magenta]Modo de visualização de pensamentos ativado.[/bold magenta]")
        elif "# CONFIG: SHOW_THOUGHTS=False" in llm_response:
            settings["show_thoughts"] = False
            save_settings(settings)
            if not is_discord: console.print("[bold magenta]Modo de visualização de pensamentos desativado.[/bold magenta]")
        
        if "# CONFIG: TTS_ENABLED=True" in llm_response:
            settings["tts_enabled"] = True
            save_settings(settings)
            if not is_discord: console.print("[bold magenta]Saída de voz (TTS) ativada.[/bold magenta]")
        elif "# CONFIG: TTS_ENABLED=False" in llm_response:
            settings["tts_enabled"] = False
            save_settings(settings)
            if not is_discord: console.print("[bold magenta]Saída de voz (TTS) desativada.[/bold magenta]")
        
        user_name_match = re.search(r"# CONFIG: USER_NAME=(.*)", llm_response)
        if user_name_match:
            new_name = user_name_match.group(1).strip()
            settings["user_name"] = new_name
            save_settings(settings)
            if not is_discord: console.print(f"[bold magenta]Nome do usuário alterado para: {new_name}[/bold magenta]")

        command = extract_bash_command(llm_response)
        summary = extract_summary(llm_response)

        if command:
            step_count += 1
            if summary:
                if is_discord:
                    console.print(f"[bold magenta][DISCORD][/bold magenta] Etapa {step_count}: {summary}")
                    await ctx.send(f"⏳ **Etapa {step_count}:** {summary}")
                else:
                    console.print(f"[italic yellow]→ {summary}[/italic yellow]")
                    await speak(summary)
            
            if is_discord:
                console.print(f"[bold magenta][DISCORD][/bold magenta] Executando: `{command}`")
            else:
                console.print(f"[bold cyan]Executando (Etapa {step_count}):[/bold cyan] `{command}`")
            
            stdout, stderr, code = execute_command(command)
            result_msg = f"RESULTADO DA ETAPA {step_count}:\nSTDOUT: {stdout}\nSTDERR: {stderr}\nEXIT_CODE: {code}"
            
            if len(result_msg) > 2000:
                result_msg = result_msg[:1000] + "\n... (saída truncada por ser muito longa) ...\n" + result_msg[-1000:]
            
            messages.append({'role': 'user', 'content': result_msg})
            continue
        else:
            final_response = llm_response
            if not is_discord:
                console.print(Panel(Markdown(llm_response), border_style="green", title="Tarefa Concluída"))
                await speak(llm_response)
            break
            
    if step_count >= max_steps and not is_discord:
        console.print("[bold red]Aviso:[/bold red] Limite de etapas atingido.")
    
    return final_response, messages

async def chat():
    global memory
    # Inicia o bot do Discord se estiver habilitado e tiver token
    if settings.get("discord_enabled") and settings.get("discord_token"):
        asyncio.create_task(run_discord_bot())

    # Verifica atualizações ao iniciar e lida com a decisão do Agente
    update_info = check_for_updates()
    if update_info:
        await handle_update_decision(update_info)
    
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
            user_input = await asyncio.to_thread(console.input, f"[bold blue]{current_user}:[/bold blue] ")
            
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
                        response = await asyncio.to_thread(requests.get, url, headers=headers)
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
            
            # Chama o processador de tarefas multi-etapa
            ollama_model = settings.get("ollama_model", DEFAULT_MODEL)
            await process_multi_step_task(messages, ollama_model, is_discord=False)

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
                console.print("3. Chave API Murf.ai")
                console.print("4. Token do Bot Discord")
                console.print("5. Habilitar/Desabilitar Discord")
                console.print("6. Senha Sudo (Linux)")
                console.print("0. Sair e Salvar")
                
                opcao = console.input("\n[bold yellow]Opção: [/bold yellow]").strip()
                
                if opcao == "1":
                    settings["user_name"] = console.input(f"Novo nome (atual: {settings['user_name']}): ").strip() or settings["user_name"]
                elif opcao == "2":
                    settings["ollama_model"] = console.input(f"Novo modelo (atual: {settings['ollama_model']}): ").strip() or settings["ollama_model"]
                elif opcao == "3":
                    settings["murf_api_key"] = console.input(f"Nova chave Murf.ai (atual: {settings['murf_api_key'][:10]}...): ").strip() or settings["murf_api_key"]
                elif opcao == "4":
                    settings["discord_token"] = console.input(f"Novo Token Discord (atual: {settings['discord_token'][:10]}...): ").strip() or settings["discord_token"]
                elif opcao == "5":
                    estado = "habilitado" if settings["discord_enabled"] else "desabilitado"
                    confirm = console.input(f"Discord está {estado}. Deseja trocar? (s/n): ").lower().strip()
                    if confirm == 's':
                        settings["discord_enabled"] = not settings["discord_enabled"]
                elif opcao == "6":
                    if IS_WINDOWS:
                        console.print("[red]Sudo não é usado no Windows.[/red]")
                    else:
                        settings["sudo_password"] = console.input("Nova senha sudo: ").strip() or settings["sudo_password"]
                elif opcao == "0":
                    save_settings(settings)
                    console.print("[green]Configurações salvas![/green]")
                    sys.exit(0)
                
                save_settings(settings)

        # Iniciar bot em segundo plano
        if len(sys.argv) > 1 and sys.argv[1] == "start":
            # Verifica se já existe algo rodando ANTES de tentar iniciar outro
            if os.path.exists(LOCK_FILE):
                pid_active = False
                try:
                    with open(LOCK_FILE, "r") as f:
                        pid = int(f.read().strip())
                    if is_process_running(pid):
                        pid_active = True
                        console.print(f"[bold red]Erro:[/bold red] O {AGENT_NAME} já está rodando em segundo plano (PID: {pid}).")
                        console.print("[yellow]Use 'agent-ollama stop' para encerrar antes de iniciar novamente.[/yellow]")
                except (ValueError, IOError):
                    pass
                
                if pid_active:
                    sys.exit(1)

            if not settings.get("discord_token") or not settings.get("discord_enabled"):
                console.print("[bold red]Erro:[/bold red] Discord não está configurado ou habilitado. Use 'agent-ollama config' primeiro.")
                sys.exit(1)
            
            console.print(f"[bold green]Iniciando {AGENT_NAME} em segundo plano...[/bold green]")
            
            script_path = os.path.abspath(__file__)
            python_exe = sys.executable
            
            if IS_WINDOWS:
                # No Windows, usamos pythonw para não abrir janela de terminal
                # Se não houver pythonw, usamos python normal com flags de criação de processo
                pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
                if not os.path.exists(pythonw_exe):
                    pythonw_exe = python_exe
                
                # Redirecionamos a saída para o LOG_FILE no Windows também
                # (Isso é um pouco mais complexo no Windows sem abrir janela, mas possível via shell redirection)
                subprocess.Popen(
                    f'"{pythonw_exe}" "{script_path}" run-bot >> "{LOG_FILE}" 2>&1',
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                    close_fds=True
                )
            else:
                # No Linux, usamos nohup e redirecionamos saída
                with open(LOG_FILE, "a") as f:
                    subprocess.Popen(
                        [python_exe, script_path, "run-bot"],
                        stdout=f,
                        stderr=f,
                        preexec_fn=os.setpgrp
                    )
            
            console.print("[bold cyan]Ollie agora está rodando em segundo plano. Você pode fechar este terminal.[/bold cyan]")
            sys.exit(0)

        # Modo apenas bot (usado pelo comando 'start')
        if len(sys.argv) > 1 and sys.argv[1] == "run-bot":
            check_instance_lock()
            async def run_only_bot():
                await run_discord_bot()
                while True: # Mantém o processo vivo
                    await asyncio.sleep(3600)
            asyncio.run(run_only_bot())
            sys.exit(0)
        
        # Comando para acompanhar os logs em tempo real
        if len(sys.argv) > 1 and sys.argv[1] == "log":
            if not os.path.exists(LOG_FILE):
                console.print(f"[bold red]Erro:[/bold red] Arquivo de log não encontrado em {LOG_FILE}")
                sys.exit(1)
            
            console.print(f"[bold cyan]Acompanhando logs de {AGENT_NAME} (Ctrl+C para sair):[/bold cyan]\n")
            
            try:
                # No Windows e Linux, podemos ler o arquivo continuamente
                with open(LOG_FILE, "r") as f:
                    # Vai para o final do arquivo primeiro
                    f.seek(0, os.SEEK_END)
                    while True:
                        line = f.readline()
                        if not line:
                            time.sleep(0.1)
                            continue
                        print(line, end="")
            except KeyboardInterrupt:
                console.print("\n[bold yellow]Saindo do log...[/bold yellow]")
                sys.exit(0)

        # Comando para encerrar o bot em segundo plano
        if len(sys.argv) > 1 and sys.argv[1] == "stop":
            console.print(f"[bold yellow]Encerrando instâncias do {AGENT_NAME}...[/bold yellow]")
            if IS_WINDOWS:
                # No Windows, usamos taskkill para matar processos pythonw que estão rodando o script
                subprocess.run(["taskkill", "/F", "/IM", "pythonw.exe", "/T"], capture_output=True)
                # Também tentamos matar pelo nome do script para garantir
                subprocess.run(["powershell", "-Command", f"Get-Process | Where-Object {{ $_.CommandLine -like '*{AGENT_NAME}*' }} | Stop-Process -Force"], capture_output=True)
            else:
                # No Linux, usamos pkill
                subprocess.run(["pkill", "-f", "agent-ollama.py"])
            
            # Remove o lock file se existir (já que estamos forçando a parada)
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)

            console.print("[bold green]Instâncias encerradas![/bold green]")
            sys.exit(0)

        # Se chegou aqui, é o modo interativo normal
        check_instance_lock()
        asyncio.run(chat())
    except KeyboardInterrupt:
        pass
    finally:
        pygame.mixer.quit()
