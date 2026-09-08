import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from .ui import build_window
    app = QApplication(sys.argv)
    window = build_window()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
