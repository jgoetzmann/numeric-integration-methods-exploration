# Start the rk run after a Windows sign-in, unless it was stopped on purpose.
#   .\autostart.ps1 -Install     register the logon task that runs this script
#   .\autostart.ps1 -Uninstall   remove it
#   .\autostart.ps1              what the task runs: wait for Docker, then start.ps1
#
# Why (DECISIONS D47): nothing started the run after a reboot. The container may come back
# with Docker, but the watchdog and the stats writer are plain processes and do not, so a
# reboot left the run with no guard, no push and no resume until someone ran start.ps1.
#
# A deliberate stop survives the reboot. stop.ps1 writes run-stopped.txt and start.ps1
# deletes it, and this script does nothing while that file or rk-work\STOP exists.
param([switch]$Install, [switch]$Uninstall, [int]$DockerWaitMinutes = 10)
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
$logFile = Join-Path $root "autostart.log"
$taskName = "rk-run autostart"

function Say([string]$msg) {
    $line = "$([datetime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'", [Globalization.CultureInfo]::InvariantCulture)) $msg"
    Write-Host $line
    try { Add-Content -Path $logFile -Value $line -Encoding ascii } catch {}
}

if ($Install) {
    $user = "$env:USERDOMAIN\$env:USERNAME"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File `"$PSCommandPath`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
    $trigger.Delay = "PT1M"    # let the desktop settle before Docker is asked for anything
    # Task defaults would refuse to start on battery and would stop the task on unplugging.
    # The watchdog owns the battery rule (it pauses the container), so the task does not.
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
    $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
    try {
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Starts the rk run after sign-in unless stop.ps1 stopped it (rk-harness DECISIONS D47)." -Force -ErrorAction Stop | Out-Null
    } catch { Say "could not register the scheduled task '$taskName': $_"; exit 1 }
    Say "registered the scheduled task '$taskName' (at sign-in of $user, after one minute)"
    exit 0
}
if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Say "removed the scheduled task '$taskName'"
    exit 0
}

if (Test-Path (Join-Path $root "run-stopped.txt")) { Say "run-stopped.txt is present, so stop.ps1 was the last word; not starting"; exit 0 }
if (Test-Path (Join-Path $root "rk-work\STOP")) { Say "rk-work\STOP is present; not starting"; exit 0 }

# Docker Desktop may still be starting, or may not start at sign-in at all.
$deadline = (Get-Date).AddMinutes($DockerWaitMinutes)
$launched = $false
while ($true) {
    $null = docker info 2>$null
    if ($LASTEXITCODE -eq 0) { break }
    if (-not $launched) {
        $exe = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
        if (Test-Path $exe) { Start-Process $exe; Say "Docker did not answer; launched Docker Desktop" }
        $launched = $true
    }
    if ((Get-Date) -gt $deadline) { Say "Docker did not answer within $DockerWaitMinutes min; not starting"; exit 1 }
    Start-Sleep -Seconds 10
}

# Docker may have brought the container back by itself. With a watchdog alive too there is
# nothing to do; without one, start.ps1 recreates both, at the cost of at most one cycle.
$status = docker inspect -f "{{.State.Status}}" rk 2>$null
$watchdog = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*watchdog.ps1*" -and $_.CommandLine -notlike "*-Once*" }
if (($status -eq "running" -or $status -eq "paused") -and $watchdog) { Say "rk is $status and a watchdog is running; nothing to do"; exit 0 }

Say "starting the run with start.ps1 (container was: $(if ($status) { $status } else { 'absent' }))"
try {
    & (Join-Path $root "start.ps1") *>&1 | ForEach-Object { Say "  $_" }
    Say "start.ps1 finished"
} catch {
    Say "start.ps1 FAILED: $_"
    exit 1
}
