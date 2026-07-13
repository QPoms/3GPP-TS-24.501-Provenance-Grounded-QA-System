# TS 24.501 retrieval baseline

Evaluation date: 2026-07-12

## Corpus

- Specification: 3GPP TS 24.501 v19.2.0 (`24501-j20`)
- Structure-aware chunks: 3,037
- Document-built working graph: 2,056 nodes and 2,891 edges
- Explicit provenance-carrying graph edges: 2,891
- Schema-blocked illegal candidate triples during graph construction: 828

## BM25 baseline

The baseline uses telecom-aware tokenization that preserves values such as `5G-GUTI` and
`5.5.1.2`. Section titles receive a four-fold token boost. This value was selected by comparing
title boosts 2, 3, 4, 5, 6, and 8 on the same initial evaluation set; boost 4 was the smallest
value that recovered all expected sections in the top five.

| Metric | Result |
|---|---:|
| Questions | 8 |
| Recall@5 | 1.0000 |
| MRR | 0.68125 |

This is an initial engineering test set, not a publication-quality benchmark. It is small and
was created from known specification sections. The result verifies pipeline behavior but must
not be presented as general TS 24.501 question-answering accuracy.

## Initial graph-to-text alignment

| Metric | Result |
|---|---:|
| Graph nodes | 2,056 |
| Graph edges | 2,891 |
| Alignment rows | 1,560 |

The alignment file stores lexical candidates between graph items and TS 24.501 chunks. It is
useful for review and retrieval expansion, but candidate-level rows must not be emitted as
authoritative citations by default.

## Graph limitations observed

The document-built graph currently emphasizes section structure, external specification
references, and section-defined entities. Consequently:

- Graph paths are explanatory hints, not automatically valid evidence chains.
- Every edge must expose its own source metadata.
- Text evidence remains mandatory for the final answer.
- Entity resolution returns ranked candidates rather than silently choosing every ambiguous term.

## Semantic retrieval

The vector index, Sentence Transformers adapter, and reciprocal-rank fusion implementation are
present and unit-tested with a deterministic fake embedder. A real model index has not yet been
built in the current environment because the optional Torch/Sentence Transformers dependencies
are not installed. The project exposes explicit `build-vector` and `search-hybrid` commands;
model files and generated vectors remain outside Git.
