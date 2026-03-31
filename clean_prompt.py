from pathlib import Path
path = Path('agent-ollama.py')
text = path.read_text(encoding='utf-8')
lines = text.splitlines(True)
new_lines = [line for line in lines if line not in ['` para configurar a API de voz.\n', '` para configurar a API de voz.\r\n']]
path.write_text(''.join(new_lines), encoding='utf-8')
print('removed', len(lines) - len(new_lines))
