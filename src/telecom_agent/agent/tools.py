"""Bounded local tools exposed to the runtime model."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

from telecom_agent.graph import GraphRepository
from telecom_agent.models import SpecChunk
from telecom_agent.retrieval import BM25Index


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
        "strict": True,
    }


TOOL_SCHEMAS = [
    _schema(
        "resolve_entities",
        "Resolve a user term to ranked TS 24.501 knowledge-graph entities. Use before graph tools when the exact node is unknown.",
        {
            "query": {"type": "string", "description": "Entity name or telecom term"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10},
        },
        ["query", "limit"],
    ),
    _schema(
        "search_spec",
        "Search the reconstructed TS 24.501 v19.2.0 text corpus and return citation metadata and excerpts.",
        {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
            "section_prefix": {"type": ["string", "null"]},
        },
        ["query", "top_k", "section_prefix"],
    ),
    _schema(
        "inspect_entity",
        "Inspect one resolved graph entity, its graph degree, provenance, and high-confidence aligned specification evidence.",
        {"node_id": {"type": "string"}},
        ["node_id"],
    ),
    _schema(
        "expand_graph",
        "Return a bounded graph neighborhood. Edge source metadata must be checked before treating a relation as TS 24.501 evidence.",
        {
            "node_id": {"type": "string"},
            "direction": {"type": "string", "enum": ["in", "out", "both"]},
            "relation": {"type": ["string", "null"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 30},
        },
        ["node_id", "direction", "relation", "limit"],
    ),
    _schema(
        "find_paths",
        "Find bounded graph paths between two exact node IDs. Paths are structural hints and require text evidence.",
        {
            "source_node_id": {"type": "string"},
            "target_node_id": {"type": "string"},
            "max_hops": {"type": "integer", "minimum": 1, "maximum": 3},
            "limit": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        ["source_node_id", "target_node_id", "max_hops", "limit"],
    ),
]


class AgentTools:
    def __init__(
        self,
        repository: GraphRepository,
        chunks: list[SpecChunk],
        *,
        alignments_path: str | Path | None = None,
        max_excerpt_chars: int = 1600,
    ) -> None:
        self.repository = repository
        self.chunks = chunks
        self.index = BM25Index(chunks)
        self.chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        self.max_excerpt_chars = max_excerpt_chars
        self.alignments: dict[str, list[dict[str, Any]]] = defaultdict(list)
        if alignments_path and Path(alignments_path).is_file():
            with Path(alignments_path).open("r", encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    if row.get("confidence_label") in {"verified", "high"}:
                        self.alignments[row["graph_item_id"]].append(row)

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return TOOL_SCHEMAS

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handlers: dict[str, Callable[..., dict[str, Any]]] = {
            "resolve_entities": self.resolve_entities,
            "search_spec": self.search_spec,
            "inspect_entity": self.inspect_entity,
            "expand_graph": self.expand_graph,
            "find_paths": self.find_paths,
        }
        if name not in handlers:
            return {"ok": False, "error": f"Unknown tool: {name}"}
        try:
            return {"ok": True, "result": handlers[name](**arguments)}
        except (KeyError, ValueError) as error:
            return {"ok": False, "error": str(error)}

    def resolve_entities(self, query: str, limit: int) -> dict[str, Any]:
        return {
            "query": query,
            "matches": [
                {
                    "node_id": match.node.node_id,
                    "label": match.node.label,
                    "entity_type": match.node.attributes.get("entity_type", "UNKNOWN"),
                    "score": round(match.score, 4),
                    "method": match.method,
                }
                for match in self.repository.resolve_entities(query, limit=min(limit, 10))
            ],
        }

    def search_spec(
        self, query: str, top_k: int, section_prefix: str | None
    ) -> dict[str, Any]:
        hits = self.index.search(
            query, top_k=min(top_k, 10), section_prefix=section_prefix or None
        )
        return {
            "query": query,
            "specification": "3GPP TS 24.501",
            "version": "19.2.0",
            "hits": [self._evidence(hit.chunk, score=hit.score) for hit in hits],
        }

    def inspect_entity(self, node_id: str) -> dict[str, Any]:
        view = self.repository.node_view(node_id)
        evidence = []
        for alignment in sorted(
            self.alignments.get(node_id, []), key=lambda row: -row["confidence"]
        )[:5]:
            chunk = self.chunk_by_id.get(alignment["chunk_id"])
            if chunk:
                value = self._evidence(chunk)
                value["alignment_confidence"] = alignment["confidence"]
                value["alignment_label"] = alignment["confidence_label"]
                evidence.append(value)
        return {"entity": view, "aligned_evidence": evidence}

    def expand_graph(
        self, node_id: str, direction: str, relation: str | None, limit: int
    ) -> dict[str, Any]:
        edges = self.repository.neighbors(
            node_id,
            direction=direction,
            relation=relation or None,
            limit=min(limit, 30),
        )
        return {
            "node_id": node_id,
            "edges": [self._edge(edge) for edge in edges],
            "warning": "Graph relations are structural hints; verify claims with search_spec evidence.",
        }

    def find_paths(
        self, source_node_id: str, target_node_id: str, max_hops: int, limit: int
    ) -> dict[str, Any]:
        paths = self.repository.find_paths(
            source_node_id,
            target_node_id,
            max_hops=min(max_hops, 3),
            limit=min(limit, 5),
        )
        return {
            "source_node_id": source_node_id,
            "target_node_id": target_node_id,
            "paths": [[self._edge(edge) for edge in path] for path in paths],
            "warning": "A graph path is not a citation. Retrieve the supporting specification text.",
        }

    def _evidence(self, chunk: SpecChunk, *, score: float | None = None) -> dict[str, Any]:
        value: dict[str, Any] = {
            "chunk_id": chunk.chunk_id,
            "specification": chunk.spec_id,
            "version": chunk.version,
            "section": chunk.section,
            "section_title": chunk.section_title,
            "page_start": chunk.page_start,
            "content_type": chunk.content_type,
            "source_file": chunk.source_file,
            "excerpt": chunk.text[: self.max_excerpt_chars],
        }
        if score is not None:
            value["retrieval_score"] = round(score, 6)
        return value

    def _edge(self, edge: Any) -> dict[str, Any]:
        return {
            "source_node_id": edge.source,
            "source_label": self.repository.nodes[edge.source].label,
            "target_node_id": edge.target,
            "target_label": self.repository.nodes[edge.target].label,
            "relations": list(edge.relations),
            "description": edge.attributes.get("description", ""),
            "file_path": edge.attributes.get("file_path", ""),
            "source_file": edge.attributes.get("source_file", ""),
            "is_ts24501_provenance": "24501-j20" in edge.attributes.get("file_path", ""),
        }

