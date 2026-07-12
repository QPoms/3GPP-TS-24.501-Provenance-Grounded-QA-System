"""Optional local semantic vector retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np

from telecom_agent.models import SpecChunk


class Embedder(Protocol):
    def encode(self, texts: Sequence[str]) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    """Lazy adapter so core commands do not require the heavy retrieval extras."""

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:  # pragma: no cover - environment-specific
            raise RuntimeError(
                "Semantic retrieval requires the retrieval extra: uv sync --extra retrieval"
            ) from error
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        return np.asarray(
            self.model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False),
            dtype=np.float32,
        )


@dataclass(frozen=True)
class VectorHit:
    chunk: SpecChunk
    score: float


class VectorIndex:
    def __init__(self, chunks: Sequence[SpecChunk], embeddings: np.ndarray) -> None:
        matrix = np.asarray(embeddings, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] != len(chunks):
            raise ValueError("Embedding matrix must have one row per chunk")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        self.embeddings = matrix / np.maximum(norms, 1e-12)
        self.chunks = list(chunks)

    @classmethod
    def build(cls, chunks: Sequence[SpecChunk], embedder: Embedder) -> "VectorIndex":
        texts = [f"{chunk.section_title}\n{chunk.text}" for chunk in chunks]
        return cls(chunks, embedder.encode(texts))

    def save(self, path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        np.save(output, self.embeddings, allow_pickle=False)

    @classmethod
    def load(cls, path: str | Path, chunks: Sequence[SpecChunk]) -> "VectorIndex":
        return cls(chunks, np.load(Path(path), allow_pickle=False))

    def search(self, query: str, embedder: Embedder, *, top_k: int = 10) -> list[VectorHit]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        query_vector = np.asarray(embedder.encode([query]), dtype=np.float32)
        if query_vector.shape != (1, self.embeddings.shape[1]):
            raise ValueError("Query embedding dimension does not match the index")
        query_vector /= max(float(np.linalg.norm(query_vector)), 1e-12)
        scores = self.embeddings @ query_vector[0]
        indices = np.argsort(-scores, kind="stable")[:top_k]
        return [VectorHit(self.chunks[int(index)], float(scores[index])) for index in indices]

