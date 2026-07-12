"""Domain models shared by ingestion, graph, retrieval, and agent layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceArtifact:
    artifact_id: str
    kind: str
    source_url: str
    local_path: str
    sha256: str
    retrieved_at: str
    publisher: str
    license: str
    spec_id: str | None = None
    release: str | None = None
    version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpecChunk:
    chunk_id: str
    spec_id: str
    release: str
    version: str
    section: str
    section_title: str
    heading_path: tuple[str, ...]
    page_start: int | None
    page_end: int | None
    content_type: str
    text: str
    source_file: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["heading_path"] = list(self.heading_path)
        return value


@dataclass(frozen=True)
class Alignment:
    graph_item_id: str
    graph_item_type: str
    chunk_id: str
    confidence: float
    confidence_label: str
    match_methods: tuple[str, ...]
    component_scores: dict[str, float] = field(default_factory=dict)
    review_status: str = "auto"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["match_methods"] = list(self.match_methods)
        return value

