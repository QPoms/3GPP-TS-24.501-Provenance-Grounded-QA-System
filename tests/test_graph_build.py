from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from telecom_agent.graph import build_spec_graph
from telecom_agent.graph.repository import GraphRepository

from test_bm25 import chunk


class GraphBuildTests(unittest.TestCase):
    def test_builds_document_first_graph_with_chunk_provenance(self) -> None:
        chunks = [
            chunk(
                "c-security",
                "4.4.3.2",
                "Replay protection",
                (
                    "Replay protection shall be supported for received NAS messages. "
                    "For a given 5G NAS security context, a given NAS COUNT value "
                    "shall be accepted at most one time."
                ),
            ),
            chunk(
                "c-message",
                "8.2.28.1",
                "Security protected 5GS NAS message",
                (
                    "The SECURITY PROTECTED 5GS NAS MESSAGE contains a message "
                    "authentication code and a sequence number."
                ),
            ),
            chunk(
                "c-ref",
                "4.4.4.1",
                "Integrity protection and verification",
                "Integrity protection of NAS signalling is specified in 3GPP TS 33.501.",
            ),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "ts24501.graphml"
            result = build_spec_graph(chunks, output)
            self.assertTrue(output.exists())
            repository = GraphRepository.from_graphml(output)

        self.assertGreaterEqual(result.nodes, 6)
        self.assertGreaterEqual(result.edges, 4)
        self.assertGreater(result.provenance_edges, 0)

        replay = repository.resolve_entities("Replay protection")[0]
        self.assertEqual(replay.node.attributes["node_type"], "SecurityConcept")
        self.assertEqual(replay.node.attributes["chunk_id"], "c-security")
        self.assertTrue(replay.node.attributes["char_start"].isdigit())
        self.assertTrue(replay.node.attributes["char_end"].isdigit())

        edges = repository.neighbors(replay.node.node_id, direction="out", relation="DEFINED_IN")
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].attributes["chunk_id"], "c-security")
        self.assertTrue(edges[0].attributes["char_start"].isdigit())
        self.assertTrue(edges[0].attributes["char_end"].isdigit())
        self.assertEqual(edges[0].attributes["confidence_label"], "verified")

        external = repository.resolve_entities("3GPP TS 33.501")[0]
        self.assertEqual(external.node.attributes["node_type"], "ExternalSpec")

    def test_rejects_illegal_triples(self) -> None:
        chunks = [
            chunk("c1", "8.2.1", "Registration request", "Registration request message."),
            chunk("c2", "9.11.3.4", "5GS registration type", "An information element."),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "ts24501.graphml"
            build_spec_graph(chunks, output)
            repository = GraphRepository.from_graphml(output)

        illegal = [
            edge
            for edge in repository.edges
            if edge.source.startswith("ie:") and "CONTAINS_IE" in edge.relations
        ]
        self.assertEqual(illegal, [])


if __name__ == "__main__":
    unittest.main()
