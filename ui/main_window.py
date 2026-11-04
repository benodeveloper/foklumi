from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from core.timer import Phase
from ui.util import format_time


class MainWindow(QWidget):
    def __init__(self, on_start, on_stop, on_skip):
        super().__init__()
        self.setWindowTitle("Pomodoro DE")
        self.setFixedSize(280, 170)

        self._phase = QLabel("Ready")
        self._phase.setAlignment(Qt.AlignCenter)
        self._time = QLabel("45:00")
        self._time.setAlignment(Qt.AlignCenter)
        self._time.setStyleSheet("font-size: 42px; font-weight: bold;")

        start = QPushButton("Start")
        stop = QPushButton("Stop")
        skip = QPushButton("Skip")
        start.clicked.connect(on_start)
        stop.clicked.connect(on_stop)
        skip.clicked.connect(on_skip)

        buttons = QHBoxLayout()
        for b in (start, stop, skip):
            buttons.addWidget(b)

        layout = QVBoxLayout(self)
        layout.addWidget(self._phase)
        layout.addWidget(self._time)
        layout.addLayout(buttons)

    def set_phase(self, phase: Phase):
        names = {Phase.IDLE: "Ready", Phase.FOCUS: "Focus",
                 Phase.BREAK: "Break"}
        self._phase.setText(names[phase])
        if phase is Phase.IDLE:
            self._time.setText("--:--")

    def set_remaining(self, seconds: int):
        self._time.setText(format_time(seconds))
