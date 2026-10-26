$taskRoot = (Resolve-Path $PSScriptRoot).Path
$taskExpectedExe = Join-Path $taskRoot 'runtime\llama-server.exe'
$taskOutput = Join-Path $taskRoot 'resource_samples.jsonl'
$taskStop = Join-Path $taskRoot 'monitor_stop.flag'
$taskPrevious = @{}
$taskDeadline = [DateTime]::UtcNow.AddMinutes(90)
while ([DateTime]::UtcNow -lt $taskDeadline -and -not (Test-Path -LiteralPath $taskStop)) {
    $taskServers = Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'" | Where-Object ExecutablePath -EQ $taskExpectedExe
    foreach ($taskServer in $taskServers) {
        try {
            $taskProcess = Get-Process -Id $taskServer.ProcessId -ErrorAction Stop
            $taskModel = if ($taskServer.CommandLine -match 'Qwen3-4B') { 'qwen4' } elseif ($taskServer.CommandLine -match 'Phi-4-mini') { 'phi' } elseif ($taskServer.CommandLine -match 'qwen2.5-7b') { 'qwen7' } else { 'unknown' }
            $taskTick = [Diagnostics.Stopwatch]::GetTimestamp()
            $taskCpu = $taskProcess.TotalProcessorTime.TotalSeconds
            $taskCores = $null
            if ($taskPrevious.ContainsKey($taskProcess.Id)) {
                $taskPrior = $taskPrevious[$taskProcess.Id]
                $taskElapsed = ($taskTick - $taskPrior.tick) / [Diagnostics.Stopwatch]::Frequency
                if ($taskElapsed -gt 0) { $taskCores = ($taskCpu - $taskPrior.cpu) / $taskElapsed }
            }
            $taskPrevious[$taskProcess.Id] = @{ tick = $taskTick; cpu = $taskCpu }
            @{ utc = [DateTime]::UtcNow.ToString('o'); model = $taskModel; process_cpu_seconds = $taskCpu; active_logical_cpu_equivalents = $taskCores; working_set_bytes = $taskProcess.WorkingSet64; peak_working_set_bytes = $taskProcess.PeakWorkingSet64; private_memory_bytes = $taskProcess.PrivateMemorySize64 } | ConvertTo-Json -Compress | Add-Content -LiteralPath $taskOutput
        } catch { }
    }
    Start-Sleep -Seconds 1
}
