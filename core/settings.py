import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path


def settings_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    if os.name == "nt":
        base = os.environ.get("APPDATA") or base
    return Path(base) / "foklumi" / "settings.json"


@dataclass
class Settings:
    # timing
    focus_minutes: int = 45
    break_seconds: int = 120
    auto_start_focus: bool = True
    # break screen
    auto_speak: bool = True
    speech_speed: float = 1.0        # Piper length-scale: bigger = slower
    lock_input: bool = True
    # appearance
    focus_color: str = "#38bdf8"
    break_color: str = "#34d399"
    idle_color: str = "#64748b"
    timer_size: int = 240
    always_on_top: bool = True
    # vocabulary / speech
    vocab_path: str = ""
    piper_model: str = ""

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or settings_path()
        s = cls()
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            return s
        if not isinstance(raw, dict):
            return s
        for field in fields(cls):
            if field.name in raw:
                try:
                    default = getattr(s, field.name)
                    value = raw[field.name]
                    if isinstance(default, bool):
                        value = bool(value)
                    elif isinstance(default, int):
                        value = int(value)
                    elif isinstance(default, float):
                        value = float(value)
                    else:
                        value = str(value)
                    setattr(s, field.name, value)
                except (TypeError, ValueError):
                    pass  # keep the default for a bad value
        s.clamp()
        return s

    def clamp(self):
        self.focus_minutes = min(240, max(1, self.focus_minutes))
        self.break_seconds = min(3600, max(10, self.break_seconds))
        self.speech_speed = min(2.5, max(0.5, self.speech_speed))
        self.timer_size = min(400, max(160, self.timer_size))

    def save(self, path: Path | None = None):
        path = path or settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
        tmp.replace(path)  # atomic, so a crash never leaves a half file
