import unittest

from tools.fetch_random_words import (_distribute_counts, _english_gloss,
                                      _is_lemma_entry, _valid_title,
                                      build_candidate)

HAUS_ENTRY = {
    "word": "Haus",
    "pos": "noun",
    "senses": [{"tags": ["neuter", "strong"], "glosses": ["house"]}],
    "forms": [
        {"form": "Häuser", "tags": ["plural"]},
        {"form": "Hauses", "tags": ["genitive", "singular"]},
    ],
}

HAUS_SENTENCE = {
    "de": "Das Haus ist sehr groß.",
    "en": "The house is very big.",
    "source": "tatoeba:1",
}

FORM_OF_ENTRY = {
    "word": "Häuser",
    "pos": "noun",
    "senses": [{
        "tags": ["form-of", "plural"],
        "form_of": [{"word": "Haus"}],
        "glosses": ["plural of Haus"],
    }],
}


class FetchRandomTests(unittest.TestCase):
    def test_valid_title_accepts_single_words(self):
        self.assertTrue(_valid_title("Haus"))
        self.assertTrue(_valid_title("Straßenbahn"))
        self.assertTrue(_valid_title("E-Mail"))
        self.assertFalse(_valid_title("gut betuchter"))
        self.assertFalse(_valid_title("Haus,"))

    def test_form_of_entries_are_rejected(self):
        self.assertTrue(_is_lemma_entry(HAUS_ENTRY))
        self.assertFalse(_is_lemma_entry(FORM_OF_ENTRY))
        self.assertIsNone(build_candidate(
            "Häuser", [FORM_OF_ENTRY], "noun", [HAUS_SENTENCE], set(), set()))

    def test_english_gloss_skips_form_of_senses(self):
        self.assertEqual(_english_gloss(HAUS_ENTRY), "house")
        self.assertEqual(_english_gloss(FORM_OF_ENTRY), "")

    def test_distribute_counts_is_balanced(self):
        self.assertEqual(
            _distribute_counts(20, ["noun", "verb", "adj"]),
            {"noun": 7, "verb": 7, "adj": 6})
        self.assertEqual(
            _distribute_counts(2, ["noun", "verb", "adj"]),
            {"noun": 1, "verb": 1, "adj": 0})

    def test_build_candidate_keeps_article_and_example(self):
        candidate = build_candidate(
            "Haus", [HAUS_ENTRY], "noun", [HAUS_SENTENCE], set(), set())
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["lemma"], "Haus")
        self.assertEqual(candidate["article"], "das")
        self.assertEqual(candidate["english"], "house")
        self.assertEqual(candidate["example_source"], "tatoeba:1")

    def test_build_candidate_skips_existing_and_missing_examples(self):
        self.assertIsNone(build_candidate(
            "Haus", [HAUS_ENTRY], "noun", [HAUS_SENTENCE], set(),
            {("haus", "noun")}))
        self.assertIsNone(build_candidate(
            "Haus", [HAUS_ENTRY], "noun", [], set(), set()))
        self.assertIsNotNone(build_candidate(
            "Haus", [HAUS_ENTRY], "noun", [], set(), set(),
            allow_missing_examples=True))


if __name__ == "__main__":
    unittest.main()
