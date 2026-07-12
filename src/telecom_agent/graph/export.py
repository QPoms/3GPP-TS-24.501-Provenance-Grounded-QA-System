"""Provenance-based GraphML subgraph export."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


GRAPHML_NAMESPACE = "http://graphml.graphdrawing.org/xmlns"
GRAPHML = f"{{{GRAPHML_NAMESPACE}}}"


@dataclass(frozen=True)
class ExportResult:
    source_path: str
    output_path: str
    spec_token: str
    nodes: int
    edges: int
    provenance_edges: int
    contextual_edges: int
    directly_matched_nodes: int
    endpoint_nodes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _data_values(element: ElementTree.Element, keys: dict[str, str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for child in element.findall(f"{GRAPHML}data"):
        key = keys.get(child.attrib.get("key", ""), child.attrib.get("key", ""))
        values[key] = (child.text or "").strip()
    return values


def _matches(values: dict[str, str], spec_token: str) -> bool:
    token = spec_token.casefold().replace(".", "")
    return any(
        token in values.get(key, "").casefold().replace(".", "")
        for key in ("source_file", "file_path", "description", "source_id")
    )


def export_spec_subgraph(
    source_path: str | Path,
    output_path: str | Path,
    *,
    spec_token: str = "24501",
    include_contextual_edges: bool = True,
) -> ExportResult:
    """Export graph elements carrying explicit provenance for one specification.

    Edges are retained only when their own metadata matches the specification. Every endpoint
    of a retained edge is included even when the endpoint node was originally extracted from a
    different specification. This preserves cross-specification references without importing
    unrelated edges.
    """

    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(f"GraphML file not found: {source}")

    ElementTree.register_namespace("", GRAPHML_NAMESPACE)
    tree = ElementTree.parse(source)
    root = tree.getroot()
    graph = root.find(f"{GRAPHML}graph")
    if graph is None:
        raise ValueError(f"No graph element found in {source}")

    keys = {
        key.attrib.get("id", ""): key.attrib.get("attr.name", key.attrib.get("id", ""))
        for key in root.findall(f"{GRAPHML}key")
    }
    nodes = list(graph.findall(f"{GRAPHML}node"))
    edges = list(graph.findall(f"{GRAPHML}edge"))

    directly_matched_node_ids = {
        node.attrib["id"]
        for node in nodes
        if _matches(_data_values(node, keys), spec_token)
    }
    matching_edges = [edge for edge in edges if _matches(_data_values(edge, keys), spec_token)]
    endpoint_ids = {
        endpoint
        for edge in matching_edges
        for endpoint in (edge.attrib.get("source", ""), edge.attrib.get("target", ""))
        if endpoint
    }
    retained_node_ids = directly_matched_node_ids | endpoint_ids

    for node in nodes:
        if node.attrib.get("id") not in retained_node_ids:
            graph.remove(node)
    retained_edges = [
        edge
        for edge in edges
        if edge in matching_edges
        or (
            include_contextual_edges
            and edge.attrib.get("source") in retained_node_ids
            and edge.attrib.get("target") in retained_node_ids
        )
    ]
    for edge in edges:
        if edge not in retained_edges:
            graph.remove(edge)

    graph.set("id", f"ts-{spec_token}-provenance-subgraph")
    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding="utf-8", xml_declaration=True)

    return ExportResult(
        source_path=str(source.resolve()),
        output_path=str(output.resolve()),
        spec_token=spec_token,
        nodes=len(retained_node_ids),
        edges=len(retained_edges),
        provenance_edges=len(matching_edges),
        contextual_edges=len(retained_edges) - len(matching_edges),
        directly_matched_nodes=len(directly_matched_node_ids),
        endpoint_nodes=len(endpoint_ids - directly_matched_node_ids),
    )
