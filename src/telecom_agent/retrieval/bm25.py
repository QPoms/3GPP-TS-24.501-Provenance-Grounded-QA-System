"""Small, deterministic BM25 implementation for the TS 24.501 corpus."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

from telecom_agent.models import SpecChunk


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[-./][A-Za-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    """Tokenize telecom text while preserving terms such as 5G-GUTI and 5.5.1.2."""

    return [token.casefold() for token in TOKEN_PATTERN.findall(text)]


@dataclass(frozen=True)
class SearchHit:
    chunk: SpecChunk
    score: float
    matched_terms: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "score": round(self.score, 6),
            "matched_terms": list(self.matched_terms),
            "spec_id": self.chunk.spec_id,
            "version": self.chunk.version,
            "section": self.chunk.section,
            "section_title": self.chunk.section_title,
            "page_start": self.chunk.page_start,
            "content_type": self.chunk.content_type,
            "text": self.chunk.text,
            "source_file": self.chunk.source_file,
        }


class BM25Index:
    def __init__(
        self,
        chunks: Sequence[SpecChunk],
        *,
        k1: float = 1.5,
        b: float = 0.75,
        title_boost: int = 4,
    ) -> None:
        if not chunks:
            raise ValueError("BM25Index requires at least one chunk")
        self.chunks = list(chunks)
        self.k1 = k1
        self.b = b
        self.term_frequencies: list[Counter[str]] = []
        self.document_lengths: list[int] = []
        document_frequencies: Counter[str] = Counter()

        for chunk in self.chunks:
            tokens = tokenize(chunk.text)
            tokens.extend(tokenize(chunk.section_title) * title_boost)
            tokens.append(chunk.section.casefold())
            frequencies = Counter(tokens)
            self.term_frequencies.append(frequencies)
            self.document_lengths.append(sum(frequencies.values()))
            document_frequencies.update(frequencies.keys())

        self.average_length = sum(self.document_lengths) / len(self.document_lengths)
        count = len(self.chunks)
        self.idf = {
            term: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequencies.items()
        }

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        section_prefix: str | None = None,
        content_types: Iterable[str] | None = None,
    ) -> list[SearchHit]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        query_terms = tuple(dict.fromkeys(tokenize(query)))
        if not query_terms:
            return []
        allowed_types = set(content_types or ())
        scored: list[SearchHit] = []

        for index, chunk in enumerate(self.chunks):
            if section_prefix and not (
                chunk.section == section_prefix or chunk.section.startswith(section_prefix + ".")
            ):
                continue
            if allowed_types and chunk.content_type not in allowed_types:
                continue
            frequencies = self.term_frequencies[index]
            length = self.document_lengths[index]
            score = 0.0
            matched: list[str] = []
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                matched.append(term)
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length / self.average_length
                )
                score += self.idf.get(term, 0.0) * frequency * (self.k1 + 1) / denominator
            if score:
                scored.append(SearchHit(chunk, score, tuple(matched)))

        scored.sort(key=lambda hit: (-hit.score, hit.chunk.section, hit.chunk.chunk_id))
        return scored[:top_k]
