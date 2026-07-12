# Contributing

Thanks for taking a look at this project. The repository is intentionally
small and evidence-focused: it should answer questions about 3GPP TS 24.501
only when it has retrieved supporting specification evidence.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Optional extras:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ingestion]"
.\.venv\Scripts\python.exe -m pip install -e ".[retrieval]"
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Before opening a change

Run:

```powershell
.\scripts\check_release.ps1
$env:PYTHONPATH='tests'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

If optional ingestion dependencies are not installed, DOCX ingestion tests may
be skipped. Install `.[ingestion]` when changing ingestion code.

## Data and secret boundaries

Do not commit:

- `.env`
- API keys or screenshots containing API keys
- downloaded 3GPP specification files
- generated chunks, alignments, vector indexes, or audit JSON files
- bulk upstream graph files unless their redistribution terms have been
  checked and the project owner has explicitly decided to publish them

Keep source code, third-party data, and generated artifacts separate.

## Evidence rules

- Do not answer standards questions from model memory alone.
- Every final standards claim should be grounded in retrieved evidence.
- A final `chunk_id` citation must have been returned by a tool in the same run.
- Graph paths are hints, not sufficient evidence by themselves.
- If evidence is weak, conflicting, or missing, say that directly.
