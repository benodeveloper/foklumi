from dataclasses import dataclass, fields

from PySide6.QtCore import QSettings

ORGANIZATION = "foklumi"
APPLICATION = "foklumi"


def _store(path=None) -> QSettings:
    """The platform's normal settings store (a .conf file in ~/.config on
    Linux, the registry on Windows, a plist on macOS). A path forces an INI
    file at that location, which is what the tests use."""
    if path is not None:
        return QSettings(str(path), QSettings.Format.IniFormat)
    return QSettings(ORGANIZATION, APPLICATION)


def _coerce(default, raw):
    """Turn whatever QSettings returned into the type of the default.
    INI files store everything as text, so "false" must become False."""
    if isinstance(raw, (list, tuple)):  # INI turns "a,b" into a list
        raw = ",".join(str(x) for x in raw)
    if isinstance(default, bool):
        if isinstance(raw, str):
            return raw.strip().lower() in ("true", "1", "yes", "on")
        return bool(raw)
    if isinstance(default, int):
        return int(float(raw))
    if isinstance(default, float):
        return float(raw)
    return "" if raw is None else str(raw)


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
    start_in_background: bool = False
    # vocabulary / speech
    vocab_path: str = ""
    piper_model: str = ""

    @staticmethod
    def location(path=None) -> str:
        """Where the settings are stored (for messages and debugging)."""
        return _store(path).fileName()

    @classmethod
    def load(cls, path=None) -> "Settings":
        s = cls()
        store = _store(path)
        for field in fields(cls):
            if store.contains(field.name):
                try:
                    default = getattr(s, field.name)
                    setattr(s, field.name,
                            _coerce(default, store.value(field.name)))
                except (TypeError, ValueError):
                    pass  # keep the default for a bad value
        s.clamp()
        return s

    def clamp(self):
        self.focus_minutes = min(240, max(1, self.focus_minutes))
        self.break_seconds = min(3600, max(10, self.break_seconds))
        self.speech_speed = min(2.5, max(0.5, self.speech_speed))
        self.timer_size = min(400, max(160, self.timer_size))

    def save(self, path=None):
        """Writes every setting to disk right away. Raises OSError if the
        settings file could not be written."""
        store = _store(path)
        for field in fields(self):
            store.setValue(field.name, getattr(self, field.name))
        store.sync()
        if store.status() != QSettings.Status.NoError:
            raise OSError(f"could not write settings to {store.fileName()}")
