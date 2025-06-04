# Serv.Local Otimizado - Verificador de Sistema PowerShell
# Versão 2.0 - Diagnóstico completo

param(
    [switch]$Detailed,
    [switch]$FixIssues
)

# Configurações
$ErrorActionPreference = "Continue"
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
    $issues = @()
    
    # Verificar Windows 11
    $os = Get-CimInstance Win32_OperatingSystem
    if ($os.Caption -notlike "*Windows 11*") {
        $issues += "⚠️  Sistema não é Windows 11: $($os.Caption)"
    } else {
        Write-ColorOutput "✅ Windows 11 detectado: $($os.Caption)" "Success"
    }
    
    # Verificar PowerShell
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        $issues += "❌ PowerShell muito antigo: $($PSVersionTable.PSVersion)"
    } else {
        Write-ColorOutput "✅ PowerShell: $($PSVersionTable.PSVersion)" "Success"
    }
    
    # Verificar memória
    $memory = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    if ($memory -lt 4) {
        $issues += "⚠️  Pouca memória RAM: $memory GB (recomendado: 4GB+)"
    } else {
        Write-ColorOutput "✅ Memória RAM: $memory GB" "Success"
    }
    
    # Verificar espaço em disco
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
    $freeSpace = [math]::Round($disk.FreeSpace / 1GB, 2)
    if ($freeSpace -lt 1) {
        $issues += "❌ Pouco espaço em disco: $freeSpace GB (necessário: 1GB+)"
    } else {
        Write-ColorOutput "✅ Espaço livre: $freeSpace GB" "Success"
    }
    
    return $issues
}

function Test-PythonInstallation {
    Write-ColorOutput "🐍 Verificando instalação do Python..." "Info"
    $issues = @()
    
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            # Verificar versão
            if ($pythonVersion -match "Python (\d+)\.(\d+)") {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                
                if ($major -ge 3 -and $minor -ge 8) {
                    Write-ColorOutput "✅ Python: $pythonVersion" "Success"
                } else {
                    $issues += "❌ Python muito antigo: $pythonVersion (necessário: 3.8+)"
                }
            }
            
            # Verificar pip
            $pipVersion = python -m pip --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-ColorOutput "✅ Pip: $($pipVersion.Split(' ')[1])" "Success"
            } else {
                $issues += "❌ Pip não encontrado"
            }
        } else {
            $issues += "❌ Python não encontrado no PATH"
        }
    }
    catch {
        $issues += "❌ Erro ao verificar Python: $($_.Exception.Message)"
    }
    
    return $issues
}

function Test-ProjectStructure {
    Write-ColorOutput "📁 Verificando estrutura do projeto..." "Info"
    $issues = @()
    
    $requiredFiles = @(
        "src\app.py",
        "src\config\settings.py",
        "src\models\usuario.py",
        "src\models\produto.py",
        "src\services\database.py",
        "requirements.txt",
        ".env.example",
        "instalar.ps1",
        "iniciar.ps1",
        "migrar.ps1"
    )
    
    $requiredDirs = @("src", "src\config", "src\models", "src\services")
    
    foreach ($dir in $requiredDirs) {
        if (-not (Test-Path $dir)) {
            $issues += "❌ Diretório ausente: $dir"
        } else {
            Write-ColorOutput "✅ Diretório: $dir" "Success"
        }
    }
    
    foreach ($file in $requiredFiles) {
        if (-not (Test-Path $file)) {
            $issues += "❌ Arquivo ausente: $file"
        } else {
            Write-ColorOutput "✅ Arquivo: $file" "Success"
        }
    }
    
    return $issues
}

function Test-VirtualEnvironment {
    Write-ColorOutput "🐍 Verificando ambiente virtual..." "Info"
    $issues = @()
    
    if (-not (Test-Path "venv")) {
        $issues += "⚠️  Ambiente virtual não encontrado (execute: .\instalar.ps1)"
        return $issues
    }
    
    $venvPython = "venv\Scripts\python.exe"
    $venvPip = "venv\Scripts\pip.exe"
    
    if (-not (Test-Path $venvPython)) {
        $issues += "❌ Python do ambiente virtual não encontrado"
        return $issues
    }
    
    Write-ColorOutput "✅ Ambiente virtual encontrado" "Success"
    
    # Verificar dependências
    try {
        $testResult = & $venvPython -c "import flask, sqlite3, pandas, cryptography; print('OK')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Dependências principais instaladas" "Success"
        } else {
            $issues += "❌ Dependências ausentes: $testResult"
        }
    }
    catch {
        $issues += "❌ Erro ao verificar dependências: $($_.Exception.Message)"
    }
    
    return $issues
}

