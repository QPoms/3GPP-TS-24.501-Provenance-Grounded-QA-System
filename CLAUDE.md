# Repository guidance

## Project scope

This repository implements a provenance-grounded QA system for 3GPP TS 24.501.
Do not expand the implementation to other specifications until the TS 24.501 pipeline is
working and evaluated end to end.

## Runtime boundary

- The application runtime uses the OpenAI API.
- Claude Code may assist development, testing, review, and documentation.
- Do not add an Anthropic runtime dependency unless the project owner explicitly requests it.

## Evidence rules

- Never treat model memory as evidence for a standards claim.
- Citations must be created from retrieved metadata.
- Preserve specification version, section, page, source file, and chunk identifiers.
- Mark weak alignments as candidates; do not present them as verified evidence.
- When evidence is missing or conflicting, expose that limitation in the answer.

## Data rules

- Treat the GSMA/KU-DF knowledge graph as third-party data.
- Never claim that this repository constructed the upstream Rel-19 graph.
- Do not commit downloaded specification documents, generated indexes, or API keys.
- Record source URL, retrieval date, version, and SHA-256 for every external artifact.
- The graph currently points to `24501-j20`, corresponding to TS 24.501 v19.2.0.

## Engineering conventions

- Python 3.11+ is the supported runtime.
- Keep domain models independent from storage and API adapters.
- Bound graph depth, result count, and QA runtime tool-call count.
- Add tests for parsing, filtering, citations, and failure cases.
- Prefer deterministic local processing before adding model calls.

## Verification

Run these checks before presenting a change as complete:

```powershell
python -m compileall -q src tests
python -m unittest discover -s tests -v
```

When `uv` and development dependencies are installed, also run:

```powershell
uv run ruff check .
uv run pyright
uv run pytest
```
