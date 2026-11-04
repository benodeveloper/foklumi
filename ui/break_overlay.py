from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QVBoxLayout, QWidget)

from core.vocab import NounInfo, VerbInfo, Word
from ui.ring import RingTimer
from ui.util import format_time, is_x11

EMERGENCY_MODS = Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier


class VerbView(QWidget):
    """Displays a 4x2 grid of tenses showing the 'ich' form, expanding 
    to all pronouns when a tense is clicked."""
    def __init__(self, verb: VerbInfo):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        
        self.grid = QGridLayout()
        self.buttons = {}
        self.tense_data = verb.tenses
        self.pronouns = verb.pronouns
        
        tenses_ordered = [
            ("praesens", "Präsens"), ("perfekt", "Perfekt"),
            ("praeteritum", "Präteritum"), ("plusquamperfekt", "Plusquamperfekt"),
            ("futur1", "Futur I"), ("futur2", "Futur II"),
            ("konjunktiv1", "Konjunktiv I"), ("konjunktiv2", "Konjunktiv II")
        ]
        
        row, col = 0, 0
        for key, label in tenses_ordered:
            if key not in verb.tenses:
                continue
            ich_form = verb.tenses[key][0]
            
            btn = QPushButton(f"{label}\n(ich {ich_form})")
            btn.setCheckable(True)
            btn.setObjectName("tense_btn")
            btn.setCursor(Qt.PointingHandCursor)
            # Capture the key correctly in the lambda
            btn.clicked.connect(lambda checked, k=key: self.show_tense(k))
            
            self.buttons[key] = btn
            self.grid.addWidget(btn, row, col)
            
            col += 1
            if col > 3:
                col = 0
                row += 1
                
        layout.addLayout(self.grid)
        
        self.pronoun_label = QLabel()
        self.pronoun_label.setObjectName("pronoun_display")
        self.pronoun_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.pronoun_label)
        
        self.setStyleSheet("""
            #tense_btn { 
                background-color: #1e293b; color: #94a3b8; 
                border: 1px solid #334155; border-radius: 6px; 
                padding: 10px; font-size: 16px; 
            }
            #tense_btn:hover { background-color: #334155; color: #e2e8f0; }
            #tense_btn:checked { 
                background-color: #38bdf8; color: #0f172a; 
                font-weight: bold; border: 1px solid #38bdf8;
            }
            #pronoun_display {
                font-size: 20px; color: #e2e8f0; margin-top: 5px;
                background-color: #1e293b; border-radius: 8px; padding: 12px;
            }
        """)
        
        if "praesens" in self.buttons:
            self.buttons["praesens"].setChecked(True)
            self.show_tense("praesens")

    def show_tense(self, tense_key):
        for k, btn in self.buttons.items():
            btn.setChecked(k == tense_key)
        
        forms = self.tense_data[tense_key]
        lines = [f"<span style='color:#94a3b8'>{p}</span> {f}" 
                 for p, f in zip(self.pronouns, forms)]
        
        html = f"""
        <table width='100%' cellpadding='6'>
            <tr>
                <td align='center'>{lines[0]}</td>
                <td align='center'>{lines[1]}</td>
                <td align='center'>{lines[2]}</td>
            </tr>
            <tr>
                <td align='center'>{lines[3]}</td>
                <td align='center'>{lines[4]}</td>
                <td align='center'>{lines[5]}</td>
            </tr>
        </table>
        """
        self.pronoun_label.setText(html)


class NounView(QWidget):
    def __init__(self, noun: NounInfo):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        
        label = QLabel(f"<b>Plural:</b> {noun.plural} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Genitiv:</b> {noun.genitive}")
        label.setStyleSheet("""
            font-size: 20px; color: #cbd5e1; 
            background-color: #1e293b; border-radius: 8px; padding: 12px;
        """)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)


class ScreenCover(QWidget):
    """A plain dark window covering one monitor."""

    def __init__(self, screen):
        super().__init__()
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        if is_x11():
            flags |= Qt.X11BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self.setStyleSheet("background-color: #0f172a;")

    def present(self):
        if is_x11():
            self.show()  # no window manager involved, geometry is already set
        else:
            self.showFullScreen()
        self.raise_()


