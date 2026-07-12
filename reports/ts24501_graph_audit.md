# TS 24.501 data foundation audit

Audit date: 2026-07-12

## Version identification

The full knowledge graph contains repeated provenance references to:

```text
Rel-19/24_series/24501-j20
```

The matching official 3GPP archive entry is `24501-j20.zip`. The source code `j20`
corresponds to TS 24.501 version 19.2.0. The archive was published on 2025-03-20.

## Full graph

Source: `data/tkg/rel19_3gpp_telecom_kg.graphml`

| Metric | Value |
|---|---:|
| File size | 31,915,826 bytes |
| Nodes | 21,540 |
| Edges | 31,718 |
| Directed | Yes |
| Self-loops | 0 |
| Nodes with descriptions | 14,491 |
| Edges with descriptions | 31,692 |
| Edges with conditions | 8,134 |

## TS 24.501 provenance coverage

The previously supplied lightweight visualization has only 38 nodes and 104 unique edges.
It is therefore unsuitable as the authoritative working subgraph.

Filtering the full graph by explicit `24501` provenance produced:

| Metric | Value |
|---|---:|
| Directly matching nodes | 409 |
| Matching provenance edges | 134 |
| Cross-specification endpoint nodes | 12 |
| Exported working nodes | 421 |
| Contextual edges between retained nodes | 50 |
| Exported working edges | 184 |

The 12 endpoint nodes are retained because a TS 24.501-sourced edge points to them. Edges
between retained nodes are included as contextual structure, but retain their original source
metadata. A contextual edge must not be cited as TS 24.501 evidence unless its own provenance
supports that claim.

The dominant working-subgraph relation labels are:

| Relation | Count |
|---|---:|
| Reference | 58 |
| Definition | 34 |
| Condition | 26 |
| apply | 6 |
| govern | 2 |
| transmit | 2 |
| validate | 2 |
| require | 2 |
| protect | 2 |

## Specification corpus

Official source: `24501-j20.docx` from the 3GPP archive.

| Metric | Value |
|---|---:|
| DOCX SHA-256 | `0f36c754bfdcfee5b000ba8572d9242a20cbd256359e896b4fb77710fd033ceb` |
| Body paragraphs parsed | 15,235 |
| Tables parsed | 550 |
| Heading sections parsed | 1,300 |
| Output chunks | 3,037 |
| Chunks with page metadata | 3,036 |

Chunks are section-aware and retain the specification, release, version, section, heading
path, page, content type, source file, and text. Tables are represented separately from prose.

## Known limitations

- Page numbers are derived from the document's own table of contents. They identify the
  section start page, not the exact rendered page of every paragraph within a long section.
- The upstream Hugging Face chunk metadata contains empty `text` values and is not used as
  the retrieval corpus.
- The working graph is filtered by explicit provenance. Graph items missing or carrying
  incorrect provenance may be excluded.
- Semantic graph-to-text alignment has not yet been performed.

## Generated artifacts

These outputs are reproducible and intentionally ignored by Git:

```text
data/processed/graph/ts24501_working_subgraph.graphml
data/processed/chunks/ts24501_v19_2_0.jsonl
reports/generated/ts24501_graph_audit.json
reports/generated/ts24501_working_subgraph_audit.json
```
