from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QMenu, QPushButton, QVBoxLayout

from core.settings import Settings
from core.timer import Phase
from ui.ring import RingTimer
from ui.util import format_time

BUTTON_CSS = (
    "QPushButton {{ background-color: #1e293b; color: #e2e8f0; border: none;"
    " border-radius: {radius}px; font-size: {font}px; }}"
    "QPushButton:hover {{ background-color: {hover}; }}"
)


class MainWindow(RingTimer):
    """Floating round timer. Drag to move. Top row: settings, hide, quit.
    Bottom row: start, stop, skip."""

    def __init__(self, settings: Settings, on_start, on_stop, on_skip,
                 on_settings, on_minimize, on_quit):
        super().__init__(size=settings.timer_size, thickness=12,
                         text_dy=-0.04, label_dy=0.15)
        self._s = settings
        self._phase = Phase.IDLE
        self._remaining = 0
        self._on_settings = on_settings
        self._on_minimize = on_minimize
        self._on_quit = on_quit

        self.setWindowTitle("Foklumi")
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._buttons = []  # (button, is_small, hover color)
        top = self._row([
            ("⚙", "Settings", on_settings, "#334155", True),
            ("–", "Hide to background", on_minimize, "#334155", True),
            ("✕", "Quit", on_quit, "#991b1b", True),
        ])
        bottom = self._row([
            ("▶", "Start", on_start, "#334155", False),
            ("■", "Stop", on_stop, "#334155", False),
            ("»", "Skip to next phase", on_skip, "#334155", False),
        ])

        self._layout = QVBoxLayout(self)
        self._layout.addLayout(top)
        self._layout.addStretch()
        self._layout.addLayout(bottom)

        self._apply_geometry()
        area = QGuiApplication.primaryScreen().availableGeometry()
        self.move(area.right() - self.width() - 30, area.top() + 30)
        self.set_phase(Phase.IDLE)

    def _row(self, specs):
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addStretch()
        for text, tip, callback, hover, small in specs:
            button = QPushButton(text)
            button.setToolTip(tip)
            button.setFocusPolicy(Qt.NoFocus)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(callback)
            self._buttons.append((button, small, hover))
            row.addWidget(button)
        row.addStretch()
        return row

    # ---------- visibility (used by the tray icon) ----------

    def is_shown(self) -> bool:
        return self.isVisible() and not self.isMinimized()

    def show_timer(self):
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()

    # ---------- settings ----------

    def _apply_geometry(self):
        size = self._s.timer_size
        self.setFixedSize(size, size)
        self._thickness = max(8, size // 20)

        big = max(24, int(size * 0.125))
        small = max(18, int(size * 0.095))
        for button, is_small, hover in self._buttons:
            d = small if is_small else big
            button.setFixedSize(d, d)
            button.setStyleSheet(BUTTON_CSS.format(
                radius=d // 2, font=int(d * 0.5), hover=hover))

        margin = int(size * 0.2)
        self._layout.setContentsMargins(0, margin, 0, margin)

        flags = Qt.FramelessWindowHint
        if self._s.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def apply_settings(self, settings: Settings):
        was_visible = self.isVisible()
        pos = self.pos()
        self._s = settings
        self._apply_geometry()
        self.move(pos)
        if was_visible:
            self.show()  # setWindowFlags hides the window
        self._refresh()

    # ---------- called by the timer ----------

    def set_phase(self, phase: Phase):
        self._phase = phase
        self._remaining = self._total(phase)
        self._refresh()

    def set_remaining(self, seconds: int):
        if self._phase is not Phase.IDLE:
            self._remaining = seconds
            self._refresh()

    def _total(self, phase: Phase) -> int:
        if phase is Phase.BREAK:
            return self._s.break_seconds
        return self._s.focus_minutes * 60

    def _refresh(self):
        if self._phase is Phase.IDLE:
            self.set_state(1.0, format_time(self._s.focus_minutes * 60),
                           "READY", self._s.idle_color)
            return
        focus = self._phase is Phase.FOCUS
        total = max(1, self._total(self._phase))
        self.set_state(self._remaining / total, format_time(self._remaining),
                       "FOCUS" if focus else "BREAK",
                       self._s.focus_color if focus else self._s.break_color)

    # ---------- dragging and menu ----------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.windowHandle():
            self.windowHandle().startSystemMove()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Settings…", self._on_settings)
        menu.addAction("Hide to background", self._on_minimize)
        menu.addSeparator()
        menu.addAction("Quit", self._on_quit)
        menu.exec(event.globalPos())
