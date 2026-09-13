# PKG Viewer

> **Upstream attribution:** This project is heavily based on [PS4 PKG Validator](https://github.com/Nigel1992/ps4-pkg-validator) by Nigel1992 and [PS4-pkg-viewer / ps4-pkgtools](https://github.com/Oxwald/PS4-pkg-viewer) by Oxwald. See [`CREDITS.md`](CREDITS.md) for the full attribution and license-preservation notice.

PKG Viewer is a cross-platform desktop application for inspecting PS4 `.pkg` files, reviewing metadata, and checking documented package structure and supported integrity records.

It is developed on macOS first and targets macOS, Windows, and Linux. The interface combines a compact reference-style overview with batch loading, game and package-type grouping, icon preview, validation evidence, entry inspection, report export, and safe extraction of exposed package entries.

## Features

- Open one or many PKGs through a picker, drag-and-drop, or recursive folder scan.
- Group packages by title and classify base games, updates, DLC, and other packages.
- View title, IDs, category, versions, firmware, region, icon, size, and package fields.
- Inspect entry IDs, names, offsets, sizes, flags, and encryption state.
- Validate PKG magic, header and entry ranges, names, overlaps, `param.sfo`, and supported SHA-256 records.
- Export deterministic JSON and readable text reports, or copy a report to the clipboard.
- Extract selected entries or all readable exposed entries with range checks, collision policies, progress, and cancellation.
- Run large-file inspection and extraction without blocking the UI.

Validation distinguishes **Pass**, **Fail**, **Warning**, and **Not checked**. Unsupported payload coverage, signatures, encrypted regions, and unavailable algorithms are never reported as verified.

## Requirements

- Python 3.10 or newer
- PySide6 6.6 or newer

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Run the application:

```bash
pkg-viewer
```

Run checks:

```bash
python -m compileall -q src tests
ruff check src tests
pytest -q
pytest -m real_pkg -q       # requires local samples under pkg/
```

Local sample packages belong in `pkg/`. That directory is intentionally ignored and is never included in source commits or release artifacts.

## Builds and downloads

Builds use PyInstaller on native operating systems:

```bash
./build_macos.sh       # dist/PKGViewer-macOS.dmg and PKG Viewer.app
./build_linux.sh       # dist/PKGViewer-Linux-x86_64.AppImage
.\build_windows.ps1  # dist/PKGViewer-Windows-x86_64.exe
```

Tagged releases publish ready-to-download artifacts on the repository's GitHub Releases page:

- **macOS:** `PKGViewer-macOS.dmg` (open it and drag PKG Viewer to Applications).
- **Windows:** `PKGViewer-Windows-x86_64.exe` (portable executable).
- **Linux:** `PKGViewer-Linux-x86_64.AppImage` (make executable, then run it).

Create a version tag such as `v0.1.0` to trigger native builds and publish the release automatically. macOS is the primary local verification target; Windows and Linux artifacts must be smoke-tested on their native platforms.

## Scope and limitations

PKG Viewer reads documented metadata and exposed package entries. It does not build or edit PKGs, manage signing keys, decrypt protected content, bypass protections, verify digital signatures, or unpack the internal game filesystem. Advisory indicators such as trophy presence or filename backport hints are informational and do not affect authoritative validation.

## Attribution

The full upstream attribution and applicable license notices are preserved in [`CREDITS.md`](CREDITS.md). The project also uses [LibOrbisPkg](https://github.com/maxton/LibOrbisPkg) as a documented format reference.
