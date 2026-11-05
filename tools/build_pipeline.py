"""Build data/vocab.json from curated word data plus Kaikki grammar.

The curated file owns the learner-facing text (translation, explanation and
example). Kaikki supplies noun and verb grammar. Tatoeba is only used for
words that do not have a curated example yet.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
DEFAULT_CURATED = ROOT / "data" / "curated_words.json"
DEFAULT_KAIKKI = TOOLS / "kaikki.jsonl"
DEFAULT_TATOEBA = TOOLS / "tatoeba.tsv"
DEFAULT_OUT = ROOT / "data" / "vocab.json"

PRONOUNS = ["ich", "du", "er/sie/es", "wir", "ihr", "sie/Sie"]
PERSON_INDEX = {"first-person": 0, "second-person": 1, "third-person": 2}
GENDER_TAGS = ("masculine", "feminine", "neuter")
ARTICLE_BY_GENDER = {"masculine": "der", "feminine": "die", "neuter": "das"}
BAD_SENSE_TAGS = {
    "archaic", "dated", "dialectal", "misspelling", "nonstandard",
    "obsolete", "rare",
}
BAD_FORM_TAGS = {
    "alternative", "archaic", "auxiliary", "dated", "dialectal",
    "inflection-template", "misspelling", "multiword-construction",
    "nonstandard", "obsolete", "rare", "table-tags",
}
WERDEN = ["werde", "wirst", "wird", "werden", "werdet", "werden"]
WUERDE = ["würde", "würdest", "würde", "würden", "würdet", "würden"]
AUX_PRESENT = {
    "haben": ["habe", "hast", "hat", "haben", "habt", "haben"],
    "sein": ["bin", "bist", "ist", "sind", "seid", "sind"],
}
AUX_PAST = {
    "haben": ["hatte", "hattest", "hatte", "hatten", "hattet", "hatten"],
    "sein": ["war", "warst", "war", "waren", "wart", "waren"],
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _tags(item: dict) -> set:
    return set(item.get("tags", []))


def _entry_tags(entry: dict) -> set:
    """Kaikki sometimes puts gender and other tags on a sense, not the entry."""
    tags = set(entry.get("tags", []))
    for sense in entry.get("senses", []):
        tags.update(sense.get("tags", []))
    return tags


def _is_form_of_sense(sense: dict) -> bool:
    tags = set(sense.get("tags", []))
    return ("form-of" in tags or "alt-of" in tags
            or bool(sense.get("form_of")) or bool(sense.get("alt_of")))


def _is_quality_sense(sense: dict) -> bool:
    return (not _is_form_of_sense(sense)
            and not (_tags(sense) & BAD_SENSE_TAGS))


def _slot(tags: Iterable[str]) -> Optional[int]:
    tags = set(tags)
    person = next((PERSON_INDEX[t] for t in tags if t in PERSON_INDEX), None)
    if person is None:
        return None
    if "singular" in tags:
        return person
    if "plural" in tags:
        return person + 3
    return None


def _tense(tags: Iterable[str]) -> Optional[str]:
    tags = set(tags)
    if "multiword-construction" in tags:
        return None
    if "subjunctive-i" in tags:
        return "konjunktiv1"
    if "subjunctive-ii" in tags:
        return "konjunktiv2"
    if "present" in tags and "indicative" in tags:
        return "praesens"
    if "past" in tags and "indicative" in tags:
        return "praeteritum"
    return None


def _first_form(forms: List[dict], required: set) -> str:
    for form in forms:
        if required <= _tags(form):
            text = _clean(form.get("form", ""))
            if text:
                return text
    return ""


def _generate_past(base: str) -> List[str]:
    """Fill in the six Präteritum forms from the dictionary's base past form.

    Kaikki gives one past form (usually the third person singular) for many
    verbs, so regular endings are used to complete the table.
    """
    if base.endswith("te"):
        # Weak and mixed verbs: lernte -> lernte, lerntest, lernte, ...
        return [base, base + "st", base, base + "n", base + "t", base + "n"]
    if base.endswith(("d", "t")):
        du, ihr = base + "est", base + "et"
    elif base.endswith(("s", "ß", "z")):
        du, ihr = base + "t", base + "t"
    else:
        du, ihr = base + "st", base + "t"
    return [base, du, base, base + "en", ihr, base + "en"]


def _infinitive_stem(infinitive: str) -> str:
    if infinitive.endswith("en"):
        return infinitive[:-2]
    if infinitive.endswith("n"):
        return infinitive[:-1]
    return infinitive


def extract_noun(entry: dict, curated: dict) -> dict:
    tags = _entry_tags(entry)
    gender = next((g for g in GENDER_TAGS if g in tags), "")
    article = curated.get("article") or ARTICLE_BY_GENDER.get(gender, "")
    forms = entry.get("forms", [])
    plural = curated.get("plural") or _first_form(forms, {"plural"}) or "-"
    genitive = (curated.get("genitive")
                or _first_form(forms, {"genitive", "singular"}) or "-")
    return {"article": article, "plural": plural, "genitive": genitive}


def extract_verb_forms(entry: dict) -> dict:
    word = _clean(entry.get("word", ""))
    forms = entry.get("forms", [])
    reflexive = (word.lower().startswith("sich ")
                 or "reflexive" in _entry_tags(entry))
    verb = {
        "auxiliary": "haben",
        "separable": False,
        "reflexive": reflexive,
        "participle": "",
        "pronouns": PRONOUNS,
        "tenses": {
            "praesens": [""] * 6,
            "praeteritum": [""] * 6,
            "konjunktiv1": [""] * 6,
            "konjunktiv2": [""] * 6,
        },
        "imperative": {"du": "", "ihr": "", "Sie": ""},
    }

    infinitive = word
    past_base = ""

    for form in forms:
        tags = _tags(form)
        text = _clean(form.get("form", ""))
        if not text or "table-tags" in tags or "inflection-template" in tags:
            continue
        if "multiword-construction" in tags:
            continue
        if "auxiliary" in tags:
            if text in AUX_PRESENT:
                verb["auxiliary"] = text
            continue
        if "infinitive" in tags:
            if "infinitive-zu" not in tags:
                infinitive = text
            continue
        if "participle" in tags and "past" in tags:
            verb["participle"] = text
            continue
        if "imperative" in tags:
            if "second-person" in tags and "singular" in tags:
                verb["imperative"]["du"] = text
            elif "second-person" in tags and "plural" in tags:
                verb["imperative"]["ihr"] = text
            continue

        tense = _tense(tags)
        if tense:
            slot = _slot(tags)
            if slot is not None and not verb["tenses"][tense][slot]:
                verb["tenses"][tense][slot] = text

        if ("past" in tags and "subjunctive" not in tags
                and "participle" not in tags):
            if "third-person" in tags and "singular" in tags:
                past_base = text
            elif not any(t in tags for t in PERSON_INDEX) and not past_base:
                past_base = text

    if past_base:
        for index, form in enumerate(_generate_past(past_base)):
            if not verb["tenses"]["praeteritum"][index]:
                verb["tenses"]["praeteritum"][index] = form

    if not any(verb["tenses"]["konjunktiv1"]):
        stem = _infinitive_stem(infinitive)
        endings = ["e", "est", "e", "en", "et", "en"]
        verb["tenses"]["konjunktiv1"] = [stem + e for e in endings]

    if not any(verb["tenses"]["konjunktiv2"]):
        if past_base and past_base.endswith("te"):
            verb["tenses"]["konjunktiv2"] = list(
                verb["tenses"]["praeteritum"])
        elif infinitive:
            verb["tenses"]["konjunktiv2"] = [
                f"{w} {infinitive}" for w in WUERDE]

    if not verb["imperative"]["du"]:
        present_du = verb["tenses"]["praesens"][1]
        if present_du.endswith("st"):
            verb["imperative"]["du"] = present_du[:-2]
    if not verb["imperative"]["ihr"]:
        verb["imperative"]["ihr"] = verb["tenses"]["praesens"][4]
    if not verb["imperative"]["Sie"]:
        sie_form = (verb["tenses"]["konjunktiv1"][5]
                    or verb["tenses"]["praesens"][5])
        if sie_form:
            verb["imperative"]["Sie"] = f"{sie_form} Sie"

    if not verb["reflexive"]:
        verb["separable"] = any(
            " " in form for form in verb["tenses"]["praesens"] if form)

    if verb["participle"]:
        aux = verb["auxiliary"]
        verb["tenses"]["perfekt"] = [
            f"{a} {verb['participle']}" for a in AUX_PRESENT[aux]]
        verb["tenses"]["plusquamperfekt"] = [
            f"{a} {verb['participle']}" for a in AUX_PAST[aux]]
        verb["tenses"]["futur1"] = [f"{w} {infinitive}" for w in WERDEN]
        verb["tenses"]["futur2"] = [
            f"{w} {verb['participle']} {aux}" for w in WERDEN]

    return verb


def _pick_entry(entries: List[dict]) -> Optional[dict]:
    if not entries:
        return None

    def score(entry: dict) -> tuple:
        senses = entry.get("senses", [])
        quality = [sense for sense in senses if _is_quality_sense(sense)]
        first = quality[0].get("glosses", [""])[0] if quality else ""
        return (bool(quality), len(quality), len(entry.get("forms", [])),
                len(senses), -len(first))

    return max(entries, key=score)


def load_curated(path: Path) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    words = data.get("words", []) if isinstance(data, dict) else data
    required = ("lemma", "pos", "level", "english", "explanation")
    for index, word in enumerate(words, 1):
        missing = [key for key in required if not word.get(key)]
        if missing:
            raise ValueError(
                f"curated word #{index} is missing: {', '.join(missing)}")
    return words


def load_tatoeba(path: Path) -> List[dict]:
    sentences = []
    try:
        with open(path, encoding="utf-8") as f:
            for index, line in enumerate(f):
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2:
                    continue
                en, de = _clean(parts[0]), _clean(parts[1])
                if not en or not de:
                    continue
                source = (parts[2].strip() if len(parts) > 2
                          and parts[2].strip() else f"tatoeba:line-{index}")
                sentences.append({"de": de, "en": en, "source": source})
    except FileNotFoundError:
        print(f"Warning: Tatoeba file {path} not found.")
    return sentences


def load_kaikki(path: Path, targets: set) -> Dict[tuple, List[dict]]:
    found: Dict[tuple, List[dict]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            key = (entry.get("word", "").lower(), entry.get("pos", ""))
            if key in targets:
                found.setdefault(key, []).append(entry)
    return found


def _match_forms(entry: dict, lemma: str) -> List[str]:
    forms = {lemma}
    for form in entry.get("forms", []):
        tags = _tags(form)
        if tags & BAD_FORM_TAGS or "infinitive-zu" in tags:
            continue
        text = _clean(form.get("form", ""))
        if text and len(text) <= 40:
            forms.add(text)
    return sorted(forms, key=len, reverse=True)


def _choose_example(sentences: List[dict], forms: List[str], lemma: str,
                    used: set) -> Optional[dict]:
    lemma_re = re.compile(rf"\b{re.escape(lemma)}\b", re.IGNORECASE)
    form_res = [re.compile(rf"\b{re.escape(form)}\b", re.IGNORECASE)
                for form in forms if len(form) > 1]
    best = None
    for sentence in sentences:
        de, en = sentence["de"], sentence["en"]
        if de in used:
            continue
        length = len(de.split())
        if length < 4 or length > 14:
            continue
        exact = bool(lemma_re.search(de))
        if not exact and not any(r.search(de) for r in form_res):
            continue
        rank = (0 if exact else 1, abs(length - 8), length)
        if best is None or rank < best[0]:
            best = (rank, sentence)
    return best[1] if best else None


def _build_word(item: dict, entry: dict, sentences: List[dict],
                used: set) -> dict:
    pos = item["pos"]
    lemma = item["lemma"]
    examples = []
    if item.get("example_de") and item.get("example_en"):
        examples.append({
            "de": item["example_de"],
            "en": item["example_en"],
            "source": item.get("example_source", "curated"),
        })
        used.add(item["example_de"])
    elif sentences:
        sentence = _choose_example(
            sentences, _match_forms(entry, lemma), lemma, used)
        if sentence:
            used.add(sentence["de"])
            examples.append(sentence)

    word = {
        "id": f"{lemma.lower().replace(' ', '-')}-{pos}",
        "lemma": lemma,
        "pos": pos,
        "level": item["level"],
        "english": item["english"],
        "explanation": item["explanation"],
        "examples": examples,
    }
    if pos == "noun":
        word["noun"] = extract_noun(entry, item)
    elif pos == "verb":
        word["verb"] = extract_verb_forms(entry)
    return word


def validate_word(word: dict) -> Tuple[List[str], List[str]]:
    errors, warnings = [], []
    name = word["lemma"]

    if not word.get("examples"):
        warnings.append(f"{name}: no example sentence")
    if not word.get("english"):
        errors.append(f"{name}: missing English translation")

    if word["pos"] == "noun":
        noun = word.get("noun") or {}
        if noun.get("article") not in ARTICLE_BY_GENDER.values():
            errors.append(f"{name}: missing definite article")
        if not noun.get("plural") or noun["plural"] == "-":
            warnings.append(f"{name}: missing plural")
        if not noun.get("genitive") or noun["genitive"] == "-":
            warnings.append(f"{name}: missing genitive")

    if word["pos"] == "verb":
        verb = word.get("verb") or {}
        tenses = verb.get("tenses", {})
        for tense in ("praesens",):
            forms = tenses.get(tense, [])
            if len(forms) != 6 or any(not form for form in forms):
                errors.append(f"{name}: incomplete {tense}")
        if not verb.get("participle"):
            errors.append(f"{name}: missing past participle")
        if verb.get("auxiliary") not in AUX_PRESENT:
            errors.append(f"{name}: invalid auxiliary")
        for tense in ("praeteritum", "konjunktiv1", "konjunktiv2"):
            forms = tenses.get(tense, [])
            if len(forms) != 6 or any(not form for form in forms):
                warnings.append(f"{name}: incomplete {tense}")
        for form in verb.get("imperative", {}).values():
            if not form:
                warnings.append(f"{name}: incomplete imperative")
                break

    return errors, warnings


def build_deck(curated_path: Path, kaikki_path: Path, tatoeba_path: Path
               ) -> Tuple[List[dict], List[str], List[str]]:
    curated = load_curated(curated_path)
    targets = {(word["lemma"].lower(), word["pos"]) for word in curated}
    print(f"Scanning {kaikki_path} for {len(targets)} words...")
    entries = load_kaikki(kaikki_path, targets)

    needs_sentences = any(
        not (word.get("example_de") and word.get("example_en"))
        for word in curated)
    sentences = load_tatoeba(tatoeba_path) if needs_sentences else []
    used_examples = set()

    words, errors, warnings = [], [], []
    seen_ids = set()
    for item in curated:
        key = (item["lemma"].lower(), item["pos"])
        entry = _pick_entry(entries.get(key, []))
        if entry is None:
            errors.append(f"{item['lemma']}: not found in Kaikki")
            continue
        word = _build_word(item, entry, sentences, used_examples)
        if word["id"] in seen_ids:
            errors.append(f"{item['lemma']}: duplicate id {word['id']}")
        seen_ids.add(word["id"])
        word_errors, word_warnings = validate_word(word)
        errors.extend(word_errors)
        warnings.extend(word_warnings)
        words.append(word)

    return words, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curated", type=Path, default=DEFAULT_CURATED)
    parser.add_argument("--kaikki", type=Path, default=DEFAULT_KAIKKI)
    parser.add_argument("--tatoeba", type=Path, default=DEFAULT_TATOEBA)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.kaikki.exists():
        print(f"Missing {args.kaikki}. Run tools/download_data.py first.")
        return 1

    words, errors, warnings = build_deck(
        args.curated, args.kaikki, args.tatoeba)
    for warning in warnings:
        print(f"warning: {warning}")
    if errors:
        for error in errors:
            print(f"error: {error}")
        print("vocab.json was not written.")
        return 1

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"schema": 2, "words": words}, f, indent=2,
                  ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(words)} words to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
