import tempfile
import unittest
from pathlib import Path

from core.settings import Settings


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "s.conf"

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_file_gives_defaults(self):
        s = Settings.load(self.path)
        self.assertEqual((s.focus_minutes, s.break_seconds), (45, 120))

    def test_roundtrip_keeps_every_type(self):
        original = Settings(focus_minutes=25, break_seconds=90,
                            focus_color="#ff0000", lock_input=False,
                            auto_speak=False, speech_speed=1.3,
                            start_in_background=True,
                            vocab_path="/tmp/my words, v2.json")
        original.save(self.path)
        loaded = Settings.load(self.path)
        self.assertEqual(loaded, original)

    def test_false_stays_false(self):
        Settings(always_on_top=False).save(self.path)
        self.assertFalse(Settings.load(self.path).always_on_top)

    def test_corrupt_file_gives_defaults(self):
        self.path.write_text("{not valid at all", encoding="utf-8")
        self.assertEqual(Settings.load(self.path).focus_minutes, 45)

    def test_bad_values_and_unknown_keys_are_ignored(self):
        self.path.write_text(
            "[General]\nfocus_minutes=abc\nbreak_seconds=5\nbogus=1\n",
            encoding="utf-8")
        s = Settings.load(self.path)
        self.assertEqual(s.focus_minutes, 45)   # kept the default
        self.assertEqual(s.break_seconds, 10)   # clamped to the minimum


if __name__ == "__main__":
    unittest.main()
