from pathlib import Path
path = Path('agent-ollama.py')
lines = path.read_text(encoding='utf-8').splitlines(True)
for i, line in enumerate(lines):
    if 'Voz (TTS)' in line or 'Chave ElevenLabs' in line or 'Nome do Usuário' in line:
        print(i, repr(line))
