from pathlib import Path
path = Path('agent-ollama.py')
text = path.read_text(encoding='utf-8')
start = text.index('   - Voz (TTS): Use ```bash\n# CONFIG: TTS_ENABLED=True\n``` ou False.')
end = text.index('   - Nome do Usuário: Use ```bash\n# CONFIG: USER_NAME=NovoNome\n``` para mudar como você chama o usuário.', start)
old = text[start:end]
new_block = (
    '   - Voz (TTS): Use ```bash\n'
    '# CONFIG: TTS_ENABLED=True\n'
    '``` ou False.\n'
    '   - Chave ElevenLabs: Use ```bash\n'
    '# CONFIG: ELEVENLABS_API_KEY=SuaChaveAqui\n'
    '``` para configurar a API de voz.\n'
)
text = text[:start] + new_block + text[end:]
path.write_text(text, encoding='utf-8')
print('fixed')
