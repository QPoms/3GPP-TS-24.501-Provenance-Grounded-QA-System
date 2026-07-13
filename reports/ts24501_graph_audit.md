# TS 24.501 data foundation audit

Audit date: 2026-07-13

## Version identification

The project targets:

```text
3GPP TS 24.501 v19.2.0
Rel-19/24_series/24501-j20
```

The matching official 3GPP archive entry is `24501-j20.zip`. The source archive and
extracted DOCX are recorded in `data/manifest.json` with SHA-256 checksums.

## Document-built working graph

Source: `data/processed/graph/ts24501_working_subgraph.graphml`

This graph is built from the reconstructed TS 24.501 document chunks. It is the current
working graph used by the provenance-grounded QA path and is intentionally included in the
repository as an inspectable artifact.

| Metric | Value |
|---|---:|
| File size | 1,990,678 bytes |
| Nodes | 2,056 |
| Edges | 2,891 |
| Directed | Yes |
| Self-loops | 0 |
| Relation labels | `DEFINED_IN`, `SUBCLAUSE_OF`, `REFERENCES` |
| Provenance-carrying edges | 2,891 |
| Source token | `24501-j20` |

Node attribute coverage:

| Attribute | Nodes |
|---|---:|
| `entity_id` | 2,056 |
| `node_type` | 2,056 |
| `section` | 2,056 |
| `chunk_id` | 2,056 |
| `char_start` | 2,056 |
| `char_end` | 2,056 |
| `confidence_label` | 2,056 |
| `section_title` | 1,881 |

Edge attribute coverage:

| Attribute | Edges |
|---|---:|
| `keywords` | 2,891 |
| `chunk_id` | 2,891 |
| `section` | 2,891 |
| `char_start` | 2,891 |
| `char_end` | 2,891 |
| `confidence_label` | 2,891 |
| `extraction_method` | 2,891 |
| `source_file` | 2,891 |

Relation distribution:

| Relation | Count |
|---|---:|
| `DEFINED_IN` | 1,080 |
| `SUBCLAUSE_OF` | 1,076 |
| `REFERENCES` | 735 |

During deterministic graph construction, 828 illegal candidate triples were blocked by the
schema whitelist.

## Specification corpus

Official source: `24501-j20.docx` from the 3GPP archive.

| Metric | Value |
|---|---:|
| DOCX SHA-256 | `0f36c754bfdcfee5b000ba8572d9242a20cbd256359e896b4fb77710fd033ceb` |
| Structure-aware chunks | 3,037 |
| Chunks with section-start page metadata | 3,036 |

Chunks are section-aware and retain the specification, release, version, section, heading
path, page, content type, source file, and text. The full parsed chunk file is not committed
because it contains reconstructed specification text.

## Published data artifacts

These lightweight artifacts are included in Git:

```text
data/processed/graph/ts24501_working_subgraph.graphml
data/processed/alignments/ts24501_lexical.jsonl
data/tkg/rel19_24501_subgraph_gephi_lite.graphml
```

The source archive, extracted DOCX, full-text chunks, full upstream graph, Hugging Face
cache, generated indexes, and generated benchmark reports remain local-only by default.

## Known limitations

- Page numbers are derived from the document's own table of contents. They identify the
  section start page, not the exact rendered page of every paragraph within a long section.
- The uploaded graph is a deterministic structural graph. Richer behavioral relations still
  require a later schema-constrained extraction pass.
- The lexical alignment file contains candidate matches for review and expansion. Candidate
  rows should not be treated as authoritative citations without supporting text evidence.
- Text evidence remains mandatory for final QA answers.
