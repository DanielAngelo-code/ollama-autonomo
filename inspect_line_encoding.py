from pathlib import Path
lines = Path('agent-ollama.py').read_text(encoding='utf-8').splitlines(True)
for i in range(431, 436):
    line = lines[i]
    print(i, [hex(ord(c)) for c in line])
    print(repr(line))
