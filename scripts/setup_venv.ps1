param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "Creating .venv with $PythonExe..."
& $PythonExe -m venv .venv

Write-Host "Installing dependencies into .venv..."
& .\.venv\Scripts\python -m pip install --upgrade pip
& .\.venv\Scripts\python -m pip install -r requirements.lock.txt
& .\.venv\Scripts\python -m pip install -e .

Write-Host "Done. Activate with: .\\.venv\\Scripts\\Activate.ps1"
