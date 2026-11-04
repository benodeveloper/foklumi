import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.timer import Phase, PomodoroTimer
from core.vocab import VocabDeck
from ui.break_overlay import BreakScreen
from ui.main_window import MainWindow
from ui.speech import Speaker

AUTO_SPEAK = True  # say the word and sentence when a break starts


def main():
    app = QApplication(sys.argv)

    # --fast     10 s focus / 15 s break, for testing
    # --no-grab  cover the screen but don't grab keyboard and mouse
    if "--fast" in sys.argv:
        pomo = PomodoroTimer(focus_seconds=10, break_seconds=15)
    else:
        pomo = PomodoroTimer()  # 45 min / 2 min

    deck = VocabDeck()
    speaker = Speaker()
    if speaker.available:
        print(f"[speech] using {speaker.engine}")
    else:
        print(f"[speech] disabled: {speaker.problem}")

    overlay = BreakScreen(speaker, on_emergency=pomo.stop,
                          grab="--no-grab" not in sys.argv)
    window = MainWindow(
        on_start=pomo.start, on_stop=pomo.stop, on_skip=pomo.skip,
        on_quit=app.quit,
        durations={Phase.FOCUS: pomo.focus_seconds,
                   Phase.BREAK: pomo.break_seconds},
    )

    def on_phase(phase: Phase):
        window.set_phase(phase)
        if phase is Phase.BREAK:
            overlay.show(deck.next_word(), pomo.break_seconds, AUTO_SPEAK)
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
