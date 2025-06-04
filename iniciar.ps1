# Serv.Local Otimizado - Inicializador PowerShell
# Versão 2.0 - Otimizado para Windows 11

param(
    [switch]$Debug,
    [string]$Port = "5000",
    [string]$Host = "127.0.0.1"
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

function Test-SystemRequirements {
    Write-ColorOutput "🔍 Verificando requisitos do sistema..." "Info"
    
    # Verificar se está no diretório correto
    if (-not (Test-Path "src\app.py")) {
        Write-ColorOutput "❌ Erro: Execute este script no diretório do Serv.Local Otimizado" "Error"
        Write-Host ""
        Write-ColorOutput "Estrutura esperada:" "Warning"
        Write-ColorOutput "  serv_local_otimizado\" "Warning"
        Write-ColorOutput "  ├── src\" "Warning"
        Write-ColorOutput "  ├── data\" "Warning"
        Write-ColorOutput "  ├── backups\" "Warning"
        Write-ColorOutput "  └── iniciar.ps1 (este arquivo)" "Warning"
        return $false
    }
    
    # Verificar ambiente virtual
    if (-not (Test-Path "venv\Scripts\python.exe")) {
        Write-ColorOutput "❌ Ambiente virtual não encontrado!" "Error"
        Write-ColorOutput "Execute primeiro: .\instalar.ps1" "Warning"
        return $false
    }
    
    # Verificar dependências básicas
    $venvPython = ".\venv\Scripts\python.exe"
    try {
        $testResult = & $venvPython -c "import flask; print('OK')" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "❌ Dependências não instaladas!" "Error"
            Write-ColorOutput "Instalando dependências..." "Info"
            
            $venvPip = ".\venv\Scripts\pip.exe"
            & $venvPip install -r requirements.txt --quiet
            
            if ($LASTEXITCODE -ne 0) {
                Write-ColorOutput "❌ Erro ao instalar dependências" "Error"
                return $false
            }
        }
    }
    catch {
        Write-ColorOutput "❌ Erro ao verificar dependências: $($_.Exception.Message)" "Error"
        return $false
    }
    
    Write-ColorOutput "✅ Requisitos verificados" "Success"
    return $true
}

function Initialize-Environment {
    Write-ColorOutput "⚙️  Preparando ambiente..." "Info"
    
    # Criar diretórios se não existirem
    $directories = @("data", "backups", "logs")
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-ColorOutput "📁 Diretório criado: $dir" "Success"
        }
    }
    
    # Verificar/criar arquivo .env
    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-ColorOutput "⚙️  Configuração padrão criada (.env)" "Success"
        } else {
            Write-ColorOutput "⚠️  Arquivo .env.example não encontrado" "Warning"
        }
    }
    
    # Configurar variáveis de ambiente para esta sessão
    if ($Debug) {
        $env:DEBUG = "True"
        $env:LOG_LEVEL = "DEBUG"
    }
    
    if ($Port -ne "5000") {
        $env:PORT = $Port
    }
    
    if ($Host -ne "127.0.0.1") {
        $env:HOST = $Host
    }
    
    Write-ColorOutput "✅ Ambiente preparado" "Success"
    return $true
}

function Test-PortAvailability {
    param([string]$Port)
    
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    }
    catch {
        return $false
    }
}

