import json
import unittest
from pathlib import Path

from tools.build_pipeline import (_generate_past, extract_noun,
                                  extract_verb_forms, validate_word)

ROOT = Path(__file__).resolve().parent.parent


SEIN_ENTRY = {
    "word": "sein",
    "pos": "verb",
    "senses": [{"tags": ["auxiliary"]}],
    "forms": [
        {"form": "bin", "tags": ["first-person", "indicative", "present",
                                 "singular"]},
        {"form": "bist", "tags": ["indicative", "present", "second-person",
                                  "singular"]},
        {"form": "ist", "tags": ["indicative", "present", "singular",
                                 "third-person"]},
        {"form": "sind", "tags": ["first-person", "indicative", "present",
                                  "plural"]},
        {"form": "seid", "tags": ["indicative", "plural", "present",
                                  "second-person"]},
        {"form": "sind", "tags": ["indicative", "plural", "present",
                                  "third-person"]},
        {"form": "war", "tags": ["past"]},
        {"form": "gewesen", "tags": ["participle", "past"]},
        {"form": "sein", "tags": ["auxiliary"]},
        {"form": "sei", "tags": ["first-person", "singular", "subjunctive",
                                 "subjunctive-i"]},
        {"form": "seist", "tags": ["second-person", "singular", "subjunctive",
                                   "subjunctive-i"]},
        {"form": "sei", "tags": ["singular", "subjunctive", "subjunctive-i",
                                 "third-person"]},
        {"form": "seien", "tags": ["first-person", "plural", "subjunctive",
                                   "subjunctive-i"]},
        {"form": "seiet", "tags": ["plural", "second-person", "subjunctive",
                                   "subjunctive-i"]},
        {"form": "seien", "tags": ["plural", "subjunctive", "subjunctive-i",
                                   "third-person"]},
        {"form": "wäre", "tags": ["first-person", "singular", "subjunctive",
                                  "subjunctive-ii"]},
        {"form": "wärst", "tags": ["second-person", "singular", "subjunctive",
                                   "subjunctive-ii"]},
        {"form": "wäre", "tags": ["singular", "subjunctive", "subjunctive-ii",
                                  "third-person"]},
        {"form": "wären", "tags": ["first-person", "plural", "subjunctive",
                                   "subjunctive-ii"]},
        {"form": "wärt", "tags": ["plural", "second-person", "subjunctive",
                                  "subjunctive-ii"]},
        {"form": "wären", "tags": ["plural", "subjunctive", "subjunctive-ii",
                                   "third-person"]},
        {"form": "sei", "tags": ["imperative", "second-person", "singular"]},
        {"form": "seid", "tags": ["imperative", "plural", "second-person"]},
    ],
}


class PipelineTests(unittest.TestCase):
    def test_noun_gender_comes_from_sense_tags(self):
        entry = {
            "word": "Apfel",
            "pos": "noun",
            "senses": [{"tags": ["masculine", "strong"]}],
            "forms": [
                {"form": "Äpfel", "tags": ["plural"]},
                {"form": "Apfels", "tags": ["genitive", "singular"]},
            ],
        }
        noun = extract_noun(entry, {})
        self.assertEqual(noun, {"article": "der", "plural": "Äpfel",
                                "genitive": "Apfels"})

    def test_verb_uses_correct_auxiliary_and_fills_tenses(self):
        verb = extract_verb_forms(SEIN_ENTRY)
        self.assertEqual(verb["auxiliary"], "sein")
        self.assertEqual(verb["participle"], "gewesen")
        self.assertEqual(verb["tenses"]["praesens"][0], "bin")
        self.assertEqual(verb["tenses"]["praeteritum"],
                         ["war", "warst", "war", "waren", "wart", "waren"])
        self.assertEqual(verb["tenses"]["konjunktiv1"][0], "sei")
        self.assertEqual(verb["tenses"]["konjunktiv2"][0], "wäre")
        self.assertEqual(verb["tenses"]["perfekt"][0], "bin gewesen")
        self.assertEqual(verb["imperative"]["Sie"], "seien Sie")

    def test_generate_past_handles_weak_and_strong_verbs(self):
        self.assertEqual(_generate_past("lernte"),
                         ["lernte", "lerntest", "lernte", "lernten",
                          "lerntet", "lernten"])
        self.assertEqual(_generate_past("ging"),
                         ["ging", "gingst", "ging", "gingen", "gingt",
                          "gingen"])
        self.assertEqual(_generate_past("fand"),
                         ["fand", "fandest", "fand", "fanden", "fandet",
                          "fanden"])

    def test_validation_rejects_missing_article(self):
        word = {
            "id": "x-noun", "lemma": "X", "pos": "noun", "level": "A1",
            "english": "x", "explanation": "x", "examples": [],
            "noun": {"article": "", "plural": "-", "genitive": "-"},
        }
        errors, warnings = validate_word(word)
        self.assertIn("X: missing definite article", errors)
        self.assertTrue(warnings)


class BundledVocabTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / "data" / "vocab.json"
        with open(path, encoding="utf-8") as f:
            self.data = json.load(f)
        self.words = {word["id"]: word for word in self.data["words"]}

    def test_contains_curated_words(self):
        self.assertEqual(self.data["schema"], 2)
        self.assertEqual(len(self.words), 19)
        self.assertEqual(len(self.words), len(self.data["words"]))
        for word in self.words.values():
            self.assertTrue(word["examples"])
            self.assertEqual(word["examples"][0]["source"], "curated")

    def test_bundled_vocab_matches_curated_source(self):
        curated_path = ROOT / "data" / "curated_words.json"
        with open(curated_path, encoding="utf-8") as f:
            curated = json.load(f)["words"]
        for item in curated:
            word_id = f"{item['lemma'].lower().replace(' ', '-')}-{item['pos']}"
            word = self.words[word_id]
            self.assertEqual(word["english"], item["english"])
            self.assertEqual(word["explanation"], item["explanation"])
            self.assertEqual(word["examples"][0]["de"], item["example_de"])
            self.assertEqual(word["examples"][0]["en"], item["example_en"])

    def test_nouns_have_articles_and_plurals(self):
        for word in self.words.values():
            if word["pos"] != "noun":
                continue
            self.assertIn(word["noun"]["article"], ("der", "die", "das"))
            self.assertNotEqual(word["noun"]["plural"], "-")

    def test_verbs_have_complete_tenses(self):
        for word in self.words.values():
            if word["pos"] != "verb":
                continue
            verb = word["verb"]
            self.assertIn(verb["auxiliary"], ("haben", "sein"))
            self.assertTrue(verb["participle"])
            for tense in ("praesens", "praeteritum", "konjunktiv1",
                          "konjunktiv2", "perfekt", "plusquamperfekt",
                          "futur1", "futur2"):
                forms = verb["tenses"][tense]
                self.assertEqual(len(forms), 6, f"{word['id']} {tense}")
                self.assertTrue(all(forms), f"{word['id']} {tense}")

    def test_sein_uses_sein_as_auxiliary(self):
        verb = self.words["sein-verb"]["verb"]
        self.assertEqual(verb["auxiliary"], "sein")
        self.assertEqual(verb["tenses"]["perfekt"][0], "bin gewesen")


if __name__ == "__main__":
    unittest.main()
