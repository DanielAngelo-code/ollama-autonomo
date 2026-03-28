import ollama
import subprocess
import sys
import re
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

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

def chat():
    console.print(Panel("[bold green]Ollama Autônomo V2[/bold green]\nModo multi-etapa com atualizações em tempo real.", title="Sistema Ativo"))
    
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
                    break
            
            if step_count >= max_steps:
                console.print("[bold red]Aviso:[/bold red] Limite de etapas atingido.")

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]Erro:[/bold red] {e}")

if __name__ == "__main__":
    chat()
