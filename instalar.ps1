# Serv.Local Otimizado - Instalador PowerShell
# Versão 2.0 - Otimizado para Windows 11

param(
    [switch]$SkipPython,
    [switch]$Force,
    [string]$InstallPath = $PWD.Path
)

# Configurações
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Cores para output
$Colors = @{
    Success = "Green"
    Warning = "Yellow" 
    Error = "Red"
    Info = "Cyan"
    Header = "Magenta"
}

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Colors[$Color]
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-ColorOutput "╔══════════════════════════════════════════════════════════════╗" "Header"
    Write-ColorOutput "║  $($Title.PadRight(58))  ║" "Header"
    Write-ColorOutput "╚══════════════════════════════════════════════════════════════╝" "Header"
    Write-Host ""
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-PythonInstallation {
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Python encontrado: $pythonVersion" "Success"
            
            # Verificar versão mínima (3.8)
            $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
            if ($versionMatch) {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                
                if ($major -ge 3 -and $minor -ge 8) {
                    return $true
                } else {
                    Write-ColorOutput "⚠️  Versão do Python muito antiga. Necessário Python 3.8+" "Warning"
                    return $false
                }
            }
        }
        return $false
    }
    catch {
        return $false
    }
}

function Install-Python {
    Write-ColorOutput "🐍 Instalando Python..." "Info"
    
    $pythonUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $pythonInstaller = "$env:TEMP\python-installer.exe"
    
    try {
        Write-ColorOutput "📥 Baixando Python 3.11.9..." "Info"
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller -UseBasicParsing
        
        Write-ColorOutput "🔧 Instalando Python (isso pode demorar alguns minutos)..." "Info"
        Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait
        
        # Atualizar PATH na sessão atual
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        
        Remove-Item $pythonInstaller -Force
        
        # Verificar instalação
        Start-Sleep -Seconds 3
        if (Test-PythonInstallation) {
            Write-ColorOutput "✅ Python instalado com sucesso!" "Success"
            return $true
        } else {
            throw "Falha na verificação pós-instalação"
        }
    }
    catch {
        Write-ColorOutput "❌ Erro ao instalar Python: $($_.Exception.Message)" "Error"
        Write-ColorOutput "Por favor, instale manualmente: https://www.python.org/downloads/" "Warning"
        return $false
    }
}

function New-VirtualEnvironment {
    param([string]$Path)
    
    Write-ColorOutput "🐍 Criando ambiente virtual..." "Info"
    
    if (Test-Path "$Path\venv") {
        if ($Force) {
            Write-ColorOutput "🗑️  Removendo ambiente virtual existente..." "Warning"
            Remove-Item "$Path\venv" -Recurse -Force
        } else {
            $response = Read-Host "⚠️  Ambiente virtual já existe. Recriar? (s/N)"
            if ($response -eq "s" -or $response -eq "S") {
                Remove-Item "$Path\venv" -Recurse -Force
            } else {
                Write-ColorOutput "✅ Usando ambiente virtual existente" "Success"
                return $true
            }
        }
    }
    
    try {
        python -m venv "$Path\venv"
        Write-ColorOutput "✅ Ambiente virtual criado" "Success"
        return $true
    }
    catch {
        Write-ColorOutput "❌ Erro ao criar ambiente virtual: $($_.Exception.Message)" "Error"
        return $false
    }
}

function Install-Dependencies {
    param([string]$Path)
    
    Write-ColorOutput "📦 Instalando dependências..." "Info"
    
    $venvPython = "$Path\venv\Scripts\python.exe"
    $venvPip = "$Path\venv\Scripts\pip.exe"
    
    try {
        # Atualizar pip
        Write-ColorOutput "📦 Atualizando pip..." "Info"
        & $venvPython -m pip install --upgrade pip --quiet
        
        # Instalar dependências
        $requirementsFile = "$Path\requirements.txt"
        if (Test-Path $requirementsFile) {
            Write-ColorOutput "📦 Instalando dependências do requirements.txt..." "Info"
            & $venvPip install -r $requirementsFile --quiet
        } else {
            Write-ColorOutput "📦 Instalando dependências individuais..." "Info"
            $dependencies = @(
                "Flask==3.1.0",
                "cryptography==43.0.1", 
                "pandas==2.2.2",
                "openpyxl==3.1.2",
                "requests==2.31.0",
                "Werkzeug==3.1.0",
                "schedule==1.2.0",
                "python-dotenv==1.0.0"
            )
            
            foreach ($dep in $dependencies) {
                Write-ColorOutput "  📦 Instalando $dep..." "Info"
                & $venvPip install $dep --quiet
            }
        }
        
        Write-ColorOutput "✅ Dependências instaladas com sucesso!" "Success"
        return $true
    }
    catch {
        Write-ColorOutput "❌ Erro ao instalar dependências: $($_.Exception.Message)" "Error"
        return $false
    }
}

