param(
    [string]$PythonExe = ".\.venv\Scripts\python.exe",
    [string]$StartDate = "2024-01-01",
    [switch]$ClearProxyEnv = $true,
    [string]$LogDir = "local_data\logs",
    [int]$MaxLogs = 2
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $repoRoot $PythonExe
$logDirPath = Join-Path $repoRoot $LogDir
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDirPath "backfill_pipeline_$timestamp.log"

function Write-Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format s)] $Message"
    Write-Host $line
    Add-Content -Path $logPath -Value $line
}

function Trim-Logs {
    param(
        [string]$Directory,
        [string]$Pattern,
        [int]$Keep
    )
    if ($Keep -lt 1) {
        return
    }
    $files = Get-ChildItem -Path $Directory -Filter $Pattern -File | Sort-Object LastWriteTime -Descending
    if ($files.Count -le $Keep) {
        return
    }
    $toDelete = $files | Select-Object -Skip $Keep
    foreach ($file in $toDelete) {
        Remove-Item -Path $file.FullName -Force
    }
}

Push-Location $repoRoot
try {
    New-Item -ItemType Directory -Path $logDirPath -Force | Out-Null
    New-Item -ItemType File -Path $logPath -Force | Out-Null
    Trim-Logs -Directory $logDirPath -Pattern "backfill_pipeline_*.log" -Keep $MaxLogs

    if (-not (Test-Path $pythonPath)) {
        throw "Python executable not found at $pythonPath. Create the venv first."
    }

    if ($ClearProxyEnv) {
        $env:ALL_PROXY = ""
        $env:HTTP_PROXY = ""
        $env:HTTPS_PROXY = ""
        $env:GIT_HTTP_PROXY = ""
        $env:GIT_HTTPS_PROXY = ""
        Write-Log "Cleared proxy environment variables."
    }

    Write-Log "Running universe refresh..."
    & $pythonPath "scripts/update_universe.py" 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) {
        throw "update_universe.py failed with exit code $LASTEXITCODE"
    }

    Write-Log "Building sector benchmarks (top ETFs/stocks per sector)..."
    & $pythonPath "scripts/build_sector_benchmarks.py" 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) {
        throw "build_sector_benchmarks.py failed with exit code $LASTEXITCODE"
    }

    Write-Log "Running hourly backfill from $StartDate..."
    & $pythonPath "scripts/backfill_hourly.py" "--start-date" $StartDate 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) {
        throw "backfill_hourly.py failed with exit code $LASTEXITCODE"
    }

    Write-Log "Backfill pipeline complete."
    Write-Log "Log file: $logPath"
}
catch {
    Write-Log "Pipeline failed: $($_.Exception.Message)"
    Write-Log "Log file: $logPath"
    throw
}
finally {
    Pop-Location
}