class BreakOverlay(ScreenCover):
    speak_word = Signal()
    speak_sentence = Signal()
    emergency = Signal()

    def __init__(self, screen):
        super().__init__(screen)
        self.setStyleSheet("""
            QWidget { background-color: #0f172a; color: #e2e8f0; }
            #german { font-size: 64px; font-weight: bold; color: #f8fafc; }
            #english { font-size: 30px; color: #fbbf24; }
            #explanation { font-size: 22px; color: #cbd5e1; }
            #example_de { font-size: 28px; font-style: italic; color: #f1f5f9; }
            #example_en { font-size: 20px; color: #94a3b8; }
            QPushButton#action_btn { 
                background-color: #1e293b; color: #e2e8f0;
                border: 1px solid #334155; border-radius: 8px;
                padding: 8px 20px; font-size: 18px; 
            }
            QPushButton#action_btn:hover { background-color: #334155; }
        """)

        ring_size = max(180, min(300, int(screen.geometry().height() * 0.28)))
        self._ring = RingTimer(size=ring_size, thickness=ring_size // 18)

        self._german = self._label("german")
        self._english = self._label("english")
        self._explanation = self._label("explanation", wrap=True)
        self._example_de = self._label("example_de", wrap=True)
        self._example_en = self._label("example_en", wrap=True)

        btn_word = self._button("▶  Listen", self.speak_word)
        btn_sentence = self._button("▶  Listen to the sentence", self.speak_sentence)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #334155; background-color: #334155;")
        line.setMaximumWidth(700)

        # Container for the dynamic Verb/Noun panels
        self.extra_container = QVBoxLayout()
        self.extra_container.setAlignment(Qt.AlignHCenter)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addStretch(2)
        layout.addWidget(self._ring, alignment=Qt.AlignHCenter)
        layout.addSpacing(12)
        layout.addWidget(line, alignment=Qt.AlignHCenter)
        layout.addSpacing(12)
        layout.addWidget(self._german, alignment=Qt.AlignHCenter)
        layout.addWidget(btn_word, alignment=Qt.AlignHCenter)
        layout.addWidget(self._english, alignment=Qt.AlignHCenter)
        layout.addWidget(self._explanation, alignment=Qt.AlignHCenter)
        layout.addLayout(self.extra_container)
        layout.addWidget(self._example_de, alignment=Qt.AlignHCenter)
        layout.addWidget(btn_sentence, alignment=Qt.AlignHCenter)
        layout.addWidget(self._example_en, alignment=Qt.AlignHCenter)
        layout.addStretch(3)

    def _label(self, name, text="", wrap=False):
        label = QLabel(text)
        label.setObjectName(name)
        label.setAlignment(Qt.AlignCenter)
        if wrap:
            label.setWordWrap(True)
            label.setMinimumWidth(600)
            label.setMaximumWidth(900)
        return label

    def _button(self, text, signal):
        button = QPushButton(text)
        button.setObjectName("action_btn")
        button.setFocusPolicy(Qt.NoFocus)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(signal)
        return button

    def set_countdown(self, remaining: int, total: int, color: str):
        self._ring.set_state(remaining / max(1, total),
                             format_time(remaining), "BREAK", color)

    def set_word(self, word: Word):
        # Clear the dynamic container (Noun/Verb widgets)
        while self.extra_container.count():
            item = self.extra_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._german.setText(word.german)
        self._english.setText(word.english)
        self._explanation.setText(word.explanation)
        
        if word.verb:
            self.extra_container.addWidget(VerbView(word.verb))
        elif word.noun:
            self.extra_container.addWidget(NounView(word.noun))
            
        self._example_de.setText(f"“{word.example_de}”")
        self._example_en.setText(word.example_en)

    def keyPressEvent(self, event):
        is_q = event.key() == Qt.Key_Q
        if is_q and (event.modifiers() & EMERGENCY_MODS) == EMERGENCY_MODS:
            self.emergency.emit()


class BreakScreen:
    """Covers every monitor, grabs input on X11 (if enabled), shows one word."""

    def __init__(self, speaker, on_emergency, settings):
        self._speaker = speaker
        self._on_emergency = on_emergency
        self._use_grab = False
        self._color = settings.break_color
        self._windows = []
        self._main = None
        self._total = 1
        self._grab_timer = QTimer()
        self._grab_timer.setInterval(150)
        self._grab_timer.timeout.connect(self._try_grab)
        self.configure(settings, allow_grab=True)

    def configure(self, settings, allow_grab=True):
        self._color = settings.break_color
        self._use_grab = allow_grab and settings.lock_input and is_x11()

    def show(self, word: Word, total_seconds: int, auto_speak: bool):
        self.hide()
        self._total = max(1, total_seconds)
        primary = QGuiApplication.primaryScreen()
        for screen in QGuiApplication.screens():
            if screen == primary:
                main = BreakOverlay(screen)
                main.set_word(word)
                main.set_countdown(self._total, self._total, self._color)
                main.speak_word.connect(
                    lambda: self._speaker.say(word.german))
                main.speak_sentence.connect(
                    lambda: self._speaker.say(word.example_de))
                main.emergency.connect(
                    lambda: QTimer.singleShot(0, self._on_emergency))
                self._main = main
                self._windows.append(main)
            else:
                self._windows.append(ScreenCover(screen))
        for window in self._windows:
            window.present()
        if self._use_grab:
            self._grab_timer.start()
        if auto_speak:
            self._speaker.say([word.german, word.example_de])

    def update(self, remaining: int):
        if not self._main:
            return
        self._main.set_countdown(remaining, self._total, self._color)
        for window in self._windows:  # stay above popups, panels, etc.
            window.raise_()

    def hide(self):
        self._grab_timer.stop()
        if self._main:
            handle = self._main.windowHandle()
            if handle:
                handle.setKeyboardGrabEnabled(False)
                handle.setMouseGrabEnabled(False)
        for window in self._windows:
            window.close()
            window.deleteLater()
        self._windows.clear()
        self._main = None

    def _try_grab(self):
        handle = self._main.windowHandle() if self._main else None
        if handle is None:
            return
        if handle.setKeyboardGrabEnabled(True) and handle.setMouseGrabEnabled(True):
            self._grab_timer.stop()
