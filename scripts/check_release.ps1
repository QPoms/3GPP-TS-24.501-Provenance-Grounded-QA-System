$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

if (-not (Test-Path ".git")) {
    throw "Run this script from a Git repository."
}

$requiredIgnored = @(
    ".env",
    "data/external/specifications/24501-j20.zip",
    "data/external/specifications/24501-j20/24501-j20.docx",
    "data/processed/chunks/ts24501_v19_2_0.jsonl",
    "data/processed/graph/ts24501_working_subgraph.graphml",
    "data/tkg/rel19_3gpp_telecom_kg.graphml"
)

foreach ($path in $requiredIgnored) {
    if (Test-Path $path) {
        $ignored = git check-ignore $path 2>$null
        if (-not $ignored) {
            throw "Sensitive or generated path is not ignored: $path"
        }
    }
}

$candidates = git ls-files --cached --others --exclude-standard |
    Where-Object {
        $_ -notmatch '^(data/external|data/processed|data/indexes|data/tkg|data/chunks|data/mappings|reports/generated)/' -and
        $_ -notmatch '^\.git/' -and
        $_ -notmatch '^\.venv/'
    }

$secretPattern = "sk-" + "[A-Za-z0-9_-]{20,}"
$violations = @()

foreach ($file in $candidates) {
    if (-not (Test-Path $file -PathType Leaf)) {
        continue
    }
    $matches = Select-String -Path $file -Pattern $secretPattern -AllMatches -ErrorAction SilentlyContinue
    foreach ($match in $matches) {
        $violations += "${file}:$($match.LineNumber)"
    }
}

if ($violations.Count -gt 0) {
    $message = "Potential secret found in release candidate files:`n" + ($violations -join "`n")
    throw $message
}

Write-Output "Release check passed: ignored data boundaries and no key-like strings found."
