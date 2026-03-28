import ollama
import subprocess
import sys
import re
import requests
import json
import os
import time
import pygame
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Configurações Murf.ai
MURF_API_KEY = "ap2_6ca244bd-f1c0-4414-af05-d862ab93ec11"
MURF_VOICE_ID = "benicio" # Removido acento para compatibilidade com API
MURF_STYLE = "Conversational"
MURF_MODEL_VERSION = "GEN2"

console = Console()

# Inicializa mixer de áudio
pygame.mixer.init()

def speak(text):
    """Envia o texto para murf.ai e reproduz o áudio resultante."""
    if not text.strip():
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
            response.raise_for_status()
            audio_url = response.json().get("audioUrl")

            if audio_url:
                # Download do áudio temporário
                audio_data = requests.get(audio_url).content
                temp_file = "temp_voice.mp3"
                with open(temp_file, "wb") as f:
                    f.write(audio_data)

                # Reprodução
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                
                pygame.mixer.music.unload()
                os.remove(temp_file)
    except Exception as e:
        console.print(f"[dim red](Erro ao gerar voz: {e})[/dim red]")

SYSTEM_PROMPT = """
Você é um administrador de servidor Ubuntu autônomo e proativo. 
Sua missão é resolver as tarefas solicitadas pelo usuário de ponta a ponta.

CONTEXTO DO SERVIDOR:
- Hardware: O servidor possui uma GPU AMD Radeon RX 580.
- Gráficos/Computação: Utiliza Vulkan para aceleração.
- LLM: O Ollama está rodando e deve aproveitar a aceleração da GPU se configurado corretamente.

DIRETRIZES DE AUTONOMIA:
1. **Raciocínio Multi-etapa**: Planeje e execute uma etapa por vez.
2. **Execução de Comandos**: Sempre que for executar um comando, forneça primeiro uma breve descrição do que está fazendo seguido pelo comando BASH em um bloco de código: ```bash\ncomando\n```.
3. **Análise de Resultados**: Analise STDOUT/STDERR para decidir o próximo passo.
4. **Conclusão**: Quando terminar, forneça uma resposta final clara sem blocos de código.
"""

def extract_bash_command(response):
    """Extrai o comando bash de dentro de blocos de código markdown."""
    pattern = r"```(?:bash)?\n(.*?)\n```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def extract_summary(response):
    """Extrai o texto antes do bloco de código como resumo da ação."""
    text = re.sub(r"```(?:bash)?\n.*?\n```", "", response, flags=re.DOTALL).strip()
    return text

def execute_command(command):
    """Executa o comando no terminal e retorna a saída."""
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
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

def chat():
    # Verifica atualizações ao iniciar
    check_for_updates()
    
    # Verifica se o Ollama está acessível e se o modelo existe
    try:
        models_response = ollama.list()
        # O retorno de ollama.list() pode variar dependendo da versão da biblioteca
        # Algumas versões retornam um objeto com atributo 'models', outras um dicionário
        models_list = []
        if isinstance(models_response, dict) and 'models' in models_response:
            models_list = models_response['models']
        elif hasattr(models_response, 'models'):
            models_list = models_response.models
        
        model_names = []
        for m in models_list:
            if isinstance(m, dict) and 'name' in m:
                model_names.append(m['name'])
            elif hasattr(m, 'model'): # Algumas versões usam .model em vez de .name
                model_names.append(m.model)
            elif hasattr(m, 'name'):
                model_names.append(m.name)

        if 'llama3:latest' not in model_names and 'llama3' not in model_names:
            console.print("[bold yellow]Aviso:[/bold yellow] Modelo 'llama3' não encontrado localmente.")
            with console.status("[bold cyan]Baixando llama3 (isso pode demorar)...[/bold cyan]"):
                ollama.pull('llama3')
                console.print("[bold green]Modelo llama3 baixado com sucesso![/bold green]")
    except Exception as e:
        console.print(Panel(f"[bold red]Erro de conexão com o Ollama:[/bold red]\n{e}\n\nCertifique-se de que o Ollama está rodando no servidor.", title="Erro Crítico", border_style="red"))
        return

    console.print(Panel("[bold green]Ollama Autônomo V2[/bold green]\nModo multi-etapa com atualizações e voz ativados.", title="Sistema Ativo"))
    
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]

    while True:
        try:
            user_input = console.input("[bold blue]Você:[/bold blue] ")
            
            if user_input.lower() in ["sair", "exit", "quit"]:
                break

            messages.append({'role': 'user', 'content': user_input})
            
            step_count = 0
            max_steps = 10

            while step_count < max_steps:
                with console.status(f"[bold yellow]Ollama pensando...[/bold yellow]"):
                    response = ollama.chat(model='llama3', messages=messages)

                llm_response = response['message']['content']
                messages.append({'role': 'assistant', 'content': llm_response})
                
                command = extract_bash_command(llm_response)
                summary = extract_summary(llm_response)

                if command:
                    step_count += 1
                    if summary:
                        console.print(f"[italic yellow]→ {summary}[/italic yellow]")
                    
                    console.print(f"[bold cyan]Executando (Etapa {step_count}):[/bold cyan] `{command}`")
                    stdout, stderr, code = execute_command(command)
                    
                    result_msg = f"RESULTADO DA ETAPA {step_count}:\nSTDOUT: {stdout}\nSTDERR: {stderr}\nEXIT_CODE: {code}"
                    messages.append({'role': 'user', 'content': result_msg})
                    continue
                else:
                    console.print(Panel(Markdown(llm_response), border_style="green", title="Tarefa Concluída"))
                    # Fala a resposta final
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
