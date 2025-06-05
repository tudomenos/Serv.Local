# Script para iniciar o Sistema EAN no Windows via PowerShell

# Verifica se o Python 3 está instalado e no PATH
Write-Host "Verificando instalação do Python 3..."
try {
    $pythonVersion = python --version
    Write-Host "Python encontrado: $pythonVersion"
} catch {
    Write-Error "Python 3 não encontrado no PATH. Por favor, instale o Python 3 (https://www.python.org/downloads/windows/) e certifique-se de adicioná-lo ao PATH durante a instalação."
    exit 1
}

# Define o diretório do script como diretório de trabalho
$scriptPath = $PSScriptRoot
cd $scriptPath
Write-Host "Diretório de trabalho definido para: $scriptPath"

# Nome do ambiente virtual
$venvName = ".venv"

# Verifica se o ambiente virtual existe
if (-not (Test-Path -Path $venvName)) {
    Write-Host "Criando ambiente virtual '$venvName'..."
    python -m venv $venvName
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Falha ao criar ambiente virtual."
        exit 1
    }
    Write-Host "Ambiente virtual criado com sucesso."
} else {
    Write-Host "Ambiente virtual '$venvName' já existe."
}

# Ativa o ambiente virtual
Write-Host "Ativando ambiente virtual..."
try {
    & "$scriptPath\$venvName\Scripts\Activate.ps1"
    Write-Host "Ambiente virtual ativado."
} catch {
    Write-Error "Falha ao ativar o ambiente virtual. Certifique-se de que a execução de scripts PowerShell está habilitada (Execute: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser)."
    exit 1
}


# Instala as dependências do requirements.txt
Write-Host "Instalando dependências do requirements.txt..."
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha ao instalar dependências."
    # Tenta desativar o venv antes de sair
    try { Deactivate-Venv } catch {}
    exit 1
}
Write-Host "Dependências instaladas com sucesso."

# Executa a aplicação Flask
Write-Host "Iniciando a aplicação Flask..."
Write-Host "Acesse a aplicação em http://127.0.0.1:5000 (ou o endereço informado)"
# Define a variável de ambiente FLASK_APP (necessário para 'flask run')
$env:FLASK_APP = "src.main"
# Define o modo de desenvolvimento (opcional, fornece mais debug)
$env:FLASK_ENV = "development"

# Executa usando 'flask run' (mais padrão para Flask)
flask run

# O script terminará quando o servidor Flask for interrompido (Ctrl+C)
Write-Host "Aplicação Flask encerrada."

# Desativa o ambiente virtual (pode não ser executado se o script for interrompido)
# Write-Host "Desativando ambiente virtual..."
# try { Deactivate-Venv } catch {}

