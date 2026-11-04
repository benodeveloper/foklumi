from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QMenu, QPushButton, QVBoxLayout

from core.timer import Phase
from ui.ring import RingTimer
from ui.util import format_time

FOCUS_COLOR = "#38bdf8"
BREAK_COLOR = "#34d399"
IDLE_COLOR = "#64748b"

SIZE = 240


class MainWindow(RingTimer):
    """Floating round timer. Drag to move, right-click for Quit."""

    def __init__(self, on_start, on_stop, on_skip, on_quit, durations):
        super().__init__(size=SIZE, thickness=12, text_dy=-0.07)
        self._durations = durations
        self._phase = Phase.IDLE
        self._on_quit = on_quit

        self.setWindowTitle("Pomodoro DE")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, int(SIZE * 0.2))
        layout.addStretch()
        layout.addLayout(row)

        # start in the top-right corner of the primary screen
        area = QGuiApplication.primaryScreen().availableGeometry()
        self.move(area.right() - SIZE - 30, area.top() + 30)

        self.set_phase(Phase.IDLE)

    # ---------- called by the timer ----------

    def set_phase(self, phase: Phase):
        self._phase = phase
        if phase is Phase.IDLE:
            self.set_state(1.0, format_time(self._durations[Phase.FOCUS]),
                           "READY", IDLE_COLOR)
        else:
            self._apply(self._durations[phase])

    def set_remaining(self, seconds: int):
        if self._phase is not Phase.IDLE:
            self._apply(seconds)

    def _apply(self, seconds: int):
        total = self._durations[self._phase]
        focus = self._phase is Phase.FOCUS
        self.set_state(seconds / total, format_time(seconds),
                       "FOCUS" if focus else "BREAK",
                       FOCUS_COLOR if focus else BREAK_COLOR)

    # ---------- dragging and menu ----------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.windowHandle():
            self.windowHandle().startSystemMove()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Quit", self._on_quit)
        menu.exec(event.globalPos())
