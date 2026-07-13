# Release Checklist

Run this checklist before pushing the project to GitHub.

## 1. Local secrets

- `.env` exists only locally.
- No API key appears in README, docs, examples, reports, tests, or source files.
- Any key shared in chat, screenshots, commits, or logs has been rotated.

## 2. Data boundaries

These paths should stay ignored:

- `data/external/specifications/*`
- `data/processed/chunks/*`
- `data/indexes/*`
- large `data/tkg/*` files except `data/tkg/rel19_24501_subgraph_gephi_lite.graphml`
- `data/chunks/`
- `data/mappings/`
- `reports/generated/*`

Keep only lightweight provenance docs, manually curated examples, and the explicitly
published inspectable data artifacts in Git.

## 3. Verification

```powershell
.\scripts\check_release.ps1
$env:PYTHONPATH='tests'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\kg-agent.exe ask "What is replay protection in NAS signalling?" --json
```

If the optional ingestion dependencies are installed, DOCX tests should run instead of skip.

## 4. Git

```powershell
git status --short
git add .env.example .gitignore CLAUDE.md CONTRIBUTING.md LICENSE NOTICE README.md SECURITY.md data\README.md data\manifest.json data\processed\alignments\ts24501_lexical.jsonl data\processed\graph\ts24501_working_subgraph.graphml data\tkg\rel19_24501_subgraph_gephi_lite.graphml docs examples reports src tests pyproject.toml scripts
git status --short
git commit -m "chore: prepare ts24501 provenance qa system for release"
```

Inspect staged files before committing:

```powershell
git diff --cached --stat
git diff --cached --name-only
```

## 5. GitHub repository

- Create a new public repository.
- Push `main`.
- Add a concise repository description.
- Add topics such as `telecom`, `3gpp`, `rag`, `knowledge-graph`, `provenance`, `openai`.
- Confirm that the GitHub file browser does not show `.env`, raw 3GPP documents, full-text
  generated chunks, cache files, or large upstream graph files.
