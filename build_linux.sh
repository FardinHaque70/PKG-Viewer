#!/usr/bin/env bash
set -euo pipefail
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$PWD/.pyinstaller}"
"$PYTHON_BIN" -m PyInstaller --noconfirm --clean --paths src --name "PKG Viewer" src/pkgviewer/launcher.py
mkdir -p dist/appimage/AppDir/usr/bin dist/appimage/AppDir/usr/share/applications
cp -R "dist/PKG Viewer/." dist/appimage/AppDir/usr/bin/
mv "dist/appimage/AppDir/usr/bin/PKG Viewer" dist/appimage/AppDir/usr/bin/pkgviewer
chmod +x dist/appimage/AppDir/usr/bin/pkgviewer
cat > dist/appimage/AppDir/AppRun <<'EOF'
#!/bin/sh
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec "$HERE/usr/bin/pkgviewer" "$@"
EOF
chmod +x dist/appimage/AppDir/AppRun
cat > dist/appimage/AppDir/pkgviewer.svg <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <rect x="8" y="8" width="240" height="240" rx="48" fill="#3d3a53"/>
  <path d="M64 76h128v24H64zM64 116h128v24H64zM64 156h80v24H64z" fill="#fff"/>
</svg>
EOF
cat > dist/appimage/AppDir/pkgviewer.desktop <<'EOF'
[Desktop Entry]
Name=PKG Viewer
Exec=pkgviewer
Icon=pkgviewer
Type=Application
Categories=Utility;
EOF
cp dist/appimage/AppDir/pkgviewer.desktop dist/appimage/AppDir/usr/share/applications/
curl -L -o dist/appimage/appimagetool.AppImage https://github.com/AppImage/appimagetool/releases/latest/download/appimagetool-x86_64.AppImage
chmod +x dist/appimage/appimagetool.AppImage
ARCH=x86_64 dist/appimage/appimagetool.AppImage --appimage-extract-and-run dist/appimage/AppDir dist/PKGViewer-x86_64.AppImage
