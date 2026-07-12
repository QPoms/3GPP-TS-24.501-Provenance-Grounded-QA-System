"""Deterministic first-pass alignment between graph provenance and specification chunks."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from telecom_agent.graph.repository import GraphEdge, GraphNode, GraphRepository, normalize_entity
from telecom_agent.models import Alignment, SpecChunk
from telecom_agent.retrieval import BM25Index, tokenize


SECTION_MARKER = re.compile(r"24501-j20\.md(?P<section>[0-9A-Z.]+)", re.IGNORECASE)


@dataclass(frozen=True)
class AlignmentResult:
    output_path: str
    graph_nodes: int
    graph_edges: int
    alignments: int
    aligned_nodes: int
    aligned_edges: int
    verified: int
    high: int
    candidate: int

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def provenance_sections(attributes: dict[str, str]) -> tuple[str, ...]:
    sections: set[str] = set()
    for match in SECTION_MARKER.finditer(attributes.get("file_path", "")):
        section = match.group("section").strip(".")
        if section:
            sections.add(section)
    return tuple(sorted(sections))


def _token_overlap(left: str, right: str) -> float:
    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _confidence_label(score: float, *, name_match: bool, section_match: bool) -> str:
    if score >= 0.88 and name_match and section_match:
        return "verified"
    if score >= 0.68 and section_match:
        return "high"
    return "candidate"


def _item_alignments(
    *,
    item_id: str,
    item_type: str,
    label: str,
    description: str,
    attributes: dict[str, str],
    by_section: dict[str, list[SpecChunk]],
    index: BM25Index,
    max_per_item: int,
) -> list[Alignment]:
    sections = provenance_sections(attributes)
    candidates: dict[str, SpecChunk] = {}
    for section in sections:
        for chunk in by_section.get(section, []):
            candidates[chunk.chunk_id] = chunk

    if not candidates:
        query = f"{label} {description[:600]}".strip()
        for hit in index.search(query, top_k=max_per_item * 2):
            candidates[hit.chunk.chunk_id] = hit.chunk

    normalized_label = normalize_entity(label)
    scored: list[tuple[float, Alignment]] = []
    for chunk in candidates.values():
        normalized_text = normalize_entity(chunk.text)
        name_match = bool(normalized_label) and normalized_label in normalized_text
        section_match = chunk.section in sections
        overlap = _token_overlap(description or label, chunk.text)
        component_scores = {
            "section": 0.45 if section_match else 0.0,
            "entity_name": 0.4 if name_match else 0.0,
            "description_overlap": round(min(overlap / 0.3, 1.0) * 0.15, 6),
        }
        score = sum(component_scores.values())
        methods = tuple(
            method
            for method, active in (
                ("provenance_section", section_match),
                ("entity_name", name_match),
                ("description_overlap", overlap > 0),
            )
            if active
        )
        alignment = Alignment(
            graph_item_id=item_id,
            graph_item_type=item_type,
            chunk_id=chunk.chunk_id,
            confidence=round(score, 6),
            confidence_label=_confidence_label(
                score, name_match=name_match, section_match=section_match
            ),
            match_methods=methods,
            component_scores=component_scores,
        )
        scored.append((score, alignment))
    scored.sort(key=lambda value: (-value[0], value[1].chunk_id))
    return [alignment for score, alignment in scored[:max_per_item] if score > 0]


def align_graph_to_chunks(
    repository: GraphRepository,
    chunks: Iterable[SpecChunk],
    output_path: str | Path,
    *,
    max_per_item: int = 3,
) -> AlignmentResult:
    corpus = list(chunks)
    index = BM25Index(corpus)
    by_section: dict[str, list[SpecChunk]] = defaultdict(list)
    for chunk in corpus:
        by_section[chunk.section].append(chunk)

    alignments: list[Alignment] = []
    aligned_nodes: set[str] = set()
    aligned_edges: set[str] = set()
    for node in repository.nodes.values():
        values = _item_alignments(
            item_id=node.node_id,
            item_type="node",
            label=node.label,
            description=node.attributes.get("description", ""),
            attributes=node.attributes,
            by_section=by_section,
            index=index,
            max_per_item=max_per_item,
        )
        if values:
            aligned_nodes.add(node.node_id)
            alignments.extend(values)

    for edge_index, edge in enumerate(repository.edges, start=1):
        edge_key = f"{edge.source}->{edge.target}#{edge_index}"
        label = " ".join(edge.relations) or f"{edge.source} {edge.target}"
        values = _item_alignments(
            item_id=edge_key,
            item_type="edge",
            label=label,
            description=edge.attributes.get("description", ""),
            attributes=edge.attributes,
            by_section=by_section,
            index=index,
            max_per_item=max_per_item,
        )
        if values:
            aligned_edges.add(edge_key)
            alignments.extend(values)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for alignment in alignments:
            handle.write(json.dumps(alignment.to_dict(), ensure_ascii=False) + "\n")

    counts: dict[str, int] = defaultdict(int)
    for alignment in alignments:
        counts[alignment.confidence_label] += 1
    return AlignmentResult(
        output_path=str(output.resolve()),
        graph_nodes=len(repository.nodes),
        graph_edges=len(repository.edges),
        alignments=len(alignments),
        aligned_nodes=len(aligned_nodes),
        aligned_edges=len(aligned_edges),
        verified=counts["verified"],
        high=counts["high"],
        candidate=counts["candidate"],
    )

