from PySide6.QtGui import QGuiApplication


def format_time(seconds: int) -> str:
    minutes, secs = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def is_x11() -> bool:
    return QGuiApplication.platformName() == "xcb"
