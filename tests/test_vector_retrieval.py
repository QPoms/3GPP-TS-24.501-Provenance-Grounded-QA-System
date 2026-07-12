from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from telecom_agent.retrieval import BM25Index, VectorIndex, reciprocal_rank_fusion

from test_bm25 import chunk


class FakeEmbedder:
    def encode(self, texts):
        values = []
        for text in texts:
            lowered = text.casefold()
            values.append(
                [
                    float("registration" in lowered),
                    float("security" in lowered),
                    float("service" in lowered),
                ]
            )
        return np.asarray(values, dtype=np.float32)


class VectorRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunks = [
            chunk("a", "5.5.1", "Registration", "UE registration procedure"),
            chunk("b", "4.4", "Security", "NAS security context"),
        ]

    def test_build_save_load_and_search(self) -> None:
        embedder = FakeEmbedder()
        index = VectorIndex.build(self.chunks, embedder)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "vectors.npy"
            index.save(path)
            loaded = VectorIndex.load(path, self.chunks)
            hits = loaded.search("registration", embedder, top_k=1)
        self.assertEqual(hits[0].chunk.chunk_id, "a")

    def test_rrf_rewards_agreement(self) -> None:
        embedder = FakeEmbedder()
        lexical = BM25Index(self.chunks).search("registration", top_k=2)
        vector = VectorIndex.build(self.chunks, embedder).search(
            "registration", embedder, top_k=2
        )
        fused = reciprocal_rank_fusion(lexical, vector, top_k=2)
        self.assertEqual(fused[0].chunk.chunk_id, "a")
        self.assertEqual(fused[0].lexical_rank, 1)
        self.assertEqual(fused[0].vector_rank, 1)


if __name__ == "__main__":
    unittest.main()
