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

function Invoke-StepWithRetry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [int]$MaxAttempts = 3,
        [int]$DelaySeconds = 15
    )

    $attempt = 1
    while ($attempt -le $MaxAttempts) {
        try {
            Invoke-Step "$Label (tentativa $attempt de $MaxAttempts)" $Command
            return
        }
        catch {
            if ($attempt -ge $MaxAttempts) {
                throw
            }
            Write-Warning "$Label falhou na tentativa $attempt. Nova tentativa em $DelaySeconds segundos."
            Start-Sleep -Seconds $DelaySeconds
            $attempt++
        }
    }
}

try {
    Set-Location $ProjectDir

    Write-Host "[$(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')] Iniciando atualizacao do dashboard..."

    $env:GIT_TERMINAL_PROMPT = "0"

    Invoke-Step "git config gc.auto" { git config --local gc.auto 0 }
    Invoke-Step "git config gc.autoDetach" { git config --local gc.autoDetach false }
    Invoke-Step "git fetch" { git fetch origin }

    Invoke-StepWithRetry "build do dashboard" { python .\servidor_dashboard.py build } 3 20

    $changes = git status --porcelain
    if ([string]::IsNullOrWhiteSpace($changes)) {
        Write-Host "Nenhuma alteracao detectada. Nada para enviar ao GitHub."
        return
    }

    Invoke-Step "git add" { git add . }

    $message = "Atualiza calculos automaticos do dashboard - $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    Invoke-Step "git commit" { git commit -m $message }
    Invoke-StepWithRetry "git push" { git push origin HEAD:main --force-with-lease } 3 15

    Write-Host "Atualizacao concluida e enviada ao GitHub."
}
catch {
    Write-Error "Falha na atualizacao automatica: $($_.Exception.Message)"
    exit 1
}
finally {
    Stop-Transcript | Out-Null
}
