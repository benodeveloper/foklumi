from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def make_icon(color: str) -> QIcon:
    """A small ring icon drawn in code, so no image files are needed."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#0f172a"))
    p.drawEllipse(2, 2, 60, 60)
    pen = QPen(QColor(color), 9)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(11, 11, 42, 42), 90 * 16, -270 * 16)
    p.end()
    return QIcon(pixmap)


class Tray(QSystemTrayIcon):
    """Tray icon: click to show/hide the floating timer, right-click for the
    menu. The tooltip shows the current phase and time left."""

    def __init__(self, window, on_start, on_stop, on_skip, on_settings,
                 on_quit):
        super().__init__(make_icon("#64748b"))
        self._window = window
        self._tip = ""
        self.setToolTip("Foklumi")

        menu = QMenu()
        self._toggle = menu.addAction("Hide timer", self._toggle_window)
        menu.addSeparator()
        menu.addAction("Start", on_start)
        menu.addAction("Stop", on_stop)
        menu.addAction("Skip to next phase", on_skip)
        menu.addSeparator()
        menu.addAction("Settings…", on_settings)
        menu.addAction("Quit", on_quit)
        menu.aboutToShow.connect(self._sync_menu)
        self._menu = menu  # keep a reference so it is not garbage-collected
        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)

    def update_state(self, color: str, tip: str):
        self.setIcon(make_icon(color))
        self.set_tip(tip)

    def set_tip(self, tip: str):
        if tip != self._tip:
            self._tip = tip
            self.setToolTip(tip)

    def _sync_menu(self):
        self._toggle.setText(
            "Hide timer" if self._window.is_shown() else "Show timer")

    def _toggle_window(self):
        if self._window.is_shown():
            self._window.hide()
        else:
            self._window.show_timer()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window()
