import unittest
from core.vocab import VocabDeck


class VocabTests(unittest.TestCase):
    def test_all_fields_present(self):
        deck = VocabDeck()
        for w in deck.next_batch(18):
            for field in (w.german, w.english, w.explanation, w.example_de, w.example_en):
                self.assertTrue(field.strip())

    def test_no_repeats_until_deck_is_used_up(self):
        deck = VocabDeck()
        first_round = [w.german for w in deck.next_batch(18)]
        self.assertEqual(len(set(first_round)), 18)


if __name__ == "__main__":
    unittest.main()
