# Install only on the authorized CCWBot Windows workstation, as the current user.
# This only runs the PRIVATE benchmark worker; never bot production, CI or deploy.
[CmdletBinding(DefaultParameterSetName = 'Status')]
param(
    [Parameter(Mandatory = $true, ParameterSetName = 'Install')]
    [switch] $Install,

    [Parameter(Mandatory = $true, ParameterSetName = 'Uninstall')]
    [switch] $Uninstall
)
$ErrorActionPreference = 'Stop'
$taskName = 'CCWBot-PR349-EventSignificanceReplay'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop
    Write-Host "Removed task $taskName (private replay ledger left intact)"
    exit 0
}

if ($Install) {
    $python = Join-Path $project '.venv\Scripts\python.exe'
    $worker = Join-Path $project 'scripts\auto_event_significance_replay.py'
    $private = Join-Path $project 'reports\event-alert-review-20261016'
    foreach ($required in @(
        $python,
        $worker,
        (Join-Path $private 'v2_private_sanitized.json'),
        (Join-Path $private 'reviewer_A_significance_for_pr1.json'),
        (Join-Path $private 'merged_pilots_private\replay_state.json')
    )) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Missing required local project file: $required"
        }
    }

    # Run only while the current user is logged on. Never store passwords or
    # embed the Groq API key in the scheduler command line.
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
    $action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $worker + '" --once') -WorkingDirectory $project
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) `
        -RepetitionInterval (New-TimeSpan -Hours 1) `
        -RepetitionDuration (New-TimeSpan -Days 365)
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -StartWhenAvailable
    Register-ScheduledTask -TaskName $taskName -Action $action `
        -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'Local capped PR349 Event Alert quality benchmark; no Telegram sends' `
        -Force | Out-Null
    Write-Host "Installed ${taskName}: one safe attempt/hour when signed in, with rolling 24h caps."
    Write-Host 'View private results at reports/event-alert-review-20261016/merged_pilots_private/hourly_replay_status.json'
    exit 0
}

Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue |
    Select-Object TaskName, State, TaskPath
