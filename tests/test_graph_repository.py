from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from telecom_agent.graph.repository import GraphRepository, normalize_entity

from test_graph_audit import SAMPLE_GRAPHML


class GraphRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        path = Path(self.temp_dir.name) / "sample.graphml"
        path.write_text(SAMPLE_GRAPHML, encoding="utf-8")
        self.repository = GraphRepository.from_graphml(path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_normalizes_entity(self) -> None:
        self.assertEqual(normalize_entity("5G-GUTI"), "5g guti")

    def test_resolves_exact_entity(self) -> None:
        match = self.repository.resolve_entities("UE")[0]
        self.assertEqual(match.node.node_id, "UE")
        self.assertEqual(match.method, "exact")

    def test_returns_neighbors(self) -> None:
        edges = self.repository.neighbors("UE", direction="out", relation="Reference")
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].target, "AMF")

    def test_finds_path(self) -> None:
        paths = self.repository.find_paths("UE", "AMF", max_hops=2)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0][0].source, "UE")


if __name__ == "__main__":
    unittest.main()
