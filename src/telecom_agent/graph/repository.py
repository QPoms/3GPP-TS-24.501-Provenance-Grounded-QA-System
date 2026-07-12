"""In-memory bounded query interface for a TS 24.501 GraphML subgraph."""

from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


GRAPHML_NAMESPACE = "http://graphml.graphdrawing.org/xmlns"
GRAPHML = f"{{{GRAPHML_NAMESPACE}}}"
NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")


def normalize_entity(value: str) -> str:
    return NORMALIZE_PATTERN.sub(" ", value.casefold()).strip()


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    attributes: dict[str, str]

    @property
    def label(self) -> str:
        return self.attributes.get("entity_id") or self.node_id

    def to_dict(self) -> dict[str, object]:
        return {"node_id": self.node_id, "label": self.label, "attributes": self.attributes}


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    source: str
    target: str
    attributes: dict[str, str]

    @property
    def relations(self) -> tuple[str, ...]:
        raw = self.attributes.get("keywords", "")
        return tuple(item.strip() for item in raw.split("<SEP>") if item.strip())

    def to_dict(self) -> dict[str, object]:
        return {
            "edge_id": self.edge_id,
            "source": self.source,
            "target": self.target,
            "relations": list(self.relations),
            "attributes": self.attributes,
        }


@dataclass(frozen=True)
class EntityMatch:
    node: GraphNode
    score: float
    method: str

    def to_dict(self) -> dict[str, object]:
        value = self.node.to_dict()
        value.update({"score": round(self.score, 6), "method": self.method})
        return value


class GraphRepository:
    def __init__(self, nodes: dict[str, GraphNode], edges: list[GraphEdge]) -> None:
        self.nodes = nodes
        self.edges = edges
        self.outgoing: dict[str, list[GraphEdge]] = defaultdict(list)
        self.incoming: dict[str, list[GraphEdge]] = defaultdict(list)
        self.normalized_labels: dict[str, str] = {
            node_id: normalize_entity(node.label) for node_id, node in nodes.items()
        }
        for edge in edges:
            self.outgoing[edge.source].append(edge)
            self.incoming[edge.target].append(edge)

    @classmethod
    def from_graphml(cls, path: str | Path) -> "GraphRepository":
        graph_path = Path(path)
        if not graph_path.is_file():
            raise FileNotFoundError(f"GraphML file not found: {graph_path}")
        root = ElementTree.parse(graph_path).getroot()
        keys = {
            key.attrib.get("id", ""): key.attrib.get("attr.name", key.attrib.get("id", ""))
            for key in root.findall(f"{GRAPHML}key")
        }
        graph = root.find(f"{GRAPHML}graph")
        if graph is None:
            raise ValueError(f"No graph element found in {graph_path}")

        def attributes(element: ElementTree.Element) -> dict[str, str]:
            return {
                keys.get(data.attrib.get("key", ""), data.attrib.get("key", "")): (
                    data.text or ""
                ).strip()
                for data in element.findall(f"{GRAPHML}data")
            }

        nodes = {
            element.attrib["id"]: GraphNode(element.attrib["id"], attributes(element))
            for element in graph.findall(f"{GRAPHML}node")
        }
        edges = [
            GraphEdge(
                edge_id=element.attrib.get("id", f"edge-{index}"),
                source=element.attrib["source"],
                target=element.attrib["target"],
                attributes=attributes(element),
            )
            for index, element in enumerate(graph.findall(f"{GRAPHML}edge"), start=1)
        ]
        return cls(nodes, edges)

    def resolve_entities(self, query: str, *, limit: int = 10) -> list[EntityMatch]:
        normalized_query = normalize_entity(query)
        if not normalized_query or limit < 1:
            return []
        matches: list[EntityMatch] = []
        for node_id, normalized_label in self.normalized_labels.items():
            if normalized_label == normalized_query:
                score, method = 1.0, "exact"
            elif normalized_query in normalized_label.split():
                score, method = 0.98, "token"
            elif normalized_query in normalized_label or normalized_label in normalized_query:
                coverage = min(len(normalized_query), len(normalized_label)) / max(
                    len(normalized_query), len(normalized_label)
                )
                score, method = 0.85 + 0.14 * coverage, "substring"
            else:
                score = SequenceMatcher(None, normalized_query, normalized_label).ratio()
                method = "fuzzy"
                if score < 0.45:
                    continue
            matches.append(EntityMatch(self.nodes[node_id], score, method))
        matches.sort(
            key=lambda match: (-match.score, len(match.node.label), match.node.label.casefold())
        )
        return matches[:limit]

    def neighbors(
        self,
        node_id: str,
        *,
        direction: str = "both",
        relation: str | None = None,
        limit: int = 50,
    ) -> list[GraphEdge]:
        if node_id not in self.nodes:
            raise KeyError(f"Unknown graph node: {node_id}")
        if direction not in {"in", "out", "both"}:
            raise ValueError("direction must be 'in', 'out', or 'both'")
        candidates: list[GraphEdge] = []
        if direction in {"out", "both"}:
            candidates.extend(self.outgoing[node_id])
        if direction in {"in", "both"}:
            candidates.extend(self.incoming[node_id])
        if relation:
            expected = relation.casefold()
            candidates = [
                edge
                for edge in candidates
                if any(expected == value.casefold() for value in edge.relations)
            ]
        candidates.sort(key=lambda edge: (edge.source.casefold(), edge.target.casefold(), edge.edge_id))
        return candidates[:limit]

    def find_paths(
        self,
        source: str,
        target: str,
        *,
        max_hops: int = 3,
        limit: int = 5,
        directed: bool = False,
    ) -> list[list[GraphEdge]]:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("Both source and target must be known graph nodes")
        if not 1 <= max_hops <= 6:
            raise ValueError("max_hops must be between 1 and 6")
        queue: deque[tuple[str, list[GraphEdge], frozenset[str]]] = deque(
            [(source, [], frozenset({source}))]
        )
        results: list[list[GraphEdge]] = []
        while queue and len(results) < limit:
            current, path, visited = queue.popleft()
            if len(path) >= max_hops:
                continue
            candidates = list(self.outgoing[current])
            if not directed:
                candidates.extend(self.incoming[current])
            for edge in candidates:
                next_node = edge.target if edge.source == current else edge.source
                if next_node in visited:
                    continue
                next_path = [*path, edge]
                if next_node == target:
                    results.append(next_path)
                    if len(results) >= limit:
                        break
                else:
                    queue.append((next_node, next_path, visited | {next_node}))
        return results

    def node_view(self, node_id: str) -> dict[str, Any]:
        node = self.nodes[node_id]
        return {
            **node.to_dict(),
            "incoming_count": len(self.incoming[node_id]),
            "outgoing_count": len(self.outgoing[node_id]),
        }
