# Stop the rk run.
#   .\stop.ps1          graceful: stop the watchdog, drop the STOP killfile, wait for the cycle boundary
#   .\stop.ps1 -Force   kill the container now (at most one cycle is lost; state replays on restart)
param([switch]$Force, [int]$WaitMinutes = 20)
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
$work = Join-Path $root "rk-work"

# The watchdog goes first. It starts the container again after its own stops (DECISIONS D46),
# so while it lives it could bring back a container this script has just found stopped.
# Stopping it first means nothing below races it. The container keeps running meanwhile,
# and a graceful stop is at most one cycle long. Both helpers run under Windows PowerShell,
# and one process listing filtered to it in the query serves both matchers in this script:
# listing every process's command line costs about half a second more each time.
$shells = @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'")
$wd = $shells | Where-Object { $_.CommandLine -like "*watchdog.ps1*" -and $_.CommandLine -notlike "*-Once*" }
foreach ($p in $wd) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host "watchdog stopped (pid $($p.ProcessId))" }
# A deliberate stop also ends any restart the watchdog had pending: a watchdog started again
# by hand would otherwise find its own stop record, see the condition cleared, and start
# the run this script stops.
Remove-Item (Join-Path $root "watchdog-state.json") -ErrorAction SilentlyContinue
# And it outlasts a reboot: autostart.ps1 does not start the run while this file exists, and
# start.ps1 deletes it (DECISIONS D47).
Set-Content -Path (Join-Path $root "run-stopped.txt") -Encoding ascii -Value ("stop.ps1 stopped the run at " + [datetime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'", [Globalization.CultureInfo]::InvariantCulture) + ". start.ps1 deletes this file; autostart.ps1 will not start the run while it exists.")

# The runner ignores SIGTERM, so docker stop only ever ended in SIGKILL once the container's
# stop timeout ran out. A forced stop sends SIGKILL at once.
$killed = $false
$running = (docker inspect -f "{{.State.Status}}" rk 2>$null)
if ($running -eq "paused") { docker unpause rk | Out-Null; $running = "running" }
if ($running -eq "running") {
    if ($Force) {
        docker kill rk | Out-Null
        $killed = $true
        Write-Host "container killed (forced)"
    } else {
        Set-Content -Path (Join-Path $work "STOP") -Value "stop" -Encoding ascii
        Write-Host "STOP written; waiting for the runner to finish its cycle (up to $WaitMinutes min)..."
        $deadline = (Get-Date).AddMinutes($WaitMinutes)
        while ((Get-Date) -lt $deadline -and (docker inspect -f "{{.State.Status}}" rk 2>$null) -eq "running") { Start-Sleep 10 }
        if ((docker inspect -f "{{.State.Status}}" rk 2>$null) -eq "running") {
            Write-Host "still running after $WaitMinutes min; forcing"; docker kill rk | Out-Null
            $killed = $true
        }
        Remove-Item (Join-Path $work "STOP") -ErrorAction SilentlyContinue
        Write-Host "container stopped at a cycle boundary"
    }
} else {
    Write-Host "container is not running ($running)"
}

# A kill can land inside a git add or commit and leave a lock file in rk-work or rk-findings.
# The runner clears locks at start only once they are ten minutes old, so a start soon after
# a kill would commit nothing all run. The container is gone and the watchdog that pushes
# was stopped above, so none of the run's git processes can still hold one.
if ($killed -and (docker inspect -f "{{.State.Status}}" rk 2>$null) -ne "running") {
    foreach ($r in @("rk-work", "rk-findings")) {
        $git = Join-Path (Join-Path $root $r) ".git"
        $locks = @(Get-ChildItem -Path $git -Filter "*.lock" -File -ErrorAction SilentlyContinue) +
                 @(Get-ChildItem -Path (Join-Path $git "refs") -Filter "*.lock" -File -Recurse -ErrorAction SilentlyContinue)
        foreach ($l in $locks) { Remove-Item $l.FullName -Force -ErrorAction SilentlyContinue; Write-Host "removed $r git lock $($l.Name)" }
    }
}


# Stop the background stats writer start.ps1 launched. Matched by this script's own full
# path, escaped for -like, and never by a *stats.ps1* wildcard: a second harness sharing
# this workspace may ship its own stats.ps1, and rk's *watchdog.ps1* matcher above is
# already why that harness has to name its watchdog scripts/watchdog-jobs.ps1.
$statsPath = Join-Path $root "stats.ps1"
$statsPattern = [System.Management.Automation.WildcardPattern]::Escape($statsPath)
$sw = $shells | Where-Object { $_.CommandLine -like "*$statsPattern*" -and $_.CommandLine -like "*-Loop*" }
foreach ($p in $sw) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host "stats writer stopped (pid $($p.ProcessId))" }

# One final one-shot write, so stats.txt's last state is the stopped container and its own
# fifteen-minute shelf life starts running from here. stats.ps1 sets $ErrorActionPreference
# to Stop internally, so a failure there would otherwise take this script down with it.
try { & $statsPath -NoGpu | Out-Null; Write-Host "stats.txt written (one-shot; it declares its own shelf life)" }
catch { Write-Host "final stats write failed: $_" }

# Push anything the container committed but the watchdog had not pushed yet.
foreach ($r in @("rk-work", "rk-findings")) {
    $path = Join-Path $root $r
    $ahead = cmd /c "git -C `"$path`" rev-list --count @{u}..HEAD 2>&1"
    if ($ahead -match '^\d+$' -and [int]$ahead -gt 0) { cmd /c "git -C `"$path`" push -q origin HEAD 2>&1" | Out-Null; Write-Host "pushed $ahead commit(s) from $r" }
}
