#!/bin/bash

# Detecta automaticamente o diretório onde este script está (mesmo com espaços)
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
PROJECT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

# Navega para o diretório do projeto
cd "$PROJECT_DIR"

# Verifica se o ambiente virtual existe
if [ -d "venv" ]; then
    # Ativa o venv e roda o script python
    source venv/bin/activate
    python3 ollama_admin.py
else
    echo "Erro: Ambiente virtual (venv) não encontrado em $PROJECT_DIR"
    echo "Certifique-se de ter criado o venv com: python3 -m venv venv"
    exit 1
fi
