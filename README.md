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
- **Voz ElevenLabs local**: Saída de áudio gerada localmente com ElevenLabs (opcional).
- **Persistência de Dados**: Pasta `/data` dedicada para chaves de API, configurações e memória de longo prazo.

## 🛠️ Pré-requisitos

1. **Ollama**: Instalado e rodando localmente ou no servidor.
2. **Modelo Llama 3**: `ollama pull llama3` (ou seu modelo preferido).
3. **Python 3.8+**: Instalado no sistema. Não é necessário criar ou ativar um `venv`.
4. **ElevenLabs TTS** (opcional): se usar o SDK ElevenLabs remoto, defina `ELEVENLABS_API_KEY` no ambiente.

## 🚀 Instalação Rápida (Recomendado)

O projeto agora possui um fluxo de inicialização automática. Basta executar o script principal; ele verifica se já foi inicializado, instala as dependências se necessário e inicia o bot.

### Setup automático com venv e comando global
1. Abra o terminal na pasta do projeto.
2. Execute o script de setup do seu sistema:
   - Windows:
     ```powershell
     Set-ExecutionPolicy Bypass -Scope Process -Force; .\agent-setup.ps1
     ```
   - Ubuntu/Linux:
     ```bash
     chmod +x agent-setup.sh
     ./agent-setup.sh
     ```

O setup cria um ambiente virtual `.venv`, instala as dependências dentro dele e cria os comandos globais `agent-ollama`, `agent-ollama-server` e `ollama-autonomos`.

### Usar de qualquer lugar
Após o setup, basta abrir um novo terminal e rodar:
```bash
agent-ollama
```

Para iniciar o servidor do app PC a partir de qualquer lugar:
```bash
agent-ollama-server --host 0.0.0.0 --port 5000
```

Ou use o alias:
```bash
ollama-autonomos --host 0.0.0.0 --port 5000
```

No Linux, se `~/.local/bin` não estiver no PATH, feche e reabra o terminal ou rode:
```bash
source ~/.bashrc
```
### No Linux (Bash):
1. Navegue até a pasta do projeto e execute:
   ```bash
   chmod +x agent-setup.sh
   ./agent-setup.sh
   ```

### Configurações Adicionais:
Você pode configurar a voz ElevenLabs local e outras preferências usando o comando:
```bash
agent-ollama config
```

### 🖥️ App PC com Interface
O projeto também inclui um app local com servidor web em `pc_app/server.py`.
Basta rodar no servidor Ubuntu ou no dispositivo onde o Ollama está instalado:
```bash
cd pc_app
python3 server.py --host 0.0.0.0 --port 5000
```

Então abra no navegador do seu Windows PC usando o IP do servidor:
```text
http://<IP-do-servidor>:5000
```

Se preferir, também é possível usar variáveis de ambiente:
```bash
APP_HOST=0.0.0.0 APP_PORT=5000 python3 server.py
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
- `/voices`: Lista vozes ElevenLabs locais disponíveis.
- `/setvoice <nome_da_voz>`: Altera a voz do assistente.
- `/setapikey <sua_chave>`: Salva e recarrega a chave ElevenLabs API.
- `/setsudo <senha>`: (Linux apenas) Salva a senha para comandos `sudo`.
- `/clearmem`: Limpa a memória e o histórico.
- `sair`, `exit` ou `quit`: Encerra o assistente.

## 🛡️ Segurança

Este assistente executa comandos no seu sistema. 
- **Windows**: Ele não eleva privilégios sozinho. Se precisar de permissão de admin, abra o terminal como administrador.
- **Linux**: Pode usar `sudo` se a senha estiver configurada.

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
