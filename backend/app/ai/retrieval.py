"""Book passages for citations: the interface the books phase fills in.

The AI texts may cite a passage from the person's books (book, chapter, page and a short quote). Until the books are
indexed, `NoRetriever` finds nothing, so no text cites anything. The books phase adds a retriever (e.g. an index of
books/ built locally, never committed) with the same `search()`.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Passage:
    book: str
    chapter: str | None
    page: str
    text: str  # 1–2 sentences


class Retriever(Protocol):
    def search(self, query: str, k: int = 3) -> list[Passage]: ...


class NoRetriever:
    """The books aren't indexed yet: nothing to cite."""

    def search(self, query: str, k: int = 3) -> list[Passage]:
        return []
