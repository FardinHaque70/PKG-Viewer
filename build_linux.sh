#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$PWD/.pyinstaller}"
"$PYTHON_BIN" -m PyInstaller --noconfirm --clean --paths src --name "PKG Viewer" src/pkgviewer/launcher.py
mkdir -p dist/appimage/AppDir/usr/bin dist/appimage/AppDir/usr/share/applications
cp "dist/PKG Viewer/PKG Viewer" dist/appimage/AppDir/usr/bin/pkgviewer
chmod +x dist/appimage/AppDir/usr/bin/pkgviewer
cat > dist/appimage/AppDir/pkgviewer.desktop <<'EOF'
[Desktop Entry]
Name=PKG Viewer
Exec=pkgviewer
Type=Application
Categories=Utility;
EOF
cp dist/appimage/pkgviewer.desktop dist/appimage/AppDir/usr/share/applications/
curl -L -o dist/appimage/appimagetool.AppImage https://github.com/AppImage/appimagetool/releases/latest/download/appimagetool-x86_64.AppImage
chmod +x dist/appimage/appimagetool.AppImage
ARCH=x86_64 dist/appimage/appimagetool.AppImage dist/appimage/AppDir dist/PKGViewer-x86_64.AppImage