function Initialize-Configuration {
    param([string]$Path)
    
    Write-ColorOutput "⚙️  Configurando sistema..." "Info"
    
    # Criar diretórios necessários
    $directories = @("data", "backups", "logs")
    foreach ($dir in $directories) {
        $dirPath = "$Path\$dir"
        if (-not (Test-Path $dirPath)) {
            New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
            Write-ColorOutput "📁 Diretório criado: $dir" "Success"
        }
    }
    
    # Configurar arquivo .env
    $envFile = "$Path\.env"
    $envExample = "$Path\.env.example"
    
    if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
        Copy-Item $envExample $envFile
        Write-ColorOutput "✅ Arquivo de configuração criado (.env)" "Success"
        Write-ColorOutput "📝 Você pode editar o arquivo .env para personalizar as configurações" "Info"
    } elseif (Test-Path $envFile) {
        Write-ColorOutput "⚠️  Arquivo .env já existe, mantendo configurações atuais" "Warning"
    }
    
    return $true
}

function Test-Installation {
    param([string]$Path)
    
    Write-ColorOutput "🧪 Testando instalação..." "Info"
    
    $venvPython = "$Path\venv\Scripts\python.exe"
    
    try {
        # Testar importações básicas
        $testScript = @"
import sys
sys.path.insert(0, 'src')
try:
    from config.settings import active_config
    print('✅ Configuração carregada com sucesso')
    print(f'📊 Banco de dados: {active_config.DATABASE_PATH}')
    print(f'💾 Backups: {active_config.BACKUP_DIR}')
except Exception as e:
    print(f'❌ Erro: {e}')
    sys.exit(1)
"@
        
        $testResult = & $venvPython -c $testScript 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput $testResult "Success"
            return $true
        } else {
            Write-ColorOutput "❌ Erro no teste: $testResult" "Error"
            return $false
        }
    }
    catch {
        Write-ColorOutput "❌ Erro ao testar instalação: $($_.Exception.Message)" "Error"
        return $false
    }
}

