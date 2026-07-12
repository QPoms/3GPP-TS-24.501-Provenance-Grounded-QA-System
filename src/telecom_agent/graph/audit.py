"""Streaming GraphML audit utilities.

The audit intentionally uses the standard library so data quality can be inspected before
the optional project dependencies are installed.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


GRAPHML_NAMESPACE = "http://graphml.graphdrawing.org/xmlns"
GRAPHML = f"{{{GRAPHML_NAMESPACE}}}"


@dataclass(frozen=True)
class GraphAudit:
    path: str
    file_size_bytes: int
    directed: bool
    nodes: int
    edges: int
    self_loops: int
    node_attribute_coverage: dict[str, int]
    edge_attribute_coverage: dict[str, int]
    entity_types: dict[str, int]
    relation_keywords: dict[str, int]
    matching_spec_nodes: int
    matching_spec_edges: int
    matching_spec_sections: tuple[str, ...]
    matching_spec_source_tokens: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["matching_spec_sections"] = list(self.matching_spec_sections)
        value["matching_spec_source_tokens"] = list(self.matching_spec_source_tokens)
        return value


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _element_data(element: ElementTree.Element, keys: dict[str, str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for child in element:
        if _local_name(child.tag) != "data":
            continue
        key = keys.get(child.attrib.get("key", ""), child.attrib.get("key", ""))
        values[key] = (child.text or "").strip()
    return values


def _contains_spec(values: dict[str, str], spec_token: str) -> bool:
    token = spec_token.casefold().replace(".", "")
    for key in ("source_file", "file_path", "description", "source_id"):
        normalized = values.get(key, "").casefold().replace(".", "")
        if token in normalized:
            return True
    return False


def _sections(values: dict[str, str], source_token: str) -> set[str]:
    sections: set[str] = set()
    marker = f"{source_token}.md"
    for raw in values.get("file_path", "").split("<SEP>"):
        if marker in raw:
            section = raw.split(marker, 1)[1].strip()
            if section:
                sections.add(section)
    return sections


def audit_graphml(
    path: str | Path,
    *,
    spec_token: str = "24501",
    source_token: str = "24501-j20",
) -> GraphAudit:
    """Audit a GraphML file without loading the full graph into memory."""

    graph_path = Path(path)
    if not graph_path.is_file():
        raise FileNotFoundError(f"GraphML file not found: {graph_path}")

    keys: dict[str, str] = {}
    node_coverage: Counter[str] = Counter()
    edge_coverage: Counter[str] = Counter()
    entity_types: Counter[str] = Counter()
    relation_keywords: Counter[str] = Counter()
    source_tokens: set[str] = set()
    sections: set[str] = set()
    node_count = edge_count = self_loops = 0
    matching_nodes = matching_edges = 0
    directed = True

    for event, element in ElementTree.iterparse(graph_path, events=("start", "end")):
        name = _local_name(element.tag)
        if event == "start":
            if name == "key":
                keys[element.attrib.get("id", "")] = element.attrib.get(
                    "attr.name", element.attrib.get("id", "")
                )
            elif name == "graph":
                directed = element.attrib.get("edgedefault", "directed") == "directed"
            continue

        if name == "node":
            node_count += 1
            values = _element_data(element, keys)
            node_coverage.update(key for key, value in values.items() if value)
            entity_types[values.get("entity_type") or "UNKNOWN"] += 1
            if _contains_spec(values, spec_token):
                matching_nodes += 1
                sections.update(_sections(values, source_token))
                if source_token in values.get("source_file", ""):
                    source_tokens.add(source_token)
            element.clear()
        elif name == "edge":
            edge_count += 1
            self_loops += element.attrib.get("source") == element.attrib.get("target")
            values = _element_data(element, keys)
            edge_coverage.update(key for key, value in values.items() if value)
            for keyword in values.get("keywords", "").split("<SEP>"):
                keyword = keyword.strip()
                if keyword:
                    relation_keywords[keyword] += 1
            if _contains_spec(values, spec_token):
                matching_edges += 1
                sections.update(_sections(values, source_token))
                if source_token in values.get("source_file", ""):
                    source_tokens.add(source_token)
            element.clear()

    return GraphAudit(
        path=str(graph_path.resolve()),
        file_size_bytes=graph_path.stat().st_size,
        directed=directed,
        nodes=node_count,
        edges=edge_count,
        self_loops=self_loops,
        node_attribute_coverage=dict(node_coverage.most_common()),
        edge_attribute_coverage=dict(edge_coverage.most_common()),
        entity_types=dict(entity_types.most_common()),
        relation_keywords=dict(relation_keywords.most_common()),
        matching_spec_nodes=matching_nodes,
        matching_spec_edges=matching_edges,
        matching_spec_sections=tuple(sorted(sections, key=_section_sort_key)),
        matching_spec_source_tokens=tuple(sorted(source_tokens)),
    )


def _section_sort_key(section: str) -> tuple[tuple[int, str], ...]:
    result: list[tuple[int, str]] = []
    for part in section.split("."):
        result.append((int(part), "") if part.isdigit() else (10**9, part))
    return tuple(result)

