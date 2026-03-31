# Agent Ollama - Setup e Início (Windows)

# 0. Define o diretório do projeto de forma robusta
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (!$PSScriptRoot) { $PSScriptRoot = Get-Location }
Set-Location $PSScriptRoot

Write-Host "--- Configurando Agent Ollie (Acesso Global) ---" -ForegroundColor Cyan

# 1. Verifica se o Python está instalado
$PythonExe = $null
$PythonArgs = @()
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonExe = "py"
    $PythonArgs = @("-3")
}
if (-not $PythonExe) {
    Write-Host "Erro: Python não encontrado. Por favor, instale o Python 3." -ForegroundColor Red
    exit 1
}

# 2. Cria ou atualiza o ambiente virtual local
$VenvPath = Join-Path $PSScriptRoot ".venv"
if (!(Test-Path $VenvPath)) {
    Write-Host "Criando ambiente virtual .venv..." -ForegroundColor Cyan
    & $PythonExe @($PythonArgs + @("-m", "venv", $VenvPath))
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
if (!(Test-Path $VenvPython)) {
    Write-Host "Erro: Python do venv não encontrado." -ForegroundColor Red
    exit 1
}

Write-Host "Instalando dependências no venv..." -ForegroundColor Cyan
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

# 3. Cria comando global 'agent-ollama' em uma pasta dedicada
Write-Host "Configurando comando global no PATH..." -ForegroundColor Cyan
$GlobalBinPath = Join-Path $PSScriptRoot "bin"
if (!(Test-Path $GlobalBinPath)) {
    New-Item -ItemType Directory -Path $GlobalBinPath | Out-Null
}

$ScriptPy = Join-Path $PSScriptRoot "agent-ollama.py"
$BatPath = Join-Path $GlobalBinPath "agent-ollama.bat"
$BatContent = "@echo off`ncd /d `"$PSScriptRoot`"`n`"$VenvPython`" `"$ScriptPy`" %*"
$BatContent | Out-File -FilePath $BatPath -Encoding ASCII -Force

# Adiciona a pasta 'bin' ao PATH do usuário PERMANENTEMENTE
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$GlobalBinPath*") {
    Write-Host "Adicionando o projeto ao PATH do seu Windows..." -ForegroundColor Cyan
    $NewPath = "$GlobalBinPath;$UserPath"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    $env:Path = "$GlobalBinPath;$env:Path"
}

Write-Host "`n[SUCESSO] Setup concluído!" -ForegroundColor Green
Write-Host "-------------------------------------------------------"
Write-Host "O comando 'agent-ollama' agora pode ser usado em QUALQUER lugar," -ForegroundColor Yellow
Write-Host "sem precisar ativar manualmente o venv." -ForegroundColor Yellow
Write-Host "-------------------------------------------------------"
Write-Host "IMPORTANTE: Feche este terminal e abra um NOVO para testar." -ForegroundColor White
Write-Host "Iniciando agora para testar...`n" -ForegroundColor Cyan

# 5. Inicia o projeto pelo wrapper criado
& "$BatPath"
