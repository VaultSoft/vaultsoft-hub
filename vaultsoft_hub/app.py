from __future__ import annotations

import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from .ui.main_window import MainWindow
from .ui.styles import STYLESHEET

ICON_NAME = "icon.ico"

# Windows groups taskbar buttons by Application User Model ID. Without an
# explicit one the button falls back to a generic icon instead of the window's,
# so this has to be set before any window is created.
APP_USER_MODEL_ID = "VaultSoft.Hub"


def _set_app_user_model_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass  # Cosmetic only - never block startup over a taskbar icon.


def _resource_path(name: str) -> str:
    """Locate a bundled resource both frozen and running from source.

    PyInstaller unpacks datas into sys._MEIPASS; from source the file sits at
    the project root, one level above this package.
    """
    base = getattr(
        sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(base, name)


def main() -> int:
    _set_app_user_model_id()
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    # Embedding the icon in the .exe only covers Explorer; the title bar and
    # taskbar use the window icon, so it has to be set explicitly too.
    icon_path = _resource_path(ICON_NAME)
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
