"""Section-level retrieval evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from telecom_agent.retrieval import BM25Index


@dataclass(frozen=True)
class RetrievalEvaluation:
    questions: int
    top_k: int
    recall_at_k: float
    mean_reciprocal_rank: float
    results: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "questions": self.questions,
            "top_k": self.top_k,
            "recall_at_k": round(self.recall_at_k, 6),
            "mean_reciprocal_rank": round(self.mean_reciprocal_rank, 6),
            "results": list(self.results),
        }


def _section_matches(actual: str, expected: str) -> bool:
    return actual == expected or actual.startswith(expected + ".")


def evaluate_bm25(
    index: BM25Index,
    questions_path: str | Path,
    *,
    top_k: int = 5,
) -> RetrievalEvaluation:
    questions = json.loads(Path(questions_path).read_text("utf-8"))
    if not isinstance(questions, list) or not questions:
        raise ValueError("Evaluation file must contain a non-empty JSON list")
    results: list[dict[str, Any]] = []
    reciprocal_ranks: list[float] = []
    recalled = 0

    for item in questions:
        expected = item["required_sections"]
        hits = index.search(item["question"], top_k=top_k)
        first_rank: int | None = None
        for rank, hit in enumerate(hits, start=1):
            if any(_section_matches(hit.chunk.section, section) for section in expected):
                first_rank = rank
                break
        recalled += first_rank is not None
        reciprocal_ranks.append(1 / first_rank if first_rank else 0.0)
        results.append(
            {
                "id": item["id"],
                "question": item["question"],
                "required_sections": expected,
                "retrieved_sections": [hit.chunk.section for hit in hits],
                "first_relevant_rank": first_rank,
                "passed": first_rank is not None,
            }
        )

    return RetrievalEvaluation(
        questions=len(questions),
        top_k=top_k,
        recall_at_k=recalled / len(questions),
        mean_reciprocal_rank=sum(reciprocal_ranks) / len(reciprocal_ranks),
        results=tuple(results),
    )

