import json
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "vocab.json"


@dataclass(frozen=True)
class Example:
    de: str
    en: str
    source: str


@dataclass(frozen=True)
class VerbInfo:
    auxiliary: str
    separable: bool
    reflexive: bool
    participle: str
    pronouns: List[str]
    tenses: Dict[str, List[str]]
    imperative: Dict[str, str]


@dataclass(frozen=True)
class NounInfo:
    article: str
    plural: str
    genitive: str


@dataclass(frozen=True)
class Word:
    id: str
    lemma: str
    pos: str
    level: str
    english: str
    explanation: str
    examples: List[Example]
    verb: Optional[VerbInfo] = None
    noun: Optional[NounInfo] = None

    # V1 UI Compatibility Properties
    @property
    def german(self) -> str:
        return f"{self.noun.article} {self.lemma}" if self.noun else self.lemma

    @property
    def example_de(self) -> str:
        return self.examples[0].de if self.examples else ""

    @property
    def example_en(self) -> str:
        return self.examples[0].en if self.examples else ""


class VocabDeck:
    def __init__(self, path=None, db_path=None):
        self.warning = None
        self._words: Dict[str, Word] = {}
        self._db_path = Path(db_path) if db_path else self._default_db_path()

        target_path = Path(path).expanduser() if path else DEFAULT_PATH
        try:
            with open(target_path, encoding="utf-8") as f:
                data = json.load(f)
                if data.get("schema") != 2:
                    self.warning = f"Expected schema 2, got {data.get('schema')}"
                
                for entry in data.get("words", []):
                    examples = [Example(**ex) for ex in entry.pop("examples", [])]
                    v_data = entry.pop("verb", None)
                    n_data = entry.pop("noun", None)
                    verb = VerbInfo(**v_data) if v_data else None
                    noun = NounInfo(**n_data) if n_data else None
                    word = Word(**entry, examples=examples, verb=verb, noun=noun)
                    self._words[word.id] = word
        except (OSError, ValueError, TypeError) as e:
            self.warning = f"Failed to load vocab ({e})"

        self._init_db()

    def _default_db_path(self) -> Path:
        if sys.platform == "win32":
            base = Path.home() / "AppData" / "Local" / "foklumi"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "foklumi"
        else:
            base = Path.home() / ".local" / "share" / "foklumi"
        return base / "progress.db"

    def _init_db(self):
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS progress (
                    word_id TEXT PRIMARY KEY,
                    seen_count INTEGER DEFAULT 0,
                    last_seen REAL DEFAULT 0.0
                )
            """)

    def next_word(self) -> Word:
        if not self._words:
            raise RuntimeError("No words loaded in deck.")

        with sqlite3.connect(self._db_path) as conn:
            placeholders = ",".join("?" * len(self._words))
            cur = conn.execute(
                f"SELECT word_id, seen_count, last_seen FROM progress WHERE word_id IN ({placeholders})",
                list(self._words.keys())
            )
            progress = {row[0]: {"count": row[1], "last": row[2]} for row in cur}

        # Find words completely unseen
        unseen = [w_id for w_id in self._words if progress.get(w_id, {}).get("count", 0) == 0]

        if unseen:
            import random
            chosen_id = random.choice(unseen)
        else:
            # All words seen. Pick the one we haven't seen in the longest time.
            sorted_seen = sorted(progress.items(), key=lambda x: x[1]["last"])
            chosen_id = sorted_seen[0][0]

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                INSERT INTO progress (word_id, seen_count, last_seen)
                VALUES (?, 1, ?)
                ON CONFLICT(word_id) DO UPDATE SET
                    seen_count = seen_count + 1,
                    last_seen = excluded.last_seen
            """, (chosen_id, time.time()))

        return self._words[chosen_id]
