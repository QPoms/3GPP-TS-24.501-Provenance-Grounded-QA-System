# Security Policy

## Supported versions

This repository is an early-stage research and demo project. Security fixes
apply to the current `main` branch.

## Reporting a vulnerability

Please report security issues privately to the repository owner. Do not open a
public issue containing API keys, private endpoint URLs, proprietary standards
documents, or sensitive logs.

## API keys

Runtime credentials belong only in local environment variables or a local
`.env` file. The `.env` file is ignored by Git.

If an API key is exposed in chat, an issue, a commit, a screenshot, or a log:

1. Revoke or rotate the key in the provider dashboard.
2. Remove the exposed value from local files and history where possible.
3. Re-run `.\scripts\check_release.ps1` before pushing.

## Data handling

Downloaded 3GPP documents, generated chunks, generated indexes, and bulk
third-party graph files are excluded from Git by default. Review licenses and
redistribution terms before publishing any data artifact.
