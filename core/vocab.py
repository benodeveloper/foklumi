import json
import random
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "vocab.json"


@dataclass(frozen=True)
class Word:
    german: str
    english: str
    explanation: str
    example_de: str
    example_en: str


class VocabDeck:
    def __init__(self, path: Path = DEFAULT_PATH, rng=None):
        with open(path, encoding="utf-8") as f:
            self._words = [Word(**entry) for entry in json.load(f)]
        if not self._words:
            raise ValueError("Vocabulary file is empty")
        self._rng = rng or random.Random()
        self._queue: list[Word] = []

    def next_word(self) -> Word:
        if not self._queue:
            self._queue = self._words[:]
            self._rng.shuffle(self._queue)
        return self._queue.pop()

    def next_batch(self, n: int) -> list[Word]:
        return [self.next_word() for _ in range(n)]
