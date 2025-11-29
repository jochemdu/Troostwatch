# PowerShell script to download and install Python 3.14 automatically
# Usage: Open PowerShell and run: ./install-python314.ps1

$pythonVersion = "3.14.0"
$installerUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe"
$installerPath = "$env:TEMP\python-$pythonVersion-amd64.exe"

Write-Host "Downloading Python $pythonVersion installer..."
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath

Write-Host "Running Python installer..."
Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait

Write-Host "Cleaning up installer..."
Remove-Item $installerPath

Write-Host "Verifying installation..."
python --version

Write-Host "Python $pythonVersion installation complete."
