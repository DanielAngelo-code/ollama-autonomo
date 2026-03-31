# Agent Ollama - Setup e Início (Windows)

# 0. Define o diretório do projeto de forma robusta
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (!$PSScriptRoot) { $PSScriptRoot = Get-Location }
Set-Location $PSScriptRoot

Write-Host "--- Configurando Agent Ollie (Acesso Global) ---" -ForegroundColor Cyan

# 1. Verifica se o Python está instalado
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Erro: Python não encontrado. Por favor, instale o Python." -ForegroundColor Red
    exit
}

# 2. Instala dependências no usuário sem usar venv
Write-Host "Instalando dependências no Python do sistema..." -ForegroundColor Cyan
python -m pip install --user --upgrade pip
python -m pip install --user -r requirements.txt

# 3. Cria comando global 'agent-ollama' em uma pasta dedicada
Write-Host "Configurando comando global no PATH..." -ForegroundColor Cyan

# Cria uma pasta 'bin' dentro do projeto para o executável
$GlobalBinPath = "$PSScriptRoot\bin"
if (!(Test-Path $GlobalBinPath)) {
    New-Item -ItemType Directory -Path $GlobalBinPath | Out-Null
}

$PythonExe = "python"
$ScriptPy = "$PSScriptRoot\agent-ollama.py"

# Cria o arquivo .bat que aponta para o Python do sistema
$BatContent = "@echo off`ncd /d `"$PSScriptRoot`"`n`"$PythonExe`" `"$ScriptPy`" %*"
$BatPath = "$GlobalBinPath\agent-ollama.bat"
$BatContent | Out-File -FilePath $BatPath -Encoding ASCII -Force

# Adiciona a pasta 'bin' ao PATH do usuário PERMANENTEMENTE
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$GlobalBinPath*") {
    Write-Host "Adicionando o projeto ao PATH do seu Windows..." -ForegroundColor Cyan
    $NewPath = "$GlobalBinPath;$UserPath"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    
    # Atualiza a sessão atual do PowerShell
    $env:Path = "$GlobalBinPath;$env:Path"
}

Write-Host "`n[SUCESSO] Setup concluído!" -ForegroundColor Green
Write-Host "-------------------------------------------------------"
Write-Host "O comando 'agent-ollama' agora pode ser usado em QUALQUER lugar," -ForegroundColor Yellow
Write-Host "sem precisar estar nesta pasta." -ForegroundColor Yellow
Write-Host "-------------------------------------------------------"
Write-Host "IMPORTANTE: Feche este terminal e abra um NOVO para testar." -ForegroundColor White
Write-Host "Iniciando agora para testar...`n" -ForegroundColor Cyan

# 5. Inicia o projeto
& "$BatPath"
