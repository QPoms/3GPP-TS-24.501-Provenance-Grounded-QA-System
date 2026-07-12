"""Document-first TS 24.501 knowledge-graph construction."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree

from telecom_agent.models import SpecChunk


GRAPHML_NAMESPACE = "http://graphml.graphdrawing.org/xmlns"
GRAPHML = f"{{{GRAPHML_NAMESPACE}}}"

REFERENCE_PATTERN = re.compile(r"\b3GPP\s+TS\s+\d{2}\.\d{3}\b", flags=re.IGNORECASE)

ALLOWED_TRIPLES = {
    ("SecurityConcept", "DEFINED_IN", "Section"),
    ("NASMessage", "DEFINED_IN", "Section"),
    ("InformationElement", "DEFINED_IN", "Section"),
    ("Procedure", "DEFINED_IN", "Section"),
    ("Term", "DEFINED_IN", "Section"),
    ("Section", "SUBCLAUSE_OF", "Section"),
    ("Section", "REFERENCES", "ExternalSpec"),
    ("SecurityConcept", "REFERENCES", "ExternalSpec"),
    ("NASMessage", "REFERENCES", "ExternalSpec"),
    ("Procedure", "REFERENCES", "ExternalSpec"),
    ("Term", "REFERENCES", "ExternalSpec"),
}


@dataclass(frozen=True)
class BuildGraphResult:
    output_path: str
    chunks: int
    nodes: int
    edges: int
    provenance_edges: int
    skipped_illegal_triples: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _Node:
    node_id: str
    attributes: dict[str, str]


@dataclass(frozen=True)
class _Edge:
    edge_id: str
    source: str
    target: str
    relation: str
    attributes: dict[str, str]


def build_spec_graph(chunks: Iterable[SpecChunk], output_path: str | Path) -> BuildGraphResult:
    """Build a deterministic TS 24.501 graph layer from specification chunks.

    This is the high-precision skeleton graph: sections, section-defined entities, and
    external specification references. Behavioral LLM extraction is intentionally outside
    this deterministic builder.
    """

    chunk_list = list(chunks)
    nodes: dict[str, _Node] = {}
    edges: dict[tuple[str, str, str], _Edge] = {}
    skipped_illegal = 0

    for spec_chunk in chunk_list:
        section_node = _section_node(spec_chunk)
        nodes.setdefault(section_node.node_id, section_node)
        parent = _parent_section_node(spec_chunk)
        if parent:
            nodes.setdefault(parent.node_id, parent)
            edge, legal = _edge(
                section_node,
                "SUBCLAUSE_OF",
                parent,
                spec_chunk,
                0,
                min(len(spec_chunk.text), max(len(spec_chunk.section), 1)),
                "verified",
                "section_hierarchy",
            )
            if legal:
                edges.setdefault((edge.source, edge.relation, edge.target), edge)
            else:
                skipped_illegal += 1

        entity = _entity_node(spec_chunk)
        if entity:
            nodes.setdefault(entity.node_id, entity)
            start, end = _span(spec_chunk.text, _entity_label(spec_chunk))
            edge, legal = _edge(
                entity,
                "DEFINED_IN",
                section_node,
                spec_chunk,
                start,
                end,
                "verified",
                "section_title",
            )
            if legal:
                edges.setdefault((edge.source, edge.relation, edge.target), edge)
            else:
                skipped_illegal += 1

        for match in REFERENCE_PATTERN.finditer(spec_chunk.text):
            spec_label = _normalize_reference_label(match.group(0))
            external = _external_spec_node(spec_label, spec_chunk, match.start(), match.end())
            nodes.setdefault(external.node_id, external)
            source = entity or section_node
            edge, legal = _edge(
                source,
                "REFERENCES",
                external,
                spec_chunk,
                match.start(),
                match.end(),
                "verified",
                "reference_pattern",
            )
            if legal:
                edges.setdefault((edge.source, edge.relation, edge.target), edge)
            else:
                skipped_illegal += 1

    _write_graphml(output_path, nodes.values(), edges.values())
    output = Path(output_path)
    return BuildGraphResult(
        output_path=str(output.resolve()),
        chunks=len(chunk_list),
        nodes=len(nodes),
        edges=len(edges),
        provenance_edges=sum(1 for edge in edges.values() if edge.attributes.get("chunk_id")),
        skipped_illegal_triples=skipped_illegal,
    )


def _section_node(chunk: SpecChunk) -> _Node:
    label = f"{chunk.section} {chunk.section_title}".strip()
    start, end = _span(chunk.text, chunk.section_title)
    return _Node(
        f"section:{chunk.section}",
        {
            "entity_id": label,
            "node_type": "Section",
            "section": chunk.section,
            "section_title": chunk.section_title,
            "chunk_id": chunk.chunk_id,
            "char_start": str(start),
            "char_end": str(end),
            "confidence_label": "verified",
        },
    )


def _parent_section_node(chunk: SpecChunk) -> _Node | None:
    if "." not in chunk.section:
        return None
    parent_section = chunk.section.rsplit(".", 1)[0]
    return _Node(
        f"section:{parent_section}",
        {
            "entity_id": parent_section,
            "node_type": "Section",
            "section": parent_section,
            "section_title": "",
            "chunk_id": chunk.chunk_id,
            "char_start": "0",
            "char_end": str(min(len(chunk.text), len(parent_section))),
            "confidence_label": "candidate",
        },
    )


def _entity_node(chunk: SpecChunk) -> _Node | None:
    label = _entity_label(chunk)
    if not label:
        return None
    node_type = _node_type(chunk.section)
    start, end = _span(chunk.text, label)
    return _Node(
        f"{node_type.lower()}:{_slug(label)}",
        {
            "entity_id": label,
            "node_type": node_type,
            "section": chunk.section,
            "section_title": chunk.section_title,
            "chunk_id": chunk.chunk_id,
            "char_start": str(start),
            "char_end": str(end),
            "confidence_label": "verified",
        },
    )


def _entity_label(chunk: SpecChunk) -> str:
    return chunk.section_title.strip()


def _node_type(section: str) -> str:
    if section.startswith("8."):
        return "NASMessage"
    if section.startswith("9."):
        return "InformationElement"
    if section.startswith("5."):
        return "Procedure"
    if section.startswith("4."):
        return "SecurityConcept"
    return "Term"


def _external_spec_node(label: str, chunk: SpecChunk, start: int, end: int) -> _Node:
    return _Node(
        f"external_spec:{_slug(label)}",
        {
            "entity_id": label,
            "node_type": "ExternalSpec",
            "section": chunk.section,
            "section_title": chunk.section_title,
            "chunk_id": chunk.chunk_id,
            "char_start": str(start),
            "char_end": str(end),
            "confidence_label": "verified",
        },
    )


def _edge(
    source: _Node,
    relation: str,
    target: _Node,
    chunk: SpecChunk,
    start: int,
    end: int,
    confidence: str,
    method: str,
) -> tuple[_Edge, bool]:
    triple = (source.attributes["node_type"], relation, target.attributes["node_type"])
    legal = triple in ALLOWED_TRIPLES
    edge = _Edge(
        f"edge:{_slug(source.node_id)}:{relation.lower()}:{_slug(target.node_id)}",
        source.node_id,
        target.node_id,
        relation,
        {
            "keywords": relation,
            "chunk_id": chunk.chunk_id,
            "section": chunk.section,
            "char_start": str(start),
            "char_end": str(end),
            "confidence_label": confidence,
            "extraction_method": method,
            "source_file": chunk.source_file,
        },
    )
    return edge, legal


def _span(text: str, value: str) -> tuple[int, int]:
    if not text:
        return 0, 0
    if value:
        index = text.casefold().find(value.casefold())
        if index >= 0:
            return index, index + len(value)
    return 0, min(len(text), max(len(value), 1))


def _normalize_reference_label(value: str) -> str:
    return " ".join(value.upper().split())


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "item"


def _write_graphml(path: str | Path, nodes: Iterable[_Node], edges: Iterable[_Edge]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ElementTree.register_namespace("", GRAPHML_NAMESPACE)
    graphml = ElementTree.Element(f"{GRAPHML}graphml")
    attributes = [
        ("entity_id", "node"),
        ("node_type", "node"),
        ("section", "node"),
        ("section_title", "node"),
        ("chunk_id", "node"),
        ("char_start", "node"),
        ("char_end", "node"),
        ("confidence_label", "node"),
        ("keywords", "edge"),
        ("chunk_id", "edge"),
        ("section", "edge"),
        ("char_start", "edge"),
        ("char_end", "edge"),
        ("confidence_label", "edge"),
        ("extraction_method", "edge"),
        ("source_file", "edge"),
    ]
    key_ids: dict[tuple[str, str], str] = {}
    for index, (name, target) in enumerate(attributes):
        key_id = f"d{index}"
        key_ids[(target, name)] = key_id
        ElementTree.SubElement(
            graphml,
            f"{GRAPHML}key",
            id=key_id,
            **{"for": target, "attr.name": name, "attr.type": "string"},
        )
    graph = ElementTree.SubElement(
        graphml, f"{GRAPHML}graph", id="ts-24501-document-built-graph", edgedefault="directed"
    )
    for node in sorted(nodes, key=lambda item: item.node_id):
        element = ElementTree.SubElement(graph, f"{GRAPHML}node", id=node.node_id)
        for name, value in node.attributes.items():
            data = ElementTree.SubElement(element, f"{GRAPHML}data", key=key_ids[("node", name)])
            data.text = str(value)
    for edge in sorted(edges, key=lambda item: item.edge_id):
        element = ElementTree.SubElement(
            graph, f"{GRAPHML}edge", id=edge.edge_id, source=edge.source, target=edge.target
        )
        for name, value in edge.attributes.items():
            data = ElementTree.SubElement(element, f"{GRAPHML}data", key=key_ids[("edge", name)])
            data.text = str(value)
    ElementTree.ElementTree(graphml).write(output, encoding="utf-8", xml_declaration=True)
