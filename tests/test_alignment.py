from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from telecom_agent.alignment import align_graph_to_chunks
from telecom_agent.graph import GraphRepository
from telecom_agent.models import SpecChunk

from test_graph_audit import SAMPLE_GRAPHML


class AlignmentTests(unittest.TestCase):
    def test_aligns_entity_using_section_and_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = Path(temp_dir) / "sample.graphml"
            output = Path(temp_dir) / "alignments.jsonl"
            graph_path.write_text(SAMPLE_GRAPHML, encoding="utf-8")
            chunk = SpecChunk(
                chunk_id="c1",
                spec_id="3GPP TS 24.501",
                release="Rel-19",
                version="19.2.0",
                section="5.5.1.2",
                section_title="Registration",
                heading_path=("5", "5.5", "5.5.1", "5.5.1.2"),
                page_start=100,
                page_end=100,
                content_type="paragraph",
                text="The UE sends a message to the AMF.",
                source_file="24501-j20.docx",
            )
            result = align_graph_to_chunks(
                GraphRepository.from_graphml(graph_path), [chunk], output
            )
            rows = [json.loads(line) for line in output.read_text("utf-8").splitlines()]

        self.assertGreaterEqual(result.aligned_edges, 1)
        self.assertTrue(any(row["chunk_id"] == "c1" for row in rows))
        self.assertTrue(any("provenance_section" in row["match_methods"] for row in rows))


if __name__ == "__main__":
    unittest.main()
