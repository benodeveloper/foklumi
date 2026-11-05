from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog,
                               QDialogButtonBox, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QKeySequenceEdit,
                               QLabel, QLineEdit, QMessageBox, QPushButton,
                               QSpinBox, QTabWidget, QVBoxLayout, QWidget)

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


class FetchCandidatesWorker(QObject):
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, count: int, pos: str, output: Path,
                 allow_missing_examples: bool):
        super().__init__()
        self._count = count
        self._pos = pos
        self._output = output
        self._allow_missing = allow_missing_examples

    def run(self):
        try:
            import json
            import time
            import requests
            from tools.fetch_random_words import (
                DEFAULT_CURATED, DEFAULT_KAIKKI, DEFAULT_TATOEBA,
                USER_AGENT, _distribute_counts, _valid_title,
                build_candidate, build_sentence_index, fetch_random_titles,
                load_curated, load_kaikki_titles, load_tatoeba)
        except Exception as e:
            self.finished.emit(False, f"Missing dependency or import error: {e}")
            return

        if not DEFAULT_KAIKKI.exists():
            self.finished.emit(
                False, f"Missing {DEFAULT_KAIKKI}.\nRun tools/download_data.py first.")
            return
        curated = load_curated(DEFAULT_CURATED)
        existing_keys = {(w["lemma"].lower(), w["pos"]) for w in curated}
        sentences = load_tatoeba(DEFAULT_TATOEBA)
        if not sentences and not self._allow_missing:
            self.finished.emit(
                False,
                f"Missing or empty {DEFAULT_TATOEBA}.\nRun tools/download_data.py "
                "first, or enable 'Allow missing examples'.")
            return
        sentence_index = build_sentence_index(sentences) if sentences else None
        pos_list = [p.strip() for p in self._pos.split(",") if p.strip()]
        desired = _distribute_counts(self._count, pos_list)
        buckets = {pos: [] for pos in pos_list}
        seen_titles = set()
        used_examples = set()
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        try:
            for batch in range(1, 11):
                titles = fetch_random_titles(session, 500, 30)
                new_titles = []
                for title in titles:
                    key = title.lower()
                    if key in seen_titles:
                        continue
                    seen_titles.add(key)
                    if _valid_title(title):
                        new_titles.append(title)
                if new_titles:
                    entries_by_title = load_kaikki_titles(
                        DEFAULT_KAIKKI, {t.lower() for t in new_titles})
                    for title in new_titles:
                        entries = entries_by_title.get(title.lower(), [])
                        if not entries:
                            continue
                        for pos in pos_list:
                            if len(buckets[pos]) >= desired[pos]:
                                continue
                            candidate = build_candidate(
                                title, entries, pos, sentences, used_examples,
                                existing_keys, self._allow_missing,
                                sentence_index=sentence_index)
                            if candidate:
                                buckets[pos].append(candidate)
                progress = ", ".join(
                    f"{pos}: {len(buckets[pos])}/{desired[pos]}" for pos in pos_list)
                self.progress.emit(f"Batch {batch}/10 — {progress}")
                if all(len(buckets[pos]) >= desired[pos] for pos in pos_list):
                    break
                time.sleep(0.5)
        except Exception as e:
            self.finished.emit(False, f"Fetch failed: {e}")
            return

        candidates = [c for pos in pos_list for c in buckets[pos]]
        try:
            self._output.parent.mkdir(parents=True, exist_ok=True)
            with open(self._output, "w", encoding="utf-8") as f:
                json.dump({"schema": 1, "source": "https://de.wiktionary.org/",
                           "words": candidates}, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except OSError as e:
            self.finished.emit(False, f"Could not write {self._output}: {e}")
            return
        msg = f"Wrote {len(candidates)} candidates to {self._output}."
        if len(candidates) < self._count:
            msg += f"\nOnly found {len(candidates)} of {self._count} requested."
        self.finished.emit(True, msg)


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
        self.emergency = QKeySequenceEdit()
        self.emergency.setMaximumSequenceLength(1)
        speed_note = QLabel("Speed: 1.0 is normal, higher is slower.")
        speed_note.setStyleSheet("color: gray;")
        key_note = QLabel("Key that ends a break, for example Esc or "
                          "Ctrl+Alt+Shift+Q. Press it in the field above.")
        key_note.setWordWrap(True)
        key_note.setStyleSheet("color: gray;")
        brk = QFormLayout()
        brk.addRow("", self.auto_speak)
        brk.addRow("Speech speed", self.speed)
        brk.addRow("", speed_note)
        brk.addRow("Piper model", self.model)
        brk.addRow("", self.lock)
        brk.addRow("Emergency exit", self.emergency)
        brk.addRow("", key_note)

        # ----- appearance -----
        self.c_focus = ColorButton(current.focus_color)
        self.c_break = ColorButton(current.break_color)
        self.c_idle = ColorButton(current.idle_color)
        self.size = QSpinBox(); self.size.setRange(160, 400)
        self.size.setSuffix(" px")
        self.on_top = QCheckBox("Keep the timer above other windows")
        self.background = QCheckBox(
            "Start hidden in the background (needs a system tray)")
        bg_note = QLabel("Click the tray icon to show the timer again.")
        bg_note.setStyleSheet("color: gray;")
        look = QFormLayout()
        look.addRow("Focus color", self.c_focus)
        look.addRow("Break color", self.c_break)
        look.addRow("Idle color", self.c_idle)
        look.addRow("Timer size", self.size)
        look.addRow("", self.on_top)
        look.addRow("", self.background)
        look.addRow("", bg_note)

        # ----- vocabulary -----
        self.vocab = PathEdit("", "Vocabulary JSON (*.json);;All files (*)")
        vnote = QLabel("Leave empty for the built-in list. A custom file uses "
                       "the same format as data/vocab.json.")
        vnote.setWordWrap(True)
        vnote.setStyleSheet("color: gray;")
        self.fetch_count = QSpinBox(); self.fetch_count.setRange(1, 200)
        self.fetch_count.setValue(20)
        self.fetch_pos = QComboBox()
        self.fetch_pos.addItems([
            "noun,verb,adj,adv", "noun,verb,adj", "noun", "verb", "adj", "adv"])
        self.fetch_missing = QCheckBox("Allow candidates without example sentences")
        self.fetch_button = QPushButton("Fetch random candidates…")
        self.fetch_button.clicked.connect(self._start_fetch)
        self.fetch_status = QLabel("")
        self.fetch_status.setWordWrap(True)
        self.fetch_status.setStyleSheet("color: gray;")
        self._fetch_thread = None
        self._fetch_worker = None
        fetch_row = QHBoxLayout()
        fetch_row.addWidget(self.fetch_count)
        fetch_row.addWidget(self.fetch_pos)
        fetch_row.addWidget(self.fetch_button)
        fetch_note = QLabel(
            "Downloads random German words from free/open sources (Wiktionary "
            "API, local Kaikki/Tatoeba) into data/random_candidates.json for "
            "review. Requires tools/download_data.py data. Runs in background.")
        fetch_note.setWordWrap(True)
        fetch_note.setStyleSheet("color: gray;")
        vocab = QFormLayout()
        vocab.addRow("Vocabulary file", self.vocab)
        vocab.addRow("", vnote)
        vocab.addRow("Fetch count / POS", fetch_row)
        vocab.addRow("", self.fetch_missing)
        vocab.addRow("", self.fetch_status)
        vocab.addRow("", fetch_note)

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
        self.emergency.setKeySequence(QKeySequence(s.emergency_key))
        self.c_focus.set_color(s.focus_color)
        self.c_break.set_color(s.break_color)
        self.c_idle.set_color(s.idle_color)
        self.size.setValue(s.timer_size)
        self.on_top.setChecked(s.always_on_top)
        self.background.setChecked(s.start_in_background)
        self.vocab.edit.setText(s.vocab_path)

    def _start_fetch(self):
        if self._fetch_thread is not None and self._fetch_thread.isRunning():
            return
        try:
            from tools.fetch_random_words import DEFAULT_OUTPUT
        except Exception:
            DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "random_candidates.json"
        self.fetch_button.setEnabled(False)
        self.fetch_status.setText("Starting fetch…")
        self._fetch_thread = QThread(self)
        self._fetch_worker = FetchCandidatesWorker(
            self.fetch_count.value(), self.fetch_pos.currentText(),
            DEFAULT_OUTPUT, self.fetch_missing.isChecked())
        self._fetch_worker.moveToThread(self._fetch_thread)
        self._fetch_thread.started.connect(self._fetch_worker.run)
        self._fetch_worker.progress.connect(self.fetch_status.setText)
        self._fetch_worker.finished.connect(self._fetch_finished)
        self._fetch_worker.finished.connect(self._fetch_thread.quit)
        self._fetch_worker.finished.connect(self._fetch_worker.deleteLater)
        self._fetch_thread.finished.connect(self._fetch_thread.deleteLater)
        self._fetch_thread.start()

    def _fetch_finished(self, ok: bool, message: str):
        self.fetch_button.setEnabled(True)
        self.fetch_status.setText(message if ok else f"Error: {message}")
        if ok:
            QMessageBox.information(self, "Fetch candidates", message)
        else:
            QMessageBox.warning(self, "Fetch candidates", message)

    def _accept(self):
        emergency_key = self.emergency.keySequence().toString(
            QKeySequence.SequenceFormat.PortableText) or "Esc"
        s = replace(
            self._result,
            focus_minutes=self.focus.value(),
            break_seconds=self.brk.value(),
            auto_start_focus=self.auto_start.isChecked(),
            auto_speak=self.auto_speak.isChecked(),
            speech_speed=self.speed.value(),
            lock_input=self.lock.isChecked(),
            emergency_key=emergency_key,
            piper_model=self.model.text(),
            focus_color=self.c_focus.color(),
            break_color=self.c_break.color(),
            idle_color=self.c_idle.color(),
            timer_size=self.size.value(),
            always_on_top=self.on_top.isChecked(),
            start_in_background=self.background.isChecked(),
            vocab_path=self.vocab.text(),
        )
        s.clamp()
        self._result = s
        self.accept()

    def result_settings(self) -> Settings:
        return self._result
