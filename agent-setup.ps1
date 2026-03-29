# Agent Ollama - Setup e Início (Windows)

# 1. Verifica se o Python está instalado
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Erro: Python não encontrado. Por favor, instale o Python." -ForegroundColor Red
    exit
}

# 2. Cria ambiente virtual se não existir
if (!(Test-Path "venv")) {
    Write-Host "Criando ambiente virtual..." -ForegroundColor Cyan
    python -m venv venv
}

# 3. Instala dependências
Write-Host "Instalando dependências..." -ForegroundColor Cyan
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# 4. Cria comando global 'agent-ollama' para o usuário atual (opcional, mas recomendado)
$BinPath = "$HOME\AppData\Local\Microsoft\WindowsApps"
$ScriptPath = Get-Location
$BatContent = "@echo off`ncd /d `"$ScriptPath`"`n`"$ScriptPath\venv\Scripts\python.exe`" `"$ScriptPath\agent-ollama.py`" %*"
$BatContent | Out-File -FilePath "$BinPath\agent-ollama.bat" -Encoding ASCII

Write-Host "`nSetup concluído!" -ForegroundColor Green
Write-Host "Agora você pode iniciar o projeto de qualquer lugar digitando: agent-ollama" -ForegroundColor Yellow
Write-Host "Iniciando agora...`n" -ForegroundColor Cyan

# 5. Inicia o projeto
.\venv\Scripts\python.exe agent-ollama.py
