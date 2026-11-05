import sys
from pathlib import Path

from PySide6.QtGui import QIcon

LOGO_NAME = "foklumi-logo-rounded.png"


def base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def logo_path() -> Path:
    return base_dir() / "docs" / "assets" / LOGO_NAME


def app_icon() -> QIcon:
    path = logo_path()
    return QIcon(str(path)) if path.exists() else QIcon()
