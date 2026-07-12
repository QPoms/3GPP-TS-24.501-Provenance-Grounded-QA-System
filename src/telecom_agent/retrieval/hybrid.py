"""Reciprocal-rank fusion for lexical and semantic retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from telecom_agent.models import SpecChunk
from telecom_agent.retrieval.bm25 import SearchHit
from telecom_agent.retrieval.vector import VectorHit


@dataclass(frozen=True)
class HybridHit:
    chunk: SpecChunk
    score: float
    lexical_rank: int | None
    vector_rank: int | None


def reciprocal_rank_fusion(
    lexical: Sequence[SearchHit],
    vector: Sequence[VectorHit],
    *,
    top_k: int = 10,
    rank_constant: int = 60,
) -> list[HybridHit]:
    scores: dict[str, float] = {}
    chunks: dict[str, SpecChunk] = {}
    lexical_ranks: dict[str, int] = {}
    vector_ranks: dict[str, int] = {}
    for rank, hit in enumerate(lexical, start=1):
        chunk_id = hit.chunk.chunk_id
        chunks[chunk_id] = hit.chunk
        lexical_ranks[chunk_id] = rank
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (rank_constant + rank)
    for rank, hit in enumerate(vector, start=1):
        chunk_id = hit.chunk.chunk_id
        chunks[chunk_id] = hit.chunk
        vector_ranks[chunk_id] = rank
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (rank_constant + rank)
    ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))[:top_k]
    return [
        HybridHit(
            chunk=chunks[chunk_id],
            score=scores[chunk_id],
            lexical_rank=lexical_ranks.get(chunk_id),
            vector_rank=vector_ranks.get(chunk_id),
        )
        for chunk_id in ordered
    ]

