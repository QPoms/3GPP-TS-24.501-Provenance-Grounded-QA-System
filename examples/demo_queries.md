# Demo Queries

Use these prompts to show the project on a GitHub profile, in a short screen recording, or
in a competition submission.

## QA questions

```powershell
.\.venv\Scripts\kg-agent.exe ask "How is replay protection handled for NAS signalling?"
```

```powershell
.\.venv\Scripts\kg-agent.exe ask "When is integrity protection applied to NAS signalling?"
```

```powershell
.\.venv\Scripts\kg-agent.exe ask "What is the role of NAS COUNT in 5G NAS security?"
```

```powershell
.\.venv\Scripts\kg-agent.exe ask "What evidence does TS 24.501 give for SECURITY PROTECTED 5GS NAS MESSAGE fields?" --json
```

## Deterministic retrieval commands

```powershell
.\.venv\Scripts\kg-agent.exe search-spec "replay protection NAS COUNT integrity verification" --top-k 3
```

```powershell
.\.venv\Scripts\kg-agent.exe resolve "5G NAS security context"
```

```powershell
.\.venv\Scripts\kg-agent.exe neighbors "Replay protection" --limit 10
```

```powershell
.\.venv\Scripts\kg-agent.exe eval-retrieval --output reports\generated\bm25_eval.json
```

## What a good answer should show

- A concise answer grounded in TS 24.501.
- Section and page metadata when available.
- `chunk_id` citations that were returned by tools in the same run.
- Clear evidence limitations when the specification does not mandate an implementation detail.
- No claim that graph paths alone prove a standards behavior.
