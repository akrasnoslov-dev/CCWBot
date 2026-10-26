# One-time migration. Run in the existing CCWBot checkout after pulling dev.
# Does not delete anything until git push and remote SHA verification succeed.
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $root
try {
    $branch = (& git branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or $branch -ne "dev") {
        throw "Switch to dev before publishing Graphify."
    }
    $dirtyTracked = @(& git status --porcelain --untracked-files=no)
    if ($dirtyTracked.Count -gt 0) {
        throw "Tracked changes exist. Preserve/commit them before Graphify migration."
    }
    foreach ($required in @("graphify-out/graph.json", "graphify-out/GRAPH_REPORT.md")) {
        if (!(Test-Path $required)) { throw "Required current graph file missing: $required" }
    }

    # Do not print matched credentials. This is a basic guard, not a complete secret audit.
    $credentialPattern = '-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----|\bghp_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|\bsk-proj-[A-Za-z0-9_-]{20,}\b|\b\d{7,11}:[A-Za-z0-9_-]{35}\b'
    $allowedRoot = @(
        "graph.json", "graph.html", "GRAPH_REPORT.md", "manifest.json",
        ".graphify_labels.json", ".graphify_labels.json.sig",
        ".graphify_learning.json"
    )
    foreach ($item in $allowedRoot) {
        $p = Join-Path "graphify-out" $item
        if (Test-Path $p) {
            $text = [IO.File]::ReadAllText((Resolve-Path $p).Path)
            if ([regex]::IsMatch($text, $credentialPattern)) {
                throw "Potential credential in $p. Review and sanitize before uploading."
            }
        }
    }
    if (Test-Path "graphify-out/reflections") {
        foreach ($file in Get-ChildItem "graphify-out/reflections" -Recurse -File) {
            $text = [IO.File]::ReadAllText($file.FullName)
            if ([regex]::IsMatch($text, $credentialPattern)) {
                throw "Potential credential in $($file.FullName). Review before uploading."
            }
        }
    }

    # Validate actual JSON (the graph must already exist; no extraction run here).
    $graph = Get-Content "graphify-out/graph.json" -Raw | ConvertFrom-Json
    if (!($graph.nodes) -or !($graph.links)) {
        throw "graph.json is empty or missing expected nodes/links."
    }
    Write-Host "Graph ready: $(@($graph.nodes).Count) nodes"

    & git add -A -- graphify-out/
    if ($LASTEXITCODE -ne 0) { throw "git add failed" }
    & git diff --cached --check
    if ($LASTEXITCODE -ne 0) { throw "Staged graph files fail git whitespace check" }

    $staged = @(& git diff --cached --name-only)
    if ($staged.Count -gt 0) {
        foreach ($path in $staged) {
            if ($path -notmatch '^graphify-out/') {
                throw "Unexpected staged path: $path"
            }
        }
        $env:GRAPHIFY_SKIP_HOOK = "1"
        & git commit -m "chore(graphify): publish curated repository graph"
        if ($LASTEXITCODE -ne 0) { throw "Graph commit failed" }
        & git push origin dev
        if ($LASTEXITCODE -ne 0) { throw "Git push failed; no cleanup performed" }
    } else {
        Write-Host "Graph files are already tracked and unchanged."
    }

    # Confirm current HEAD exists on origin/dev before local cleanup.
    $localHead = (& git rev-parse HEAD).Trim()
    $remoteLine = (& git ls-remote origin refs/heads/dev)
    if ($LASTEXITCODE -ne 0 -or !$remoteLine) { throw "Cannot verify remote dev." }
    $remoteHead = ($remoteLine -split '\s+')[0]
    if ($localHead -ne $remoteHead) {
        throw "Remote dev moved; no cleanup performed. Reconcile and retry."
    }
    Write-Host "Verified: graph commit is on origin/dev."

    # Only disposable Graphify-generated local data, not repository-tracked files.
    Get-ChildItem "graphify-out" -Directory | Where-Object {
        $_.Name -match '^\d{4}-\d{2}-\d{2}$' -or
        $_.Name -in @("cache", "logs")
    } | Remove-Item -Recurse -Force
    foreach ($name in @(
        ".graphify_python", ".graphify_root", ".vocab.txt",
        ".graphify_analysis.json", ".graphify_detect.json",
        ".graphify_ast.json", ".graphify_extract.json",
        ".graphify_semantic.json", ".graphify_semantic_new.json",
        ".graphify_incremental.json", ".graphify_uncached.txt",
        ".graphify_cached.json", ".graphify_old.json"
    )) {
        $path = Join-Path "graphify-out" $name
        if (Test-Path $path) { Remove-Item $path -Force }
    }

    # Drop local-only Graphify hooks. Future dev pushes update the shared graph.
    $env:PYTHONHASHSEED = "0"
    & graphify hook uninstall
    if ($LASTEXITCODE -ne 0) { Write-Warning "Graphify hook uninstall did not succeed. Inspect local hooks." }
    $hooksDir = (& git rev-parse --git-path hooks).Trim()
    foreach ($name in @("post-merge", "post-rewrite")) {
        $path = Join-Path $hooksDir $name
        if ((Test-Path $path) -and
            ((Get-Content $path -Raw) -match '-m graphify update')) {
            Remove-Item $path -Force
        }
    }
    Write-Host "Current graph is stored in GitHub dev; ignored historical local state removed."
    & git status --short
} finally {
    Pop-Location
}
