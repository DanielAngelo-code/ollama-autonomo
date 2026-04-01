# Agent Ollama PC App

Este módulo adiciona um app local para rodar no seu PC com interface web.
Ele inicia um servidor HTTP local que permite enviar prompts ao Ollama, ver a resposta em texto e reproduzir o áudio de saída.

## O que o app oferece

- interface gráfica no navegador
- configuração de nome, modelo, TTS e voz
- geração de texto a partir do modelo Ollama
- saída de áudio em WAV para reprodução local
- opção de usar `pyttsx3` ou `ElevenLabs` como motor de áudio

## Instalação

1. Instale as dependências do projeto:

```powershell
python -m pip install -r requirements.txt
```

2. Certifique-se de que o Ollama esteja instalado e rodando localmente.

3. Execute o servidor:

```powershell
python pc_app/server.py
```

4. Abra no navegador:

```
http://127.0.0.1:5000
```

## Configuração

Use a tela de configurações para ajustar:

- `Nome do usuário`
- `Modelo Ollama`
- `Habilitar TTS`
- `Motor TTS` (local ou ElevenLabs)
- `Voz TTS`
- `Chave ElevenLabs`
- `Mostrar pensamentos`

Os ajustes são salvos em `data/settings.json`.

## Observações

- O servidor é apenas um backend local e não implementa um chat em tempo real. Ele serve como um ponto de interação com o LLM através do navegador.
- Se usar ElevenLabs, defina a chave no campo `Chave ElevenLabs`.
