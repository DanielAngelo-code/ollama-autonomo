#!/bin/bash

# Agent Ollama - Setup e Início (Linux)

# 0. Define o diretório do projeto de forma robusta
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$INSTALL_DIR"

echo -e "\e[36m--- Configurando Agent Ollie ---\e[0m"

# 1. Detecta Python 3
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "\e[31mErro: Python 3 não encontrado. Por favor, instale o Python 3.\e[0m"
    exit 1
fi

# 2. Cria ou atualiza o ambiente virtual local
VENV_DIR="$INSTALL_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "\e[36mCriando ambiente virtual .venv...\e[0m"
    $PYTHON_CMD -m venv "$VENV_DIR"
fi

VENV_PYTHON="$VENV_DIR/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    echo -e "\e[31mErro: python do venv não encontrado.\e[0m"
    exit 1
fi

echo -e "\e[36mInstalando dependências no venv...\e[0m"
$VENV_PYTHON -m pip install --upgrade pip
$VENV_PYTHON -m pip install -r requirements.txt

echo -e "\e[36mValidando arquivos principais (syntax check)...\e[0m"
if ! "$VENV_PYTHON" -m py_compile "$INSTALL_DIR/pc_app/server.py" "$INSTALL_DIR/agent-ollama.py"; then
    echo -e "\e[31mErro: falha de sintaxe detectada em arquivos do projeto.\e[0m"
    echo -e "\e[31mDica: rode 'git pull' e execute o setup novamente.\e[0m"
    exit 1
fi

# 3. Cria comando global 'agent-ollama' em ~/.local/bin
USER_BIN="$HOME/.local/bin"
mkdir -p "$USER_BIN"
WRAPPER_PATH="$USER_BIN/agent-ollama"

echo -e "\e[36mConfigurando comando global...\e[0m"
cat > "$WRAPPER_PATH" <<EOF
#!/bin/bash
cd "$INSTALL_DIR"
"$VENV_PYTHON" "$INSTALL_DIR/agent-ollama.py" "\$@"
EOF
chmod +x "$WRAPPER_PATH"

SERVER_WRAPPER_PATH="$USER_BIN/agent-ollama-server"
cat > "$SERVER_WRAPPER_PATH" <<EOF
#!/bin/bash
cd "$INSTALL_DIR/pc_app"
"$VENV_PYTHON" "$INSTALL_DIR/pc_app/server.py" "\$@"
EOF
chmod +x "$SERVER_WRAPPER_PATH"

ALIAS_WRAPPER_PATH="$USER_BIN/ollama-autonomos"
ln -sf "$SERVER_WRAPPER_PATH" "$ALIAS_WRAPPER_PATH"

SINGULAR_ALIAS_WRAPPER_PATH="$USER_BIN/ollama-autonomo"
ln -sf "$SERVER_WRAPPER_PATH" "$SINGULAR_ALIAS_WRAPPER_PATH"

if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
    SHELL_RC="$HOME/.bashrc"
    if [ -n "$ZSH_VERSION" ] && [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    fi
    if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$SHELL_RC" 2> /dev/null; then
        echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
        echo -e "\e[33mAdicionando ~/.local/bin ao PATH em $SHELL_RC.\e[0m"
    fi
    echo -e "\e[33mFeche e reabra o terminal ou rode: source $SHELL_RC\e[0m"
fi

echo -e "\n\e[32m[SUCESSO] Setup concluído!\e[0m"
echo -e "-------------------------------------------------------"
echo -e "\e[33mCOMANDO GLOBAL ATIVADO: agent-ollama\e[0m"
echo -e "-------------------------------------------------------"
echo -e "O comando agora usa automaticamente o venv do projeto, sem ativação manual.\e[0m"
echo -e "Iniciando agora...\n"

# 4. Inicia o projeto pelo venv
"$VENV_PYTHON" agent-ollama.py