function Test-DatabaseHealth {
    Write-ColorOutput "🗄️  Verificando saúde do banco de dados..." "Info"
    $issues = @()
    
    if (-not (Test-Path "data\produtos.db")) {
        $issues += "⚠️  Banco de dados não encontrado (será criado na primeira execução)"
        return $issues
    }
    
    try {
        $venvPython = "venv\Scripts\python.exe"
        $healthCheck = & $venvPython -c "
import sys, sqlite3, json
sys.path.insert(0, 'src')
try:
    from services.database_init import db_initializer
    health = db_initializer.check_database_health()
    print(json.dumps(health))
except Exception as e:
    print(f'ERROR: {e}')
" 2>&1
        
        if ($LASTEXITCODE -eq 0 -and $healthCheck -notlike "ERROR:*") {
            $health = $healthCheck | ConvertFrom-Json
            
            if ($health.status -eq "healthy") {
                Write-ColorOutput "✅ Banco de dados saudável" "Success"
                Write-ColorOutput "   Tabelas: $($health.tables -join ', ')" "Info"
                Write-ColorOutput "   Tamanho: $([math]::Round($health.size_mb, 2)) MB" "Info"
            } else {
                $issues += "⚠️  Banco com problemas: $($health.status)"
            }
        } else {
            $issues += "❌ Erro ao verificar banco: $healthCheck"
        }
    }
    catch {
        $issues += "❌ Erro ao verificar banco: $($_.Exception.Message)"
    }
    
    return $issues
}

function Test-NetworkConnectivity {
    Write-ColorOutput "🌐 Verificando conectividade de rede..." "Info"
    $issues = @()
    
    # Verificar se porta 5000 está disponível
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, 5000)
        $listener.Start()
        $listener.Stop()
        Write-ColorOutput "✅ Porta 5000 disponível" "Success"
    }
    catch {
        $issues += "⚠️  Porta 5000 em uso (use: .\iniciar.ps1 -Port 8080)"
    }
    
    # Verificar conectividade com internet (para atualizações)
    try {
        $response = Test-NetConnection -ComputerName "www.google.com" -Port 80 -InformationLevel Quiet
        if ($response) {
            Write-ColorOutput "✅ Conectividade com internet" "Success"
        } else {
            $issues += "⚠️  Sem conectividade com internet (atualizações podem falhar)"
        }
    }
    catch {
        $issues += "⚠️  Erro ao testar conectividade: $($_.Exception.Message)"
    }
    
    return $issues
}

