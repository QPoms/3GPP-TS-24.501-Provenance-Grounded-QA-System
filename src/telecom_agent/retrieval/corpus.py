"""Read and validate processed specification chunks."""

from __future__ import annotations

import json
from pathlib import Path

from telecom_agent.models import SpecChunk


def load_chunks(path: str | Path) -> list[SpecChunk]:
    corpus_path = Path(path)
    if not corpus_path.is_file():
        raise FileNotFoundError(f"Chunk corpus not found: {corpus_path}")

    chunks: list[SpecChunk] = []
    seen: set[str] = set()
    with corpus_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                chunk = SpecChunk(
                    chunk_id=row["chunk_id"],
                    spec_id=row["spec_id"],
                    release=row["release"],
                    version=row["version"],
                    section=row["section"],
                    section_title=row["section_title"],
                    heading_path=tuple(row["heading_path"]),
                    page_start=row.get("page_start"),
                    page_end=row.get("page_end"),
                    content_type=row["content_type"],
                    text=row["text"],
                    source_file=row["source_file"],
                )
            except (KeyError, TypeError, json.JSONDecodeError) as error:
                raise ValueError(f"Invalid chunk at {corpus_path}:{line_number}") from error
            if chunk.chunk_id in seen:
                raise ValueError(f"Duplicate chunk_id at {corpus_path}:{line_number}: {chunk.chunk_id}")
            if not chunk.text.strip():
                continue
            seen.add(chunk.chunk_id)
            chunks.append(chunk)
    return chunks

