from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from telecom_agent.evaluation import evaluate_bm25
from telecom_agent.retrieval import BM25Index

from test_bm25 import chunk


class RetrievalEvaluationTests(unittest.TestCase):
    def test_computes_recall_and_mrr(self) -> None:
        index = BM25Index(
            [
                chunk("a", "4.4.3.2", "Replay protection", "NAS replay protection"),
                chunk("b", "5.5.1", "Registration", "UE registration procedure"),
            ]
        )
        questions = [
            {
                "id": "q1",
                "question": "NAS replay protection",
                "required_sections": ["4.4.3.2"],
            },
            {
                "id": "q2",
                "question": "unknown subject",
                "required_sections": ["9"],
            },
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "questions.json"
            path.write_text(json.dumps(questions), encoding="utf-8")
            result = evaluate_bm25(index, path, top_k=1)
        self.assertEqual(result.recall_at_k, 0.5)
        self.assertEqual(result.mean_reciprocal_rank, 0.5)


if __name__ == "__main__":
    unittest.main()
