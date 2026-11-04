import math
import time
from enum import Enum
from typing import Callable, Optional


class Phase(Enum):
    IDLE = "idle"
    FOCUS = "focus"
    BREAK = "break"


class PomodoroTimer:
    """Pure logic, no UI. Call tick() about once per second."""

    def __init__(self, focus_seconds=45 * 60, break_seconds=2 * 60,
                 clock=time.monotonic):
        self.focus_seconds = focus_seconds
        self.break_seconds = break_seconds
        self._clock = clock
        self._phase = Phase.IDLE
        self._deadline = 0.0
        self.auto_continue = True
        # The UI will plug into these two callbacks
        self.on_phase_changed: Optional[Callable[[Phase], None]] = None
        self.on_tick: Optional[Callable[[Phase, int], None]] = None

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def remaining(self) -> int:
        """Whole seconds left in the current phase."""
        if self._phase is Phase.IDLE:
            return 0
        return max(0, math.ceil(self._deadline - self._clock()))

    def start(self):
        self._enter(Phase.FOCUS)

    def stop(self):
        self._phase = Phase.IDLE
        if self.on_phase_changed:
            self.on_phase_changed(Phase.IDLE)

    def set_durations(self, focus_seconds: int, break_seconds: int):
        """Applies from the next phase on; the running countdown is unchanged."""
        self.focus_seconds = focus_seconds
        self.break_seconds = break_seconds

    def skip(self):
        """Jump to the next phase."""
        if self._phase is Phase.FOCUS:
            self._enter(Phase.BREAK)
        elif self._phase is Phase.BREAK:
            if self.auto_continue:
                self._enter(Phase.FOCUS)
            else:
                self.stop()

    def tick(self):
        if self._phase is Phase.IDLE:
            return
        if self.remaining == 0:
            self.skip()
        elif self.on_tick:
            self.on_tick(self._phase, self.remaining)

    def _enter(self, phase: Phase):
        self._phase = phase
        duration = self.focus_seconds if phase is Phase.FOCUS else self.break_seconds
        self._deadline = self._clock() + duration
        if self.on_phase_changed:
            self.on_phase_changed(phase)
        if self.on_tick:
            self.on_tick(phase, duration)
