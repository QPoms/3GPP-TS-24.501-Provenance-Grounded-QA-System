from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from telecom_agent.agent import AgentTools
from telecom_agent.graph import GraphRepository

from test_bm25 import chunk
from test_graph_audit import SAMPLE_GRAPHML


class AgentToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        graph_path = Path(self.temp_dir.name) / "graph.graphml"
        graph_path.write_text(SAMPLE_GRAPHML, encoding="utf-8")
        self.tools = AgentTools(
            GraphRepository.from_graphml(graph_path),
            [chunk("c1", "5.5.1.2", "Registration", "The UE initiates registration.")],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_search_returns_citation_metadata(self) -> None:
        value = self.tools.call(
            "search_spec",
            {"query": "UE registration", "top_k": 3, "section_prefix": None},
        )
        hit = value["result"]["hits"][0]
        self.assertTrue(value["ok"])
        self.assertEqual(hit["section"], "5.5.1.2")
        self.assertEqual(hit["chunk_id"], "c1")

    def test_unknown_tool_is_safe_error(self) -> None:
        value = self.tools.call("shell", {})
        self.assertFalse(value["ok"])


if __name__ == "__main__":
    unittest.main()

