$ErrorActionPreference = "Stop"
$env:PYINSTALLER_CONFIG_DIR = Join-Path (Get-Location) ".pyinstaller"
python3 -m PyInstaller --noconfirm --clean --windowed --paths src --name "PKG Viewer" src/pkgviewer/launcher.py
Write-Host "Windows executable: dist\PKG Viewer.exe"
