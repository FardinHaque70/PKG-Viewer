"""PyInstaller entry point; keeps package imports valid inside frozen apps."""

from pkgviewer.app import main

if __name__ == "__main__":
    raise SystemExit(main())
