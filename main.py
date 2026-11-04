import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.timer import Phase, PomodoroTimer
from core.vocab import VocabDeck
from ui.break_overlay import BreakScreen
from ui.main_window import MainWindow

WORDS_PER_BREAK = 3


def main():
    app = QApplication(sys.argv)

    # python main.py --fast  ->  10 s focus, 15 s break, for testing
    if "--fast" in sys.argv:
        pomo = PomodoroTimer(focus_seconds=10, break_seconds=15)
    else:
        pomo = PomodoroTimer()  # 45 min / 2 min

    deck = VocabDeck()
    overlay = BreakScreen(on_escape=pomo.skip)  # Esc is temporary (Step 5)
    window = MainWindow(on_start=pomo.start, on_stop=pomo.stop,
                        on_skip=pomo.skip)

    def on_phase(phase: Phase):
        window.set_phase(phase)
        if phase is Phase.BREAK:
            overlay.show(deck.next_batch(WORDS_PER_BREAK), pomo.break_seconds)
        else:
            overlay.hide()

    def on_tick(phase: Phase, remaining: int):
        window.set_remaining(remaining)
        if phase is Phase.BREAK:
            overlay.update(remaining)

    pomo.on_phase_changed = on_phase
    pomo.on_tick = on_tick

    ticker = QTimer()
    ticker.timeout.connect(pomo.tick)
    ticker.start(500)  # tick twice a second; the timer uses a real deadline

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
