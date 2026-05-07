$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $ProjectDir "logs"
$LogFile = Join-Path $LogDir ("atualizacao-dashboard-{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Start-Transcript -Path $LogFile -Append | Out-Null

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    Write-Host "Executando: $Label"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label falhou com codigo $LASTEXITCODE."
    }
}

try {
    Set-Location $ProjectDir

    Write-Host "[$(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')] Iniciando atualizacao do dashboard..."

    Invoke-Step "build do dashboard" { python .\servidor_dashboard.py build }

    $changes = git status --porcelain
    if ([string]::IsNullOrWhiteSpace($changes)) {
        Write-Host "Nenhuma alteracao detectada. Nada para enviar ao GitHub."
        return
    }

    Invoke-Step "git add" { git add . }

    $message = "Atualiza calculos automaticos do dashboard - $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    Invoke-Step "git commit" { git commit -m $message }
    Invoke-Step "git push" { git push origin main }

    Write-Host "Atualizacao concluida e enviada ao GitHub."
}
catch {
    Write-Error "Falha na atualizacao automatica: $($_.Exception.Message)"
    exit 1
}
finally {
    Stop-Transcript | Out-Null
}
