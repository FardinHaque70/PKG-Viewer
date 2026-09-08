#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$PWD/.pyinstaller}"
"$PYTHON_BIN" -m PyInstaller --noconfirm --clean --windowed --paths src --name "PKG Viewer" src/pkgviewer/launcher.py
rm -rf dist/PKGViewer.dmg dist/dmg
mkdir -p dist/dmg
cp -R "dist/PKG Viewer.app" dist/dmg/
hdiutil create -volname "PKG Viewer" -srcfolder dist/dmg -ov -format UDZO dist/PKGViewer.dmg
