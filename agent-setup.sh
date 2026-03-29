#!/bin/bash

# Agent Ollama - Setup e Início (Linux)

# 1. Verifica se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "Erro: Python 3 não encontrado. Por favor, instale o Python 3."
    exit 1
fi

# 2. Cria ambiente virtual se não existir
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
fi

# 3. Instala dependências
echo "Instalando dependências..."
./venv/bin/python3 -m pip install -r requirements.txt

# 4. Cria comando global 'agent-ollama' (link simbólico)
INSTALL_DIR=$(pwd)
echo "Configurando comando global..."
sudo ln -sf "$INSTALL_DIR/venv/bin/python3" /usr/local/bin/agent-ollama-python
sudo bash -c "cat <<EOF > /usr/local/bin/agent-ollama
#!/bin/bash
cd $INSTALL_DIR
./venv/bin/python3 agent-ollama.py \"\$@\"
EOF"
sudo chmod +x /usr/local/bin/agent-ollama

echo -e "\nSetup concluído!"
echo "Agora você pode iniciar o projeto de qualquer lugar digitando: agent-ollama"
echo "Iniciando agora..."

# 5. Inicia o projeto
./venv/bin/python3 agent-ollama.py
