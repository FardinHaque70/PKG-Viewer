import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from pkgviewer.ui import Window


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def test_window_reference_layout(qapp):
    window = Window()
    assert (window.width(), window.height()) == (1055, 422)
    assert window.files.alternatingRowColors()
    assert window.info.editTriggers().value == 0
    assert {"Extract selected", "Extract all"} <= set(window.buttons)
    window.close()