function Test-PerformanceMetrics {
    Write-ColorOutput "⚡ Verificando métricas de performance..." "Info"
    $issues = @()
    
    # Verificar uso de CPU
    $cpu = Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average
    if ($cpu.Average -gt 80) {
        $issues += "⚠️  CPU com alta utilização: $($cpu.Average)%"
    } else {
        Write-ColorOutput "✅ CPU: $($cpu.Average)% de uso" "Success"
    }
    
    # Verificar uso de memória
    $os = Get-CimInstance Win32_OperatingSystem
    $memoryUsage = [math]::Round((($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize) * 100, 2)
    if ($memoryUsage -gt 85) {
        $issues += "⚠️  Memória com alta utilização: $memoryUsage%"
    } else {
        Write-ColorOutput "✅ Memória: $memoryUsage% de uso" "Success"
    }
    
    # Verificar fragmentação do disco
    try {
        $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
        $fragmentation = [math]::Round((($disk.Size - $disk.FreeSpace) / $disk.Size) * 100, 2)
        if ($fragmentation -gt 90) {
            $issues += "⚠️  Disco quase cheio: $fragmentation% usado"
        } else {
            Write-ColorOutput "✅ Disco: $fragmentation% usado" "Success"
        }
    }
    catch {
        $issues += "⚠️  Erro ao verificar disco: $($_.Exception.Message)"
    }
    
    return $issues
}

function Fix-CommonIssues {
    param([array]$Issues)
    
    if (-not $FixIssues) {
        return
    }
    
    Write-ColorOutput "🔧 Tentando corrigir problemas encontrados..." "Info"
    
    foreach ($issue in $Issues) {
        if ($issue -like "*Ambiente virtual não encontrado*") {
            Write-ColorOutput "🔧 Criando ambiente virtual..." "Info"
            try {
                python -m venv venv
                Write-ColorOutput "✅ Ambiente virtual criado" "Success"
            }
            catch {
                Write-ColorOutput "❌ Erro ao criar ambiente virtual: $($_.Exception.Message)" "Error"
            }
        }
        
        if ($issue -like "*Dependências ausentes*") {
            Write-ColorOutput "🔧 Instalando dependências..." "Info"
            try {
                & "venv\Scripts\pip.exe" install -r requirements.txt --quiet
                Write-ColorOutput "✅ Dependências instaladas" "Success"
            }
            catch {
                Write-ColorOutput "❌ Erro ao instalar dependências: $($_.Exception.Message)" "Error"
            }
        }
        
        if ($issue -like "*Diretório ausente*") {
            $dirName = ($issue -split ": ")[1]
            Write-ColorOutput "🔧 Criando diretório: $dirName" "Info"
            try {
                New-Item -ItemType Directory -Path $dirName -Force | Out-Null
                Write-ColorOutput "✅ Diretório criado: $dirName" "Success"
            }
            catch {
                Write-ColorOutput "❌ Erro ao criar diretório: $($_.Exception.Message)" "Error"
            }
        }
    }
}

function Show-SystemSummary {
    param([array]$AllIssues)
    
    Write-Header "RESUMO DA VERIFICAÇÃO"
    
    $criticalIssues = $AllIssues | Where-Object { $_ -like "❌*" }
    $warnings = $AllIssues | Where-Object { $_ -like "⚠️*" }
    
    if ($criticalIssues.Count -eq 0 -and $warnings.Count -eq 0) {
        Write-ColorOutput "🎉 SISTEMA PERFEITO!" "Success"
        Write-ColorOutput "   Todos os requisitos atendidos" "Success"
        Write-ColorOutput "   Sistema pronto para uso" "Success"
    } elseif ($criticalIssues.Count -eq 0) {
        Write-ColorOutput "✅ SISTEMA OK COM AVISOS" "Warning"
        Write-ColorOutput "   $($warnings.Count) avisos encontrados" "Warning"
        Write-ColorOutput "   Sistema funcional" "Success"
    } else {
        Write-ColorOutput "❌ PROBLEMAS CRÍTICOS ENCONTRADOS" "Error"
        Write-ColorOutput "   $($criticalIssues.Count) problemas críticos" "Error"
        Write-ColorOutput "   $($warnings.Count) avisos" "Warning"
    }
    
    Write-Host ""
    
    if ($AllIssues.Count -gt 0) {
        Write-ColorOutput "📋 PROBLEMAS ENCONTRADOS:" "Info"
        foreach ($issue in $AllIssues) {
            Write-ColorOutput "   $issue" "Warning"
        }
        Write-Host ""
        
        if ($criticalIssues.Count -gt 0) {
            Write-ColorOutput "🔧 SOLUÇÕES RECOMENDADAS:" "Info"
            Write-ColorOutput "   1. Execute: .\instalar.ps1" "Info"
            Write-ColorOutput "   2. Execute: .\verificar.ps1 -FixIssues" "Info"
            Write-ColorOutput "   3. Consulte: README_PowerShell.md" "Info"
        }
    }
    
    Write-Host ""
    Write-ColorOutput "📊 PRÓXIMOS PASSOS:" "Info"
    if ($criticalIssues.Count -eq 0) {
        Write-ColorOutput "   ✅ Sistema pronto: .\iniciar.ps1" "Success"
    } else {
        Write-ColorOutput "   🔧 Corrigir problemas primeiro" "Warning"
    }
    Write-ColorOutput "   📖 Documentação: README_PowerShell.md" "Info"
    Write-ColorOutput "   🆘 Suporte: logs\app.log" "Info"
}

# SCRIPT PRINCIPAL
try {
    Write-Header "VERIFICADOR DE SISTEMA SERV.LOCAL OTIMIZADO"
    
    $allIssues = @()
    
    # Executar todas as verificações
    $allIssues += Test-SystemRequirements
    $allIssues += Test-PythonInstallation
    $allIssues += Test-ProjectStructure
    $allIssues += Test-VirtualEnvironment
    $allIssues += Test-DatabaseHealth
    $allIssues += Test-NetworkConnectivity
    
    if ($Detailed) {
        $allIssues += Test-PerformanceMetrics
    }
    
    # Tentar corrigir problemas se solicitado
    if ($FixIssues -and $allIssues.Count -gt 0) {
        Fix-CommonIssues -Issues $allIssues
        
        # Re-executar verificações após correções
        Write-ColorOutput "🔄 Re-verificando após correções..." "Info"
        $allIssues = @()
        $allIssues += Test-SystemRequirements
        $allIssues += Test-PythonInstallation
        $allIssues += Test-ProjectStructure
        $allIssues += Test-VirtualEnvironment
        $allIssues += Test-DatabaseHealth
        $allIssues += Test-NetworkConnectivity
    }
    
    # Mostrar resumo
    Show-SystemSummary -AllIssues $allIssues
    
}
catch {
    Write-ColorOutput "❌ Erro fatal durante verificação: $($_.Exception.Message)" "Error"
    exit 1
}
finally {
    Read-Host "Pressione Enter para continuar"
}

