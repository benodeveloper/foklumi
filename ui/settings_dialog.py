from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QDialog,
                               QDialogButtonBox, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QSpinBox, QTabWidget, QVBoxLayout,
                               QWidget)

from core.settings import Settings


class ColorButton(QPushButton):
    def __init__(self, color: str):
        super().__init__()
        self.setFixedWidth(90)
        self.set_color(color)
        self.clicked.connect(self._pick)

    def set_color(self, color: str):
        self._color = color
        self.setText(color)
        c = QColor(color)
        fg = "#000" if c.lightness() > 128 else "#fff"
        self.setStyleSheet(f"background:{color}; color:{fg}; padding:4px;")

    def color(self) -> str:
        return self._color

    def _pick(self):
        chosen = QColorDialog.getColor(QColor(self._color), self)
        if chosen.isValid():
            self.set_color(chosen.name())


class PathEdit(QWidget):
    def __init__(self, value: str, file_filter: str):
        super().__init__()
        self._filter = file_filter
        self.edit = QLineEdit(value)
        button = QPushButton("Browse…")
        button.clicked.connect(self._browse)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.edit)
        row.addWidget(button)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose file", "",
                                              self._filter)
        if path:
            self.edit.setText(path)

    def text(self) -> str:
        return self.edit.text().strip()


class SettingsDialog(QDialog):
    def __init__(self, current: Settings, defaults: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Foklumi settings")
        self.setMinimumWidth(480)
        self._defaults = defaults
        self._result = current

        # ----- timing -----
        self.focus = QSpinBox(); self.focus.setRange(1, 240)
        self.focus.setSuffix(" min")
        self.brk = QSpinBox(); self.brk.setRange(10, 3600)
        self.brk.setSuffix(" s")
        self.auto_start = QCheckBox("Start the next focus session automatically")
        timing = QFormLayout()
        timing.addRow("Focus length", self.focus)
        timing.addRow("Break length", self.brk)
        timing.addRow("", self.auto_start)
        note = QLabel("Timing changes apply from the next phase.")
        note.setStyleSheet("color: gray;")
        timing.addRow("", note)

        # ----- break screen -----
        self.auto_speak = QCheckBox("Say the word and sentence when a break starts")
        self.speed = QDoubleSpinBox(); self.speed.setRange(0.5, 2.5)
        self.speed.setSingleStep(0.1)
        self.lock = QCheckBox("Lock keyboard and mouse during breaks (X11 only)")
        self.model = PathEdit("", "Piper model (*.onnx);;All files (*)")
        speed_note = QLabel("Speed: 1.0 is normal, higher is slower.")
        speed_note.setStyleSheet("color: gray;")
        brk = QFormLayout()
        brk.addRow("", self.auto_speak)
        brk.addRow("Speech speed", self.speed)
        brk.addRow("", speed_note)
        brk.addRow("Piper model", self.model)
        brk.addRow("", self.lock)

        # ----- appearance -----
        self.c_focus = ColorButton(current.focus_color)
        self.c_break = ColorButton(current.break_color)
        self.c_idle = ColorButton(current.idle_color)
        self.size = QSpinBox(); self.size.setRange(160, 400)
        self.size.setSuffix(" px")
        self.on_top = QCheckBox("Keep the timer above other windows")
        look = QFormLayout()
        look.addRow("Focus color", self.c_focus)
        look.addRow("Break color", self.c_break)
        look.addRow("Idle color", self.c_idle)
        look.addRow("Timer size", self.size)
        look.addRow("", self.on_top)

        # ----- vocabulary -----
        self.vocab = PathEdit("", "Vocabulary JSON (*.json);;All files (*)")
        vnote = QLabel("Leave empty for the built-in list. A custom file uses "
                       "the same format as data/vocab.json.")
        vnote.setWordWrap(True)
        vnote.setStyleSheet("color: gray;")
        vocab = QFormLayout()
        vocab.addRow("Vocabulary file", self.vocab)
        vocab.addRow("", vnote)

        tabs = QTabWidget()
        for title, form in (("Timing", timing), ("Break screen", brk),
                            ("Appearance", look), ("Vocabulary", vocab)):
            page = QWidget()
            page.setLayout(form)
            tabs.addTab(page, title)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        reset = buttons.addButton("Reset to defaults",
                                  QDialogButtonBox.ResetRole)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        reset.clicked.connect(lambda: self._load(self._defaults))

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

        self._load(current)

    def _load(self, s: Settings):
        self.focus.setValue(s.focus_minutes)
        self.brk.setValue(s.break_seconds)
        self.auto_start.setChecked(s.auto_start_focus)
        self.auto_speak.setChecked(s.auto_speak)
        self.speed.setValue(s.speech_speed)
        self.lock.setChecked(s.lock_input)
        self.model.edit.setText(s.piper_model)
        self.c_focus.set_color(s.focus_color)
        self.c_break.set_color(s.break_color)
        self.c_idle.set_color(s.idle_color)
        self.size.setValue(s.timer_size)
        self.on_top.setChecked(s.always_on_top)
        self.vocab.edit.setText(s.vocab_path)

    def _accept(self):
        s = replace(
            self._result,
            focus_minutes=self.focus.value(),
            break_seconds=self.brk.value(),
            auto_start_focus=self.auto_start.isChecked(),
            auto_speak=self.auto_speak.isChecked(),
            speech_speed=self.speed.value(),
            lock_input=self.lock.isChecked(),
            piper_model=self.model.text(),
            focus_color=self.c_focus.color(),
            break_color=self.c_break.color(),
            idle_color=self.c_idle.color(),
            timer_size=self.size.value(),
            always_on_top=self.on_top.isChecked(),
            vocab_path=self.vocab.text(),
        )
        s.clamp()
        self._result = s
        self.accept()

    def result_settings(self) -> Settings:
        return self._result
