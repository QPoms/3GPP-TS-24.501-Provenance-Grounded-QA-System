from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from telecom_agent.graph.export import GRAPHML, export_spec_subgraph

from test_graph_audit import SAMPLE_GRAPHML


class GraphExportTests(unittest.TestCase):
    def test_exports_matching_edge_and_both_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.graphml"
            output = Path(temp_dir) / "output.graphml"
            source.write_text(SAMPLE_GRAPHML, encoding="utf-8")

            result = export_spec_subgraph(source, output)
            graph = ElementTree.parse(output).getroot().find(f"{GRAPHML}graph")

        assert graph is not None
        self.assertEqual(result.nodes, 2)
        self.assertEqual(result.edges, 1)
        self.assertEqual(result.provenance_edges, 1)
        self.assertEqual(result.contextual_edges, 0)
        self.assertEqual(result.directly_matched_nodes, 1)
        self.assertEqual(result.endpoint_nodes, 1)
        self.assertEqual(len(graph.findall(f"{GRAPHML}node")), 2)
        self.assertEqual(len(graph.findall(f"{GRAPHML}edge")), 1)


if __name__ == "__main__":
    unittest.main()
