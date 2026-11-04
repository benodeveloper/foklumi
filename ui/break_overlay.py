from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from core.vocab import Word
from ui.util import format_time


class ScreenCover(QWidget):
    """A plain dark fullscreen window for one monitor."""

    def __init__(self, screen):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self.setStyleSheet("background-color: #0f172a;")


class BreakOverlay(ScreenCover):
    """The main break screen: countdown on top, vocabulary card below."""

    escape_pressed = Signal()  # temporary, for testing only

    def __init__(self, screen):
        super().__init__(screen)
        self.setStyleSheet("""
            QWidget { background-color: #0f172a; color: #e2e8f0; }
            #title { font-size: 22px; color: #94a3b8; }
            #countdown { font-size: 120px; font-weight: bold; color: #38bdf8; }
            #counter { font-size: 16px; color: #64748b; }
            #german { font-size: 56px; font-weight: bold; color: #f8fafc; }
            #english { font-size: 28px; color: #fbbf24; }
            #explanation { font-size: 22px; color: #cbd5e1; }
            #example_de { font-size: 26px; font-style: italic; color: #f1f5f9; }
            #example_en { font-size: 20px; color: #94a3b8; }
        """)

        self._title = self._label("title", "BREAK TIME")
        self._countdown = self._label("countdown", "02:00")
        self._counter = self._label("counter", "")
        self._german = self._label("german", "")
        self._english = self._label("english", "")
        self._explanation = self._label("explanation", "", wrap=True)
        self._example_de = self._label("example_de", "", wrap=True)
        self._example_en = self._label("example_en", "", wrap=True)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #334155; background-color: #334155;")
        line.setMaximumWidth(700)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addStretch(2)
        for w in (self._title, self._countdown):
            layout.addWidget(w, alignment=Qt.AlignHCenter)
        layout.addSpacing(20)
        layout.addWidget(line, alignment=Qt.AlignHCenter)
        layout.addSpacing(20)
        for w in (self._counter, self._german, self._english,
                  self._explanation, self._example_de, self._example_en):
            layout.addWidget(w, alignment=Qt.AlignHCenter)
        layout.addStretch(3)

    def _label(self, name, text, wrap=False):
        label = QLabel(text)
        label.setObjectName(name)
        label.setAlignment(Qt.AlignCenter)
        if wrap:
            label.setWordWrap(True)
            label.setMaximumWidth(900)
            label.setMinimumWidth(600)
        return label

    def set_countdown(self, seconds: int):
        self._countdown.setText(format_time(seconds))

    def set_word(self, word: Word, index: int, total: int):
        self._counter.setText(f"Word {index + 1} of {total}")
        self._german.setText(word.german)
        self._english.setText(word.english)
        self._explanation.setText(word.explanation)
        self._example_de.setText(f"“{word.example_de}”")
        self._example_en.setText(word.example_en)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.escape_pressed.emit()
        else:
            super().keyPressEvent(event)


class BreakScreen:
    """Shows the overlay on every monitor and rotates the words."""

    def __init__(self, on_escape=None):
        self._on_escape = on_escape
        self._windows = []
        self._main = None
        self._words = []
        self._total = 1
        self._shown = -1

    def show(self, words: list[Word], total_seconds: int):
        self.hide()
        self._words = words
        self._total = max(1, total_seconds)
        primary = QGuiApplication.primaryScreen()
        for screen in QGuiApplication.screens():
            if screen == primary:
                self._main = BreakOverlay(screen)
                if self._on_escape:
                    self._main.escape_pressed.connect(self._on_escape)
                window = self._main
            else:
                window = ScreenCover(screen)
            self._windows.append(window)
            window.showFullScreen()
        self._main.activateWindow()
        self._main.setFocus()
        self.update(self._total)

    def update(self, remaining: int):
        if not self._main:
            return
        self._main.set_countdown(remaining)
        n = len(self._words)
        elapsed = self._total - remaining
        index = min(n - 1, max(0, elapsed * n // self._total))
        if index != self._shown:
            self._shown = index
            self._main.set_word(self._words[index], index, n)

    def hide(self):
        for window in self._windows:
            window.close()
        self._windows.clear()
        self._main = None
        self._shown = -1
