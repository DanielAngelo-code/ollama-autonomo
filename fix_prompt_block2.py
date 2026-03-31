from pathlib import Path
path = Path('agent-ollama.py')
text = path.read_text(encoding='utf-8')
lines = text.splitlines(True)
for i, line in enumerate(lines):
    if line.startswith('   - Chave ElevenLabs: Use '):
        lines[i] = '   - Chave ElevenLabs: Use ```bash\n# CONFIG: ELEVENLABS_API_KEY=SuaChaveAqui\n``` para configurar a API de voz.\n'
        # remove any following broken lines that begin with # CONFIG: ELEVENLABS_API_KEY
        if i + 1 < len(lines) and lines[i+1].startswith('# CONFIG: ELEVENLABS_API_KEY='):
            del lines[i+1]
        break
path.write_text(''.join(lines), encoding='utf-8')
print('fixed')
