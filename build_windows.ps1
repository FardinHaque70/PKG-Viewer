$ErrorActionPreference = "Stop"
$env:PYINSTALLER_CONFIG_DIR = Join-Path (Get-Location) ".pyinstaller"
python -m PyInstaller --noconfirm --clean --onefile --windowed --paths src --name "PKGViewer-Windows-x86_64" src/pkgviewer/launcher.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Windows executable: dist\PKGViewer-Windows-x86_64.exe"
