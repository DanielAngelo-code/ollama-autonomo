#!/bin/bash

# Agent Ollama - Setup e Início (Linux)

# 0. Define o diretório do projeto de forma robusta
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$INSTALL_DIR"

echo -e "\e[36m--- Configurando Agent Ollie ---\e[0m"

# 1. Verifica se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "\e[31mErro: Python 3 não encontrado. Por favor, instale o Python 3.\e[0m"
    exit 1
fi

# 2. Instala dependências no usuário sem usar venv
echo -e "[36mInstalando dependências no Python do sistema...[0m"
python3 -m pip install --user --upgrade pip
python3 -m pip install --user -r requirements.txt

# 3. Cria comando global 'agent-ollama'
echo -e "\e[36mConfigurando acesso global...\e[0m"
PYTHON_EXE="python3"
SCRIPT_PY="$INSTALL_DIR/agent-ollama.py"

# Cria o executável em /usr/local/bin
sudo bash -c "cat <<EOF > /usr/local/bin/agent-ollama
#!/bin/bash
cd $INSTALL_DIR
$PYTHON_EXE $SCRIPT_PY \"\$@\"
EOF"
sudo chmod +x /usr/local/bin/agent-ollama

echo -e "\n\e[32m[SUCESSO] Setup concluído!\e[0m"
echo -e "-------------------------------------------------------"
echo -e "\e[33mCOMANDO GLOBAL ATIVADO: agent-ollama\e[0m"
echo -e "-------------------------------------------------------"
echo -e "DICA: Agora você pode usar o comando em qualquer terminal."
echo -e "Iniciando agora...\n"

# 4. Inicia o projeto
python3 agent-ollama.py
