# Publish screened Event Alert research evidence from an existing local staging directory.
# Intentionally fails closed on sensitive-looking content. Never deletes source files.
# Requires Windows PowerShell 5.1+, git and an authenticated origin remote.
[CmdletBinding()]
param([switch]$Push)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$stage = Join-Path $repo 'research\event_alerts\imported_reports_20261026\reports'
$relativeDestination = 'research/event_alerts/versioned_evidence_20261026/reports'
$destination = Join-Path $repo ($relativeDestination.Replace('/', '\'))
$manifestDirectory = Join-Path $repo 'research\event_alerts\versioned_evidence_20261026'

if (-not (Test-Path -LiteralPath $stage -PathType Container)) {
    throw "Research staging directory not found: $stage"
}
Set-Location $repo
$branch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -ne 'dev') { throw 'Current branch must be dev.' }
& git diff --quiet
if ($LASTEXITCODE -ne 0) { throw 'Tracked worktree changes found. No automatic changes were made.' }
& git diff --cached --quiet
if ($LASTEXITCODE -ne 0) { throw 'Staged changes found. No automatic changes were made.' }
& git fetch --quiet origin dev
if ($LASTEXITCODE -ne 0) { throw 'Cannot fetch origin/dev.' }
$localHead = (& git rev-parse HEAD).Trim()
$remoteHead = (& git rev-parse origin/dev).Trim()
if ($localHead -ne $remoteHead) { throw 'Local dev is not synchronized with origin/dev. First run git pull --ff-only origin dev.' }
if (Test-Path -LiteralPath $destination) { Write-Host 'Detected previous staging; existing copies will be hash-verified.' }

$sourceFiles = @(Get-ChildItem -LiteralPath $stage -Recurse -File -Force -ErrorAction Stop)
if ($sourceFiles.Count -ne 426) {
    throw "Expected 426 staged source files; found $($sourceFiles.Count). No files were published."
}

# Keep every excluded file in place. Recorded exclusion hashes permit later reconciliation.
$denyPath = '(?i)(^|/)(dev-source|__pycache__|\.pytest_cache|\.ruff_cache|node_modules|\.venv)(/|$)|(^|/)(\.env(?:\.[^/]*)?|[^/]*(?:credential|secret|api[_-]?key|private[_-]?key|password)[^/]*)(/|$)|\.(?:pyc|pyo|log|zip|db|sqlite|sqlite3|dump|bak|pem|key|p12|pfx|safetensors|gguf|ckpt)$|(?:host_evidence|workstation|resource_samples|pre_scrub)'
$allowExtensions = @('.txt','.md','.json','.jsonl','.csv','.py','.html','.js','.yml','.yaml','.toml')
$secretText = '(?i)(?:sk-[A-Za-z0-9_-]{20,}|gsk_[A-Za-z0-9_-]{20,}|github_pat_[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{25,}|xox[baprs]-[A-Za-z0-9-]{12,}|-----BEGIN [^-\r\n]*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._~-]{25,})'
$personalText = '(?i)(?:telegram[_-]?(?:user|chat)[_-]?id|(?:^|[^a-z_])(?:user_id|chat_id|phone_number|email_address)(?:[^a-z_]|$)|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b)'
# Host/IP traces and credential assignment are never copied to the public research area.
$highRiskText = '(?i)(?:postgres(?:ql)?://[^\s''"<>]+:[^\s''"<>]+@|(?:TELEGRAM_BOT_TOKEN|OPENAI_API_KEY|GROQ_API_KEY|CLOUDFLARE_API_TOKEN)\s*[:=]\s*["'']?[A-Za-z0-9_-]{20,})'

$strictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
$allowed = New-Object System.Collections.Generic.List[object]
$excluded = New-Object System.Collections.Generic.List[object]
foreach ($file in $sourceFiles) {
    $rel = $file.FullName.Substring($stage.Length).TrimStart('\').Replace('\','/')
    $reason = $null
    if ($rel -match $denyPath) { $reason = 'sensitive_or_duplicate_path' }
    elseif ($file.Length -gt 20MB) { $reason = 'large_file_review_required' }
    elseif ($file.Extension.ToLowerInvariant() -notin $allowExtensions) { $reason = 'unsupported_binary_or_format' }
    else {
        try { $text = $strictUtf8.GetString([System.IO.File]::ReadAllBytes($file.FullName)) }
        catch [System.Text.DecoderFallbackException] { $reason = 'non_utf8_data_requires_review' }
        if (-not $reason) {
            if ($text -match $secretText -or $text -match $highRiskText) { $reason = 'secret_pattern_requires_manual_redaction' }
            elseif ($text -match $personalText) { $reason = 'personal_data_or_identifier_requires_redaction' }
            elseif ($text -match '(?i)(?:PRIVATE KEY|\.env\.production|password\s*[:=]\s*["''][^"'']{6,})') { $reason = 'sensitive_context_requires_redaction' }
        }
    }
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $meta = [ordered]@{ path=$rel; sha256=$hash; bytes=$file.Length }
    if ($reason) {
        $meta['reason'] = $reason
        $excluded.Add([pscustomobject]$meta)
    } else { $allowed.Add([pscustomobject]$meta) }
}

if ($allowed.Count -eq 0) { throw 'All source files screened out; nothing to publish.' }
New-Item -ItemType Directory -Force -Path $manifestDirectory | Out-Null
foreach ($entry in $allowed) {
    $src = Join-Path $stage ($entry.path.Replace('/', '\'))
    $dst = Join-Path $destination ($entry.path.Replace('/', '\'))
    New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
    if (-not (Test-Path -LiteralPath $dst)) { Copy-Item -LiteralPath $src -Destination $dst }
    $copyHash = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($copyHash -ne $entry.sha256) { throw "Copy hash mismatch: $($entry.path)" }
}

$manifest = [ordered]@{
    schema='ccwbot-research-public-evidence-v1'
    source='local staged research evidence exported from full reports archive'
    source_file_count=$sourceFiles.Count
    imported_file_count=$allowed.Count
    excluded_file_count=$excluded.Count
    source_tree='research/event_alerts/imported_reports_20261026/reports'
    imported_tree=$relativeDestination
    warning='Screened for common secrets and identifying strings. Excluded files remain local for separate review. Never assume file-level heuristics certify all privacy.'
    imported=$allowed.ToArray()
    excluded=$excluded.ToArray()
}
$manifestPath = Join-Path $manifestDirectory 'IMPORT_MANIFEST.json'
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
$readmePath = Join-Path $manifestDirectory 'README.md'
@'
# Archived Event Alert research — reviewed public export

This directory contains research files screened by `scripts/ccwbot_publish_reports.ps1` from the owner's original experiment workspace. Files are copied byte-for-byte and checked against per-file SHA-256. A public-safe automated screen excluded potentially identifying or secret-bearing files as well as redundant source-code snapshots. See `IMPORT_MANIFEST.json` for the exact imported/excluded inventory. Excluded files are *not* in GitHub and may still require privacy review and transfer. This archive is evidence, not production runtime configuration.

The repository remains public. No `.env`, credentials, user IDs, production logs, raw DB backups, or local caches should be published. This screen is conservative but cannot prove comprehensive anonymization of arbitrary free text. Never claim complete local-to-Git parity while excluded evidence remains.
'@ | Set-Content -LiteralPath $readmePath -Encoding UTF8

# reports/ is gitignored everywhere. Explicitly force-add ONLY the screened output.
& git add -f -- "research/event_alerts/versioned_evidence_20261026"
if ($LASTEXITCODE -ne 0) { throw 'git add failed.' }
& git diff --cached --check
if ($LASTEXITCODE -ne 0) { Write-Warning 'Archived source contains whitespace warnings; preserving byte-exact SHA-256 evidence.' }
$staged = @(& git diff --cached --name-only)
if (@($staged | Where-Object {$_ -notlike 'research/event_alerts/versioned_evidence_20261026/*'}).Count -gt 0) {
    throw 'Unexpected staged changes; not committing.'
}
Write-Host "Prepared $($allowed.Count) screened files out of $($sourceFiles.Count). Skipped $($excluded.Count) potentially sensitive, duplicate or unsupported files."
Write-Host "Reviewable manifest: $manifestPath"
if (-not $Push) {
    Write-Host 'DRY RUN ONLY. No commit or push performed. Pass -Push to publish screened files.'
    exit 0
}
& git commit -m 'research: preserve screened historical Event Alert experiments and migration inventory'
if ($LASTEXITCODE -ne 0) { throw 'git commit failed; nothing pushed.' }
$expectedHead = (& git rev-parse HEAD).Trim()
& git push origin dev
if ($LASTEXITCODE -ne 0) { throw 'git push failed; inspect conflict; NEVER force push.' }
& git fetch --quiet origin dev
$publishedHead = (& git rev-parse origin/dev).Trim()
if ($expectedHead -ne $publishedHead) { throw 'GitHub verification failed; origin/dev differs from local commit.' }
Write-Host "PUBLISHED to origin/dev: $publishedHead"
Write-Host "Verified $($allowed.Count) copied files; $($excluded.Count) remain excluded and documented."
