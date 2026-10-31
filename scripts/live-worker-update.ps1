<#
.SYNOPSIS
  Owner-only Deploy step 4: update the live folder and restart the live worker.

.DESCRIPTION
  Run this yourself after merging to main; agents never run it (R-0009).

  1. git pull in C:\apps\ReadURList (stops if the folder isn't on a clean main).
  2. Stops the live worker by process ("End" in Task Scheduler stops only the launcher, I3).
  3. uv sync.
  4. Runs the "ReadURList Worker" task and checks exactly one live readurlist.exe runs.

  If the merge adds a database change, run live-db-deploy.ps1 BEFORE merging, as usual.

.EXAMPLE
  .\scripts\live-worker-update.ps1
#>

# Not "Stop": Windows PowerShell treats a tool's progress messages on stderr as errors.
# Each step checks its exit code instead.
$live = "C:\apps\ReadURList"
$task = "ReadURList Worker"

function Get-LiveWorker {
    Get-CimInstance Win32_Process -Filter "Name='readurlist.exe'" |
        Where-Object { $_.ExecutablePath -like "$live\*" }
}

Write-Host "1/4 git pull in $live"
$branch = git -C $live branch --show-current
if ($branch -ne "main") { Write-Error "Live folder is on '$branch', not main. Stopped."; exit 1 }
if (git -C $live status --porcelain) { Write-Error "Live folder has local changes. Stopped."; exit 1 }
git -C $live pull --ff-only
if ($LASTEXITCODE -ne 0) { Write-Error "git pull failed. Nothing else changed."; exit 1 }
git -C $live log --oneline -1

Write-Host "2/4 Stopping the live worker"
Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
foreach ($p in Get-LiveWorker) {
    Write-Host "  stopping PID $($p.ProcessId)"
    Stop-Process -Id $p.ProcessId -Force
}
for ($i = 0; $i -lt 20 -and (Get-LiveWorker); $i++) { Start-Sleep -Milliseconds 500 }
if (Get-LiveWorker) { Write-Error "The live worker is still running. Stopped before uv sync."; exit 1 }

Write-Host "3/4 uv sync"
Push-Location $live
uv sync
$synced = $LASTEXITCODE
Pop-Location
if ($synced -ne 0) { Write-Error "uv sync failed. The worker is NOT running; fix and run the task."; exit 1 }

Write-Host "4/4 Starting the task"
Start-ScheduledTask -TaskName $task
for ($i = 0; $i -lt 30 -and -not (Get-LiveWorker); $i++) { Start-Sleep -Milliseconds 500 }
Start-Sleep -Seconds 3  # give a duplicate time to show up
$workers = @(Get-LiveWorker)
$workers | Select-Object ProcessId, ExecutablePath, CreationDate | Format-Table -AutoSize
if ($workers.Count -ne 1) { Write-Error "Expected exactly one live worker, found $($workers.Count)."; exit 1 }
Write-Host "Done: one live worker, PID $($workers[0].ProcessId)."
