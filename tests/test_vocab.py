import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from core.vocab import VocabDeck

TEST_SCHEMA = {
    "schema": 2,
    "words": [
        {
            "id": "test-1", "lemma": "eins", "pos": "noun", "level": "A1",
            "english": "one", "explanation": "num", "examples": []
        },
        {
            "id": "test-2", "lemma": "zwei", "pos": "noun", "level": "A1",
            "english": "two", "explanation": "num", "examples": []
        }
    ]
}

class TestVocabDeck(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.json_path = Path(self.tmp_dir.name) / "test_vocab.json"
        self.db_path = Path(self.tmp_dir.name) / "progress.db"
        
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(TEST_SCHEMA, f)
            
        self.deck = VocabDeck(path=self.json_path, db_path=self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_loads_schema_v2(self):
        self.assertIsNone(self.deck.warning)
        self.assertEqual(len(self.deck._words), 2)
        self.assertEqual(self.deck._words["test-1"].english, "one")

    def test_rotation_prioritizes_unseen(self):
        w1 = self.deck.next_word()
        w2 = self.deck.next_word()
        
        # Both should be drawn before any repeats
        drawn_ids = {w1.id, w2.id}
        self.assertEqual(drawn_ids, {"test-1", "test-2"})

    def test_rotation_falls_back_to_oldest(self):
        # Consume both unseen words
        w1 = self.deck.next_word()
        w2 = self.deck.next_word()
        
        # Next pull must return the oldest seen (w1)
        w3 = self.deck.next_word()
        self.assertEqual(w3.id, w1.id)

if __name__ == "__main__":
    unittest.main()
