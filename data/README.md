# Data directory

This directory separates third-party inputs from project-generated artifacts.

## Existing upstream dataset

The current `tkg/`, `chunks/`, and `mappings/` files originate from the 3GPP Release 19
Telecom Knowledge Graph published by GSMA and developed by KU-DF:

- https://huggingface.co/datasets/GSMA/telecom-kg-rel19

These files are third-party data. Their presence does not mean this project created the
upstream graph. Check the upstream dataset card and license before redistribution.

The published `chunks/rel19_text_chunks.jsonl` contains empty `text` values. It is retained
as upstream metadata, not treated as a usable RAG corpus.

## Target specification

Graph provenance fields identify the target source as:

```text
Rel-19/24_series/24501-j20
```

`24501-j20` corresponds to 3GPP TS 24.501 version 19.2.0. The official archive entry is:

- https://www.3gpp.org/ftp/Specs/archive/24_series/24.501/24501-j20.zip

Specification documents are not committed automatically. The ingestion pipeline must record
their source URL, retrieval date, SHA-256 checksum, version, and local relative path.

## Layout

```text
data/
|-- external/
|   `-- specifications/  # downloaded source documents; ignored by Git
|-- processed/           # parsed chunks and alignments; ignored by Git
|-- indexes/             # BM25/vector indexes; ignored by Git
|-- tkg/                 # upstream graph files; ignored by Git
|-- mappings/            # upstream entity mappings; ignored by Git
`-- chunks/              # upstream chunk metadata with empty text values; ignored by Git
```

Git does not track empty directories, so generated-data folders may not appear on GitHub
until local commands create files inside them. This is intentional: large downloaded
specifications, generated graph artifacts, indexes, and benchmark outputs stay local by
default and should be regenerated from the documented pipeline rather than stored in the
repository.
