# Release Checklist

Run this checklist before pushing the project to GitHub.

## 1. Local secrets

- `.env` exists only locally.
- No API key appears in README, docs, examples, reports, tests, or source files.
- Any key shared in chat, screenshots, commits, or logs has been rotated.

## 2. Data boundaries

These paths should stay ignored:

- `data/external/specifications/*`
- `data/processed/*`
- `data/indexes/*`
- `data/tkg/`
- `data/chunks/`
- `data/mappings/`
- `reports/generated/*`

Keep only lightweight provenance docs and manually curated examples in Git.

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
git add .env.example .gitignore CLAUDE.md CONTRIBUTING.md LICENSE NOTICE README.md SECURITY.md data\README.md docs examples reports src tests pyproject.toml scripts
git status --short
git commit -m "chore: prepare ts24501 graphrag agent for release"
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
- Add topics such as `graphrag`, `telecom`, `3gpp`, `rag`, `knowledge-graph`, `openai`.
- Confirm that the GitHub file browser does not show `.env` or generated data files.
