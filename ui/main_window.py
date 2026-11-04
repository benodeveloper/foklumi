from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QMenu, QPushButton, QVBoxLayout

from core.settings import Settings
from core.timer import Phase
from ui.ring import RingTimer
from ui.util import format_time


class MainWindow(RingTimer):
    """Floating round timer. Drag to move, right-click for Settings / Quit."""

    def __init__(self, settings: Settings, on_start, on_stop, on_skip,
                 on_settings, on_quit):
        super().__init__(size=settings.timer_size, thickness=12, text_dy=-0.07)
        self._s = settings
        self._phase = Phase.IDLE
        self._remaining = 0
        self._on_settings = on_settings
        self._on_quit = on_quit

        self.setWindowTitle("Foklumi")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QPushButton { background-color: #1e293b; color: #e2e8f0;
                          border: none; border-radius: 15px; font-size: 14px; }
            QPushButton:hover { background-color: #334155; }
        """)

        row = QHBoxLayout()
        row.setSpacing(6)
        row.addStretch()
        for text, tip, callback in (("▶", "Start", on_start),
                                    ("■", "Stop", on_stop),
                                    ("»", "Skip to next phase", on_skip)):
            button = QPushButton(text)
            button.setFixedSize(30, 30)
            button.setToolTip(tip)
            button.setFocusPolicy(Qt.NoFocus)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(callback)
            row.addWidget(button)
        row.addStretch()

        self._layout = QVBoxLayout(self)
        self._layout.addStretch()
        self._layout.addLayout(row)

        self._apply_geometry()
        area = QGuiApplication.primaryScreen().availableGeometry()
        self.move(area.right() - self.width() - 30, area.top() + 30)
        self.set_phase(Phase.IDLE)

    # ---------- settings ----------

    def _apply_geometry(self):
        size = self._s.timer_size
        self.setFixedSize(size, size)
        self._layout.setContentsMargins(0, 0, 0, int(size * 0.2))
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
        menu.addSeparator()
        menu.addAction("Quit", self._on_quit)
        menu.exec(event.globalPos())
