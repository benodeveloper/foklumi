import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.settings import Settings
from core.timer import Phase, PomodoroTimer
from core.vocab import VocabDeck
from ui.break_overlay import BreakScreen
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from ui.speech import Speaker


def main():
    app = QApplication(sys.argv)

    # --fast     10 s focus / 15 s break, ignores saved timing (for testing)
    # --no-grab  cover the screen but never grab keyboard and mouse
    fast = "--fast" in sys.argv
    allow_grab = "--no-grab" not in sys.argv

    settings = Settings.load()

    def durations(s: Settings):
        return (10, 15) if fast else (s.focus_minutes * 60, s.break_seconds)

    focus_s, break_s = durations(settings)
    pomo = PomodoroTimer(focus_seconds=focus_s, break_seconds=break_s)
    pomo.auto_continue = settings.auto_start_focus

    deck = VocabDeck(settings.vocab_path or None)
    if deck.warning:
        print(f"[vocab] {deck.warning}")

    speaker = Speaker(settings.piper_model, settings.speech_speed)
    print(f"[speech] using {speaker.engine}" if speaker.available
          else f"[speech] disabled: {speaker.problem}")

    overlay = BreakScreen(speaker, on_emergency=pomo.stop, settings=settings)
    overlay.configure(settings, allow_grab)

    state = {"settings": settings}

    def open_settings():
        current = state["settings"]
        dialog = SettingsDialog(current, Settings(), parent=window)
        if dialog.exec() != dialog.Accepted:
            return
        new = dialog.result_settings()
        new.save()
        state["settings"] = new
        window.apply_settings(new)
        overlay.configure(new, allow_grab)
        speaker.reconfigure(new.piper_model, new.speech_speed)
        pomo.auto_continue = new.auto_start_focus
        f, b = durations(new)
        pomo.set_durations(f, b)
        if new.vocab_path != current.vocab_path:
            nonlocal_deck[0] = VocabDeck(new.vocab_path or None)
            if nonlocal_deck[0].warning:
                print(f"[vocab] {nonlocal_deck[0].warning}")

    nonlocal_deck = [deck]  # a list so open_settings can swap the deck

    window = MainWindow(
        settings, on_start=pomo.start, on_stop=pomo.stop, on_skip=pomo.skip,
        on_settings=open_settings, on_quit=app.quit)

    def on_phase(phase: Phase):
        window.set_phase(phase)
        if phase is Phase.BREAK:
            s = state["settings"]
            overlay.show(nonlocal_deck[0].next_word(), pomo.break_seconds,
                         s.auto_speak)
        else:
            overlay.hide()
            speaker.stop()

    def on_tick(phase: Phase, remaining: int):
        window.set_remaining(remaining)
        if phase is Phase.BREAK:
            overlay.update(remaining)

    pomo.on_phase_changed = on_phase
    pomo.on_tick = on_tick

    ticker = QTimer()
    ticker.timeout.connect(pomo.tick)
    ticker.start(500)

    window.show()
    app.aboutToQuit.connect(speaker.stop)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