function Get-SystemInfo {
    $info = @{
        OS = (Get-CimInstance Win32_OperatingSystem).Caption
        PowerShell = $PSVersionTable.PSVersion.ToString()
        Python = ""
        Memory = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
        Disk = [math]::Round((Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace / 1GB, 2)
    }
    
    try {
        $pythonVersion = & ".\venv\Scripts\python.exe" --version 2>&1
        $info.Python = $pythonVersion -replace "Python ", ""
    }
    catch {
        $info.Python = "Não detectado"
    }
    
    return $info
}

function Show-StartupInfo {
    param([hashtable]$SystemInfo, [string]$Port, [string]$Host)
    
    Write-Header "SERV.LOCAL OTIMIZADO v2.0"
    
    Write-ColorOutput "🖥️  INFORMAÇÕES DO SISTEMA:" "Info"
    Write-ColorOutput "   OS: $($SystemInfo.OS)" "Info"
    Write-ColorOutput "   PowerShell: $($SystemInfo.PowerShell)" "Info"
    Write-ColorOutput "   Python: $($SystemInfo.Python)" "Info"
    Write-ColorOutput "   Memória: $($SystemInfo.Memory) GB" "Info"
    Write-ColorOutput "   Espaço livre: $($SystemInfo.Disk) GB" "Info"
    Write-Host ""
    
    Write-ColorOutput "🚀 SISTEMA INICIALIZADO COM SUCESSO!" "Success"
    Write-Host ""
    Write-ColorOutput "📊 LOCALIZAÇÃO DOS DADOS:" "Info"
    Write-ColorOutput "   Banco: $(Resolve-Path 'data\produtos.db' -ErrorAction SilentlyContinue)" "Info"
    Write-ColorOutput "   Backups: $(Resolve-Path 'backups' -ErrorAction SilentlyContinue)" "Info"
    Write-ColorOutput "   Logs: $(Resolve-Path 'logs' -ErrorAction SilentlyContinue)" "Info"
    Write-Host ""
    Write-ColorOutput "🌐 ACESSO AO SISTEMA:" "Info"
    Write-ColorOutput "   URL: http://${Host}:${Port}" "Success"
    Write-ColorOutput "   👤 Login padrão: admin / admin123" "Warning"
    Write-Host ""
    Write-ColorOutput "⚡ MELHORIAS ATIVAS:" "Info"
    Write-ColorOutput "   • Pool de conexões otimizado" "Success"
    Write-ColorOutput "   • Índices de performance" "Success"
    Write-ColorOutput "   • Backup automático" "Success"
    Write-ColorOutput "   • Segurança melhorada" "Success"
    Write-ColorOutput "   • Configuração centralizada" "Success"
    Write-Host ""
    Write-ColorOutput "🛑 Para parar o sistema: Ctrl+C" "Warning"
    Write-ColorOutput "📖 Documentação: README.md" "Info"
    Write-Host ""
}

function Start-Application {
    param([string]$Port, [string]$Host)
    
    $venvPython = ".\venv\Scripts\python.exe"
    
    try {
        # Verificar se porta está disponível
        if (-not (Test-PortAvailability -Port $Port)) {
            Write-ColorOutput "⚠️  Porta $Port já está em uso!" "Warning"
            
            # Tentar encontrar porta alternativa
            $alternativePort = 5001
            while (-not (Test-PortAvailability -Port $alternativePort) -and $alternativePort -lt 5010) {
                $alternativePort++
            }
            
            if ($alternativePort -lt 5010) {
                Write-ColorOutput "🔄 Usando porta alternativa: $alternativePort" "Info"
                $env:PORT = $alternativePort
                $Port = $alternativePort
            } else {
                Write-ColorOutput "❌ Nenhuma porta disponível encontrada (5000-5009)" "Error"
                Write-ColorOutput "Finalize outros processos ou especifique uma porta diferente:" "Warning"
                Write-ColorOutput "   .\iniciar.ps1 -Port 8080" "Info"
                return $false
            }
        }
        
        # Mostrar informações de inicialização
        $systemInfo = Get-SystemInfo
        Show-StartupInfo -SystemInfo $systemInfo -Port $Port -Host $Host
        
        # Iniciar aplicação
        & $venvPython "src\app.py"
        
        return $true
    }
    catch {
        Write-ColorOutput "❌ Erro ao iniciar aplicação: $($_.Exception.Message)" "Error"
        return $false
    }
}

function Show-PostShutdownInfo {
    Write-Host ""
    Write-Header "SISTEMA FINALIZADO"
    
    Write-ColorOutput "👋 Serv.Local Otimizado finalizado com sucesso!" "Success"
    Write-Host ""
    Write-ColorOutput "📊 Para verificar logs:" "Info"
    Write-ColorOutput "   Get-Content logs\app.log -Tail 20" "Info"
    Write-Host ""
    Write-ColorOutput "🔄 Para reiniciar:" "Info"
    Write-ColorOutput "   .\iniciar.ps1" "Info"
    Write-Host ""
    Write-ColorOutput "🔧 Para configurações avançadas:" "Info"
    Write-ColorOutput "   notepad .env" "Info"
    Write-Host ""
}

# SCRIPT PRINCIPAL
try {
    # Verificar requisitos
    if (-not (Test-SystemRequirements)) {
        Read-Host "Pressione Enter para sair"
        exit 1
    }
    
    # Preparar ambiente
    if (-not (Initialize-Environment)) {
        Read-Host "Pressione Enter para sair"
        exit 1
    }
    
    # Iniciar aplicação
    $success = Start-Application -Port $Port -Host $Host
    
    if (-not $success) {
        Read-Host "Pressione Enter para sair"
        exit 1
    }
}
catch {
    Write-ColorOutput "❌ Erro fatal: $($_.Exception.Message)" "Error"
    Write-ColorOutput "Verifique os logs em logs\app.log para mais detalhes" "Warning"
}
finally {
    Show-PostShutdownInfo
    
    if (-not $Debug) {
        Read-Host "Pressione Enter para continuar"
    }
}

