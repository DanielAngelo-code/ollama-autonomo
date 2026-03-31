# Agent Ollama 🤖🚀

<p align="center">
  <img src="logo.svg" width="200" alt="Agent Ollama Logo">
</p>

Assistente de administração multiplataforma (Windows/Linux) que utiliza o Ollama para gerenciar seu sistema através de linguagem natural. Capaz de executar comandos PowerShell/Bash, analisar resultados e realizar tarefas multi-etapa de forma autônoma.

![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-LLM-blue?style=for-the-badge)

## ✨ Funcionalidades

- **Autonomia Multiplataforma**: Executa comandos PowerShell no Windows e Bash no Linux.
- **Instalação Simples**: Script de setup único que configura o ambiente e cria o comando global.
- **Feedback em Tempo Real**: Mostra o que está pensando e fazendo antes de cada execução.
- **Voz Murf.ai**: Saída de áudio de alta qualidade integrada (opcional).
- **Persistência de Dados**: Pasta `/data` dedicada para chaves de API, configurações e memória de longo prazo.

## 🛠️ Pré-requisitos

1. **Ollama**: Instalado e rodando localmente ou no servidor.
2. **Modelo Llama 3**: `ollama pull llama3` (ou seu modelo preferido).
3. **Python 3.8+**: Instalado no sistema. Não é necessário criar ou ativar um `venv`.

## 🚀 Instalação Rápida (Recomendado)

O projeto agora possui um fluxo de inicialização automática. Basta executar o script principal; ele verifica se já foi inicializado, instala as dependências se necessário e inicia o bot.

### Usar diretamente com Python:
1. Abra o terminal na pasta do projeto.
2. Execute:
   ```powershell
   python agent-ollama.py
   ```

Se faltar dependências, o script fará o setup automaticamente e reiniciará.

### No Windows (PowerShell) para criar um comando global:
1. Abra o PowerShell como Administrador.
2. Navegue até a pasta do projeto e execute:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force; .\agent-setup.ps1
   ```

### No Linux (Bash):
1. Navegue até a pasta do projeto e execute:
   ```bash
   chmod +x agent-setup.sh
   ./agent-setup.sh
   ```

### Configurações Adicionais:
Você pode configurar chaves de API e outras preferências usando o comando:
```bash
agent-ollama config
```

---

## 📖 Como Usar

### Execução de Qualquer Lugar
Após o setup, você pode simplesmente digitar em qualquer terminal:
```bash
agent-ollama
```

### Comandos Especiais
- `/model <nome>`: Troca o modelo (ex: `/model llama3`).
- `/voices`: Lista vozes Murf.ai disponíveis (pt-BR).
- `/setvoice <ID>`: Altera a voz do assistente.
- `/setsudo <senha>`: (Linux apenas) Salva a senha para comandos `sudo`.
- `/clearmem`: Limpa a memória e o histórico.
- `sair`, `exit` ou `quit`: Encerra o assistente.

## 🛡️ Segurança

Este assistente executa comandos no seu sistema. 
- **Windows**: Ele não eleva privilégios sozinho. Se precisar de permissão de admin, abra o terminal como administrador.
- **Linux**: Pode usar `sudo` se a senha estiver configurada.

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
