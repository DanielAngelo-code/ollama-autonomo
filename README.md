# Ollama Autônomo V2 🤖🚀

Gerencie seu servidor Ubuntu através de conversas em linguagem natural com o Ollama, diretamente via SSH. Este assistente é capaz de executar comandos, analisar resultados e realizar tarefas multi-etapa de forma autônoma.

![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-LLM-blue?style=for-the-badge)
![AMD RX 580](https://img.shields.io/badge/AMD%20RX%20580-Vulkan-ED1C24?style=for-the-badge&logo=amd&logoColor=white)

## ✨ Funcionalidades

- **Autonomia Total**: A IA executa comandos, lê a saída e decide o próximo passo até completar a tarefa.
- **Feedback em Tempo Real**: Mostra o que está pensando e fazendo antes de cada execução.
- **Otimizado para AMD**: Configurado para reconhecer hardware AMD RX 580 com suporte a Vulkan.
- **Interface Rica**: Utiliza a biblioteca `rich` para um terminal organizado e legível.
- **Segurança**: Inclui limites de etapas (max 10) para evitar loops e consumo excessivo.
- **Persistência de Dados**: Pasta `/data` dedicada para armazenar chaves de API, configurações de modelo e memória de longo prazo, protegida contra atualizações do GitHub.

## 🛠️ Pré-requisitos

1. **Ollama**: Instalado e rodando.
2. **Modelo Llama 3**: `ollama pull llama3`.
3. **Hardware**: Otimizado para Ubuntu com GPU AMD RX 580 (Vulkan).

## 🚀 Instalação e Comando Global

1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/ollama-autonomo.git
   cd ollama-autonomo
   ```

2. Crie e ative um ambiente virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configurar Comando Global**:
   Para chamar o assistente de qualquer lugar usando apenas `ollama-admin`:
   ```bash
   # Dê permissão ao script de entrada
   chmod +x ollama-admin.sh
   
   # Crie um link simbólico no seu bin (as aspas são importantes se o seu caminho tiver espaços!)
   sudo ln -s "$(pwd)/ollama-admin.sh" /usr/local/bin/ollama-admin
   ```

## 📖 Como Usar

### Execução Global
```bash
ollama-admin
```

### Comandos Especiais
- `/model <nome-do-modelo>`: Troca o modelo do Ollama em tempo real (ex: `/model llama3:8b`). O modelo deve estar baixado.
- `/voices`: Lista todas as vozes disponíveis para o Murf.ai no idioma pt-BR, mostrando seus IDs.
- `/setvoice <ID>`: Altera a voz do assistente usando o ID obtido no comando anterior.
- `/setsudo <senha>`: Salva sua senha do usuário para que a IA possa executar comandos `sudo` automaticamente sem te interromper.
- `/clearmem`: Limpa a memória persistente (`memory.json`) e reinicia o histórico da conversa atual.
- `sair`, `exit` ou `quit`: Encerra o assistente.

### Atualizações Automáticas
O sistema verifica por atualizações no GitHub toda vez que você inicia o `ollama-admin`. Se houver uma nova versão no repositório, ele fará o `git pull` automaticamente.

### Integração SSH (Modo "Shell AI")
Para que o assistente inicie automaticamente ao logar via SSH, adicione ao seu `~/.bashrc`:

```bash
ollama-admin && exit
```

## 🛡️ Segurança e Responsabilidade

Este script possui **autonomia para executar comandos BASH**. 
- Não há confirmação manual (s/n) por padrão.
- Use com cautela em ambientes de produção.
- O autor não se responsabiliza por danos causados por comandos sugeridos pelo LLM.

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
