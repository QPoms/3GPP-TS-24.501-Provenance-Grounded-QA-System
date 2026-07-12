from __future__ import annotations

import unittest

from telecom_agent.models import SpecChunk
from telecom_agent.retrieval import BM25Index, tokenize


def chunk(chunk_id: str, section: str, title: str, text: str) -> SpecChunk:
    return SpecChunk(
        chunk_id=chunk_id,
        spec_id="3GPP TS 24.501",
        release="Rel-19",
        version="19.2.0",
        section=section,
        section_title=title,
        heading_path=(section,),
        page_start=1,
        page_end=1,
        content_type="paragraph",
        text=text,
        source_file="24501-j20.docx",
    )


class BM25Tests(unittest.TestCase):
    def test_preserves_telecom_tokens(self) -> None:
        self.assertEqual(tokenize("5G-GUTI in 5.5.1.2"), ["5g-guti", "in", "5.5.1.2"])

    def test_ranks_matching_procedure(self) -> None:
        index = BM25Index(
            [
                chunk("a", "5.5.1", "Registration procedure", "The UE initiates registration."),
                chunk("b", "6.1", "Service request", "The UE sends a service request."),
            ]
        )
        hits = index.search("UE registration", top_k=2)
        self.assertEqual(hits[0].chunk.chunk_id, "a")
        self.assertIn("registration", hits[0].matched_terms)

    def test_section_filter(self) -> None:
        index = BM25Index(
            [
                chunk("a", "5.5.1", "Registration", "registration UE"),
                chunk("b", "6.1", "Registration", "registration UE"),
            ]
        )
        hits = index.search("registration", section_prefix="5")
        self.assertEqual([hit.chunk.chunk_id for hit in hits], ["a"])


if __name__ == "__main__":
    unittest.main()
