import unittest
from core.timer import Phase, PomodoroTimer


class FakeClock:
    def __init__(self):
        self.t = 1000.0
    def __call__(self):
        return self.t
    def advance(self, seconds):
        self.t += seconds


class TimerTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.timer = PomodoroTimer(clock=self.clock)
        self.phases = []
        self.timer.on_phase_changed = self.phases.append

    def test_starts_idle(self):
        self.assertIs(self.timer.phase, Phase.IDLE)

    def test_focus_is_45_minutes(self):
        self.timer.start()
        self.assertIs(self.timer.phase, Phase.FOCUS)
        self.assertEqual(self.timer.remaining, 45 * 60)

    def test_countdown(self):
        self.timer.start()
        self.clock.advance(60)
        self.assertEqual(self.timer.remaining, 44 * 60)

    def test_break_starts_automatically_and_is_2_minutes(self):
        self.timer.start()
        self.clock.advance(45 * 60)
        self.timer.tick()
        self.assertIs(self.timer.phase, Phase.BREAK)
        self.assertEqual(self.timer.remaining, 120)

    def test_no_long_break_ever(self):
        self.timer.start()
        for _ in range(8):  # 8 focus/break rounds
            self.clock.advance(45 * 60)
            self.timer.tick()
            self.clock.advance(2 * 60)
            self.timer.tick()
        self.assertNotIn(Phase.IDLE, self.phases)
        self.assertEqual(self.phases.count(Phase.BREAK), 8)
        self.assertEqual(self.phases.count(Phase.FOCUS), 9)


if __name__ == "__main__":
    unittest.main()
