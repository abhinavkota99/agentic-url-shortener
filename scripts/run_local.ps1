$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# This project is pinned to the Python 3.11 dependency set.
py -3.11 --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.11 is required. Install Python 3.11, then rerun this script. Check installed versions with: py -0p"
}

if (-not (Test-Path ".env")) {
    py -3.11 scripts/bootstrap.py
    if ($LASTEXITCODE -ne 0) { throw "Project bootstrap failed. Review the error above." }
}

# Native executable failures do not reliably stop Windows PowerShell 5.1.
# Check exit codes explicitly so startup never continues without Docker.
docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not ready. Start Docker Desktop, switch to Linux containers if needed, wait for Engine running, then rerun this script."
}

Write-Host "Warming Maven cache. This step needs internet access and may take several minutes."
py -3.11 scripts/warm_maven_cache.py
if ($LASTEXITCODE -ne 0) { throw "Maven cache warm-up failed. Check Docker and internet access, then rerun." }

docker compose up -d postgres redis backend prometheus grafana
if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed to start the infrastructure services. Run 'docker compose logs' for details." }

Set-Location (Join-Path $Root "orchestrator")
if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the Python 3.11 virtual environment." }
}
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Could not upgrade pip in the project virtual environment." }
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Python dependencies failed to install. Check orchestrator/requirements.txt and the Python version." }

Write-Host "Starting orchestrator at http://localhost:8000"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
if ($LASTEXITCODE -ne 0) { throw "The orchestrator exited with an error. Review the traceback above." }
