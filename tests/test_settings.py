import json
import tempfile
import unittest
from pathlib import Path

from core.settings import Settings


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "s.json"

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_file_gives_defaults(self):
        s = Settings.load(self.path)
        self.assertEqual((s.focus_minutes, s.break_seconds), (45, 120))

    def test_roundtrip(self):
        s = Settings(focus_minutes=25, focus_color="#ff0000")
        s.save(self.path)
        loaded = Settings.load(self.path)
        self.assertEqual(loaded.focus_minutes, 25)
        self.assertEqual(loaded.focus_color, "#ff0000")

    def test_corrupt_file_gives_defaults(self):
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(Settings.load(self.path).focus_minutes, 45)

    def test_bad_values_and_unknown_keys_are_ignored(self):
        self.path.write_text(json.dumps(
            {"focus_minutes": "abc", "break_seconds": 5, "bogus": 1}))
        s = Settings.load(self.path)
        self.assertEqual(s.focus_minutes, 45)   # kept default
        self.assertEqual(s.break_seconds, 10)   # clamped to the minimum


if __name__ == "__main__":
    unittest.main()
