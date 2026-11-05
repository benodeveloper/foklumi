"""Fetch random German word candidates from Wiktionary.

The German Wiktionary API supplies random page titles. Kaikki supplies the
English gloss, part of speech, and grammar, and Tatoeba supplies an example
sentence when one is available. Candidates are written to a review file; this
tool never modifies the bundled vocabulary directly.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_pipeline import (  # noqa: E402
    DEFAULT_CURATED,
    DEFAULT_KAIKKI,
    DEFAULT_TATOEBA,
    _build_word,
    _choose_example,
    _clean,
    _is_form_of_sense,
    _is_quality_sense,
    _match_forms,
    _pick_entry,
    extract_noun,
    load_curated,
    load_tatoeba,
    validate_word,
)

WIKTIONARY_API = "https://de.wiktionary.org/w/api.php"
DEFAULT_OUTPUT = ROOT / "data" / "random_candidates.json"
ALLOWED_POS = ("noun", "verb", "adj", "adv")
USER_AGENT = "Foklumi/0.1 (German vocabulary candidate fetcher)"


def _valid_title(title: str) -> bool:
    """Keep single-word titles made of letters, with optional hyphens."""
    return bool(re.fullmatch(r"[^\W\d_]+(?:-[^\W\d_]+)*", title, re.UNICODE))


def _is_lemma_entry(entry: dict) -> bool:
    """Reject entries that only describe an inflected form of another word."""
    return any(not _is_form_of_sense(sense)
               for sense in entry.get("senses", []))


def _has_quality_sense(entry: dict) -> bool:
    """Reject entries that only have archaic, rare, or dialectal senses."""
    return any(_is_quality_sense(sense) for sense in entry.get("senses", []))


def _entry_matches_pos(entry: dict, pos: str) -> bool:
    if pos == "noun":
        return entry.get("pos") in ("noun", "name")
    return entry.get("pos") == pos


def _english_gloss(entry: dict) -> str:
    senses = sorted(
        entry.get("senses", []),
        key=lambda sense: 0 if _is_quality_sense(sense) else 1)
    for sense in senses:
        if _is_form_of_sense(sense):
            continue
        for gloss in sense.get("glosses", []):
            gloss = _clean(gloss)
            if gloss:
                return gloss
    return ""


def _distribute_counts(total: int, positions: list) -> dict:
    base, remainder = divmod(total, len(positions))
    return {
        pos: base + (1 if index < remainder else 0)
        for index, pos in enumerate(positions)
    }


def _sentence_words(text: str) -> set:
    return set(re.findall(r"[^\W\d_]+", text.lower(), re.UNICODE))


def build_sentence_index(sentences: list) -> dict:
    index = {}
    for position, sentence in enumerate(sentences):
        for word in _sentence_words(sentence["de"]):
            index.setdefault(word, []).append(position)
    return index


def _indexed_candidates(forms: list, index: dict) -> set:
    positions = set()
    for form in forms:
        tokens = _sentence_words(form)
        if not tokens:
            continue
        postings = [index.get(token, []) for token in tokens]
        if any(not posting for posting in postings):
            continue
        postings.sort(key=len)
        matches = set(postings[0])
        for posting in postings[1:]:
            matches.intersection_update(posting)
        positions.update(matches)
    return positions


def _choose_example_fast(sentences: list, index: dict, forms: list,
                         lemma: str, used: set):
    lemma_ci = re.compile(rf"\b{re.escape(lemma)}\b", re.IGNORECASE)
    lemma_cs = re.compile(rf"\b{re.escape(lemma)}\b")
    form_res_ci = [re.compile(rf"\b{re.escape(form)}\b", re.IGNORECASE)
                   for form in forms if len(form) > 1]
    form_res_cs = [re.compile(rf"\b{re.escape(form)}\b")
                   for form in forms if len(form) > 1]
    best = None
    for position in _indexed_candidates(forms, index):
        sentence = sentences[position]
        de, en = sentence["de"], sentence["en"]
        if de in used:
            continue
        length = len(de.split())
        if length < 4 or length > 14:
            continue
        exact = bool(lemma_ci.search(de))
        if not exact and not any(r.search(de) for r in form_res_ci):
            continue
        if lemma_cs.search(de):
            case_rank = 0
        elif any(r.search(de) for r in form_res_cs):
            case_rank = 1
        elif exact:
            case_rank = 2
        else:
            case_rank = 3
        rank = (case_rank, abs(length - 8), length)
        if best is None or rank < best[0]:
            best = (rank, sentence)
    return best[1] if best else None


def fetch_random_titles(session: requests.Session, limit: int,
                        timeout: int) -> list:
    params = {
        "action": "query",
        "list": "random",
        "rnnamespace": 0,
        "rnlimit": limit,
        "format": "json",
        "formatversion": 2,
    }
    response = session.get(WIKTIONARY_API, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise ValueError(data["error"].get("info", "unknown API error"))
    return [item["title"] for item in data.get("query", {}).get("random", [])]


def load_kaikki_titles(path: Path, titles: set) -> dict:
    found = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            key = entry.get("word", "").lower()
            if key in titles:
                found.setdefault(key, []).append(entry)
    return found


def build_candidate(title: str, entries: list, pos: str, sentences: list,
                    used_examples: set, existing_keys: set,
                    allow_missing_examples: bool = False,
                    sentence_index: dict = None):
    if (title.lower(), pos) in existing_keys:
        return None

    candidates = [
        entry for entry in entries
        if (_entry_matches_pos(entry, pos) and _is_lemma_entry(entry)
            and _has_quality_sense(entry))
    ]
    if not candidates:
        return None

    entry = _pick_entry(candidates)
    if entry is None:
        return None

    lemma = _clean(entry.get("word", title))
    english = _english_gloss(entry)
    if not english:
        return None

    candidate = {
        "lemma": lemma,
        "pos": pos,
        "level": "?",
        "english": english,
        "explanation": english,
        "source": f"https://de.wiktionary.org/wiki/{quote(title)}",
    }

    if pos == "noun":
        article = extract_noun(entry, {})["article"]
        if not article:
            return None
        candidate["article"] = article

    sentence = None
    if sentences:
        forms = _match_forms(entry, lemma)
        if sentence_index is not None:
            sentence = _choose_example_fast(
                sentences, sentence_index, forms, lemma, used_examples)
        else:
            sentence = _choose_example(
                sentences, forms, lemma, used_examples)
    if sentence:
        candidate["example_de"] = sentence["de"]
        candidate["example_en"] = sentence["en"]
        candidate["example_source"] = sentence["source"]
    elif not allow_missing_examples:
        return None

    # Validate the grammar before offering the word for review.
    word = _build_word(candidate, entry, [], set())
    errors, _ = validate_word(word)
    if errors:
        return None

    if sentence:
        used_examples.add(sentence["de"])
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20,
                        help="number of candidates to collect (default: 20)")
    parser.add_argument("--pos", default="noun,verb,adj",
                        help="comma-separated parts of speech: noun,verb,adj,adv")
    parser.add_argument("--batch-size", type=int, default=500,
                        help="random titles per API request (max: 500)")
    parser.add_argument("--max-batches", type=int, default=10,
                        help="maximum number of API requests (default: 10)")
    parser.add_argument("--sleep", type=float, default=0.5,
                        help="seconds to wait between API requests")
    parser.add_argument("--timeout", type=int, default=30,
                        help="HTTP timeout in seconds")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--kaikki", type=Path, default=DEFAULT_KAIKKI)
    parser.add_argument("--tatoeba", type=Path, default=DEFAULT_TATOEBA)
    parser.add_argument("--curated", type=Path, default=DEFAULT_CURATED)
    parser.add_argument("--allow-missing-examples", action="store_true",
                        help="keep candidates that have no example sentence")
    args = parser.parse_args()

    pos_list = [pos.strip() for pos in args.pos.split(",") if pos.strip()]
    invalid = [pos for pos in pos_list if pos not in ALLOWED_POS]
    if not pos_list or invalid:
        parser.error(
            f"--pos must contain only: {', '.join(ALLOWED_POS)}")
    if args.count < 1:
        parser.error("--count must be at least 1")
    if args.max_batches < 1:
        parser.error("--max-batches must be at least 1")
    if not args.kaikki.exists():
        print(f"Missing {args.kaikki}. Run tools/download_data.py first.")
        return 1

    curated = load_curated(args.curated)
    existing_keys = {
        (word["lemma"].lower(), word["pos"]) for word in curated
    }
    sentences = load_tatoeba(args.tatoeba)
    if not sentences and not args.allow_missing_examples:
        print(f"Missing or empty {args.tatoeba}. Run tools/download_data.py "
              "first, or use --allow-missing-examples.")
        return 1
    sentence_index = build_sentence_index(sentences) if sentences else None

    desired = _distribute_counts(args.count, pos_list)
    buckets = {pos: [] for pos in pos_list}
    seen_titles = set()
    used_examples = set()
    batch_size = min(max(args.batch_size, 1), 500)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for batch in range(1, args.max_batches + 1):
        try:
            titles = fetch_random_titles(session, batch_size, args.timeout)
        except (requests.RequestException, ValueError, KeyError) as exc:
            print(f"Wiktionary API error: {exc}")
            break

        new_titles = []
        for title in titles:
            key = title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            if _valid_title(title):
                new_titles.append(title)

        if new_titles:
            entries_by_title = load_kaikki_titles(
                args.kaikki, {title.lower() for title in new_titles})
            for title in new_titles:
                entries = entries_by_title.get(title.lower(), [])
                if not entries:
                    continue
                for pos in pos_list:
                    if len(buckets[pos]) >= desired[pos]:
                        continue
                    candidate = build_candidate(
                        title, entries, pos, sentences, used_examples,
                        existing_keys, args.allow_missing_examples,
                        sentence_index=sentence_index)
                    if candidate:
                        buckets[pos].append(candidate)

        progress = ", ".join(
            f"{pos}: {len(buckets[pos])}/{desired[pos]}" for pos in pos_list)
        print(f"Batch {batch}: {len(new_titles)} new titles ({progress})")

        if all(len(buckets[pos]) >= desired[pos] for pos in pos_list):
            break
        if batch < args.max_batches:
            time.sleep(max(args.sleep, 0))

    candidates = [candidate for pos in pos_list for candidate in buckets[pos]]
    output = {
        "schema": 1,
        "source": "https://de.wiktionary.org/",
        "words": candidates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(candidates)} candidates to {args.output}")
    if len(candidates) < args.count:
        print(f"Warning: only found {len(candidates)} of {args.count} "
              "requested candidates.")
    print("Review the candidates, move good entries into "
          "data/curated_words.json, then run tools/build_pipeline.py.")
    return 0 if candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
