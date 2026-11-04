import time
from core.timer import Phase, PomodoroTimer
from core.vocab import VocabDeck

deck = VocabDeck()
timer = PomodoroTimer(focus_seconds=6, break_seconds=4)


def on_phase(phase):
    print(f"\n=== {phase.value.upper()} ===")
    if phase is Phase.BREAK:
        w = deck.next_word()
        print(f"{w.german}  =  {w.english}")
        print(f"  {w.explanation}")
        print(f"  DE: {w.example_de}")
        print(f"  EN: {w.example_en}")


timer.on_phase_changed = on_phase
timer.on_tick = lambda phase, left: print(f"{phase.value}: {left}s", end="\r")

timer.start()
try:
    while True:
        time.sleep(1)
        timer.tick()
except KeyboardInterrupt:
    print("\nbye")