function New-DesktopShortcut {
    param([string]$Path)
    
    $response = Read-Host "🖥️  Deseja criar atalho na área de trabalho? (s/N)"
    if ($response -eq "s" -or $response -eq "S") {
        try {
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Serv.Local Otimizado.lnk")
            $Shortcut.TargetPath = "powershell.exe"
            $Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$Path\iniciar.ps1`""
            $Shortcut.WorkingDirectory = $Path
            $Shortcut.IconLocation = "powershell.exe,0"
            $Shortcut.Description = "Serv.Local Otimizado v2.0"
            $Shortcut.Save()
            
            Write-ColorOutput "✅ Atalho criado na área de trabalho" "Success"
        }
        catch {
            Write-ColorOutput "⚠️  Não foi possível criar atalho: $($_.Exception.Message)" "Warning"
        }
    }
}

function Start-Application {
    param([string]$Path)
    
    $response = Read-Host "🚀 Deseja iniciar o sistema agora? (s/N)"
    if ($response -eq "s" -or $response -eq "S") {
        Write-ColorOutput "🚀 Iniciando Serv.Local Otimizado..." "Info"
        Write-Host ""
        
        $venvPython = "$Path\venv\Scripts\python.exe"
        & $venvPython "$Path\src\app.py"
    } else {
        Write-ColorOutput "👋 Para iniciar mais tarde, execute:" "Info"
        Write-ColorOutput "   .\iniciar.ps1" "Info"
        Write-Host ""
        Read-Host "Pressione Enter para continuar"
    }
}

# SCRIPT PRINCIPAL
try {
    Write-Header "SERV.LOCAL OTIMIZADO - INSTALADOR POWERSHELL v2.0"
    
    # Verificar se está executando como administrador
    if (-not (Test-Administrator)) {
        Write-ColorOutput "⚠️  Recomendado executar como Administrador para melhor compatibilidade" "Warning"
        $response = Read-Host "Continuar mesmo assim? (s/N)"
        if ($response -ne "s" -and $response -ne "S") {
            Write-ColorOutput "Reinicie o PowerShell como Administrador e execute novamente" "Info"
            exit 1
        }
    }
    
    # Verificar/Instalar Python
    if (-not $SkipPython) {
        if (-not (Test-PythonInstallation)) {
            Write-ColorOutput "❌ Python não encontrado ou versão inadequada!" "Error"
            
            if (Test-Administrator) {
                $installPython = Read-Host "Deseja instalar Python automaticamente? (s/N)"
                if ($installPython -eq "s" -or $installPython -eq "S") {
                    if (-not (Install-Python)) {
                        exit 1
                    }
                } else {
                    Write-ColorOutput "Por favor, instale Python 3.8+ manualmente: https://www.python.org/downloads/" "Warning"
                    exit 1
                }
            } else {
                Write-ColorOutput "Por favor, instale Python 3.8+ manualmente: https://www.python.org/downloads/" "Warning"
                exit 1
            }
        }
    }
    
    # Criar ambiente virtual
    if (-not (New-VirtualEnvironment -Path $InstallPath)) {
        exit 1
    }
    
    # Instalar dependências
    if (-not (Install-Dependencies -Path $InstallPath)) {
        exit 1
    }
    
    # Configurar sistema
    if (-not (Initialize-Configuration -Path $InstallPath)) {
        exit 1
    }
    
    # Testar instalação
    if (-not (Test-Installation -Path $InstallPath)) {
        exit 1
    }
    
    # Criar atalho (opcional)
    New-DesktopShortcut -Path $InstallPath
    
    # Mostrar resumo da instalação
    Write-Header "INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
    
    Write-ColorOutput "🎉 Serv.Local Otimizado instalado com sucesso!" "Success"
    Write-Host ""
    Write-ColorOutput "📋 PRÓXIMOS PASSOS:" "Info"
    Write-Host ""
    Write-ColorOutput "1. Para iniciar o sistema:" "Info"
    Write-ColorOutput "   .\iniciar.ps1" "Info"
    Write-Host ""
    Write-ColorOutput "2. Acesse no navegador:" "Info"
    Write-ColorOutput "   http://127.0.0.1:5000" "Info"
    Write-Host ""
    Write-ColorOutput "3. Login padrão:" "Info"
    Write-ColorOutput "   Usuário: admin" "Info"
    Write-ColorOutput "   Senha: admin123" "Info"
    Write-Host ""
    Write-ColorOutput "4. ⚠️  IMPORTANTE: Altere a senha padrão imediatamente!" "Warning"
    Write-Host ""
    Write-ColorOutput "📁 LOCALIZAÇÃO DOS DADOS:" "Info"
    Write-ColorOutput "   Banco: $InstallPath\data\produtos.db" "Info"
    Write-ColorOutput "   Backups: $InstallPath\backups\" "Info"
    Write-ColorOutput "   Logs: $InstallPath\logs\" "Info"
    Write-Host ""
    Write-ColorOutput "🔧 Para personalizar configurações, edite o arquivo .env" "Info"
    Write-ColorOutput "📖 Consulte o README.md para instruções detalhadas" "Info"
    Write-Host ""
    
    # Iniciar aplicação (opcional)
    Start-Application -Path $InstallPath
    
}
catch {
    Write-ColorOutput "❌ Erro fatal durante a instalação: $($_.Exception.Message)" "Error"
    Write-ColorOutput "Verifique os logs e tente novamente" "Warning"
    exit 1
}

