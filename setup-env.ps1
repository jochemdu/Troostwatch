# PowerShell script to automate Python virtual environment setup for Troostwatch
# Usage: Open PowerShell in project root and run: ./setup-env.ps1

$venvPath = ".venv"
$requirements = "requirements.txt"

if (!(Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..."
    python -m venv $venvPath
} else {
    Write-Host "Virtual environment already exists."
}

Write-Host "Activating virtual environment..."
. "$venvPath\Scripts\Activate.ps1"

if (Test-Path $requirements) {
    Write-Host "Installing dependencies from $requirements..."
    pip install -r $requirements
} else {
    Write-Host "$requirements not found. Skipping dependency installation."
}

Write-Host "Setup complete."
