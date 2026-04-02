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

O comando `agent-ollama` inicia o servidor web do app.

Se preferir, também é possível iniciar diretamente o servidor com:
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
Você pode ajustar o nome do usuário, modelo, TTS e voz diretamente pela interface web.

### 🌐 App Web
O projeto agora roda como um app web. Basta iniciar o servidor com:
```bash
agent-ollama
```

E então abrir o navegador em:
```text
http://127.0.0.1:5000
```

Se você quiser expor o servidor para outros dispositivos na rede:
```bash
agent-ollama --host 0.0.0.0 --port 5000
```

Também é possível usar o servidor diretamente em `pc_app`:
```bash
cd pc_app
python3 server.py --host 0.0.0.0 --port 5000
```

---

## 📖 Como Usar

### Execução de Qualquer Lugar
Após o setup, você pode iniciar o app web com:
```bash
agent-ollama
```

Em seguida, abra no navegador:
```text
http://127.0.0.1:5000
```

A interface web permite configurar:
- nome do usuário
- modelo do Ollama
- opções de TTS
- voz e chave ElevenLabs
- exibição de pensamentos

## 🛡️ Segurança

Este assistente executa comandos no seu sistema. 
- **Windows**: Ele não eleva privilégios sozinho. Se precisar de permissão de admin, abra o terminal como administrador.
- **Linux**: Pode usar `sudo` se a senha estiver configurada.

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
