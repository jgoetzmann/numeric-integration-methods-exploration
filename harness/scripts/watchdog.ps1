# Host-side kill switch (HANDOFF section 13.4) and pause watchdog (section 13.5). Hand-written (section 16.1).
# Polls every 10 s. All five triggers live here, outside the container.
param(
    [string]$Work = "D:/rk/work",
    [string]$Container = "rk",
    [string]$EnvFile = "D:/rk/.env",
    [int]$PollSeconds = 10,
    [double]$MinFreeGB = 5.0,
    [int]$HeartbeatStaleSeconds = 120,
    [int]$NoCandidateMinutes = 30,
    [string]$Findings = "D:/rk/findings",
    [int]$PushMinutes = 10,
    [int]$CpuHigh = 70,             # pause when non-container host CPU stays above this ...
    [int]$CpuLow = 30,              # ... unpause when it stays below this ...
    [int]$CpuSustainSeconds = 30,   # ... for this long (the spike triggers)
    [int]$CpuHighAvg = 60,          # ... or when the rolling average tops this ...
    [int]$CpuLowAvg = 40,           # ... or resume when the rolling average is under this ...
    [int]$CpuAvgWindowSeconds = 300, # ... over this window (the average triggers)
    [int]$SaturationCheckSeconds = 1800,  # epoch-saturation orchestrator cadence (0 = off)
    [switch]$NoSaturation,
    [switch]$AutoFreeze,   # without this, saturation checks are advisory: log only, never freeze
    [switch]$NoBatteryGuard,
    [switch]$Once,
    [string]$LogFile = "",          # append every line this script prints here as well
    [string]$PeerContainers = "rk", # comma-separated; only these are subtracted from host load
    [int]$StatsTimeoutMs = 4000,    # hard timeout on the docker stats probe
    [double]$MinFreeSystemGB = 0,   # system-drive floor; 0 = report only, never stop
    [string]$CpuSampleFile = "",    # where to publish the per-poll sample (empty = workspace root)
    [switch]$NoAutoResume,          # never start the container again after a stop this script made
    [int]$ResumeMax = 3,            # at most this many automatic restarts ...
    [double]$ResumeWindowHours = 6, # ... in this rolling window
    [double]$ResumeMarginGB = 2,    # a disk stop resumes only this far above the floor that tripped it
    [int]$ResumeCooldownSeconds = 60, # never start again sooner than this after the stop
    [string]$StateFile = ""         # where stops and restarts are recorded (empty = workspace root)
)
$ErrorActionPreference = "Continue"

# Why this log exists: the watchdog runs in a minimized window nobody looks at, so an ALERT,
# a pause or a kill is printed once and lost. status.py reads the tail of this file back into
# stats.txt, which is the file a human actually opens. Timestamps are UTC with a Z suffix,
# not Get-Date -Format s: that format is local and carries no offset, and status._parse_ts
# treats a naive stamp as UTC, which would be seven hours wrong here. Storage is UTC
# everywhere in this project (house rule 6); the display side converts, not the writer.
$script:LastRotate = [datetime]::MinValue

function Rotate-Log {
    # Logging must never be able to stop the kill switch, hence the outer try/catch.
    try {
        # Stamped first, so a no-op or a failure does not make every poll retry this.
        $script:LastRotate = Get-Date
        if (-not $LogFile) { return }
        $dir = Split-Path $LogFile -Parent
        if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        if (Test-Path $LogFile) {
            $len = (Get-Item $LogFile).Length
            if ($len -gt 1MB) { Move-Item -LiteralPath $LogFile -Destination "$LogFile.1" -Force -ErrorAction SilentlyContinue }
        }
    } catch {}
}

function Say([string]$msg) {
    $line = "$([datetime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')) $msg"
    Write-Host $line
    if ($LogFile) {
        try { Add-Content -Path $LogFile -Value $line -Encoding ascii } catch {}
    }
}

# Epoch saturation orchestrator (owner-delegated, 2026-09-02; rule in docs/ROADMAP.md).
# The decision state lives on disk in rk-work (python side), never in this process.
$HarnessRoot = Split-Path $PSScriptRoot -Parent
$VenvPython = Join-Path $HarnessRoot ".venv/Scripts/python.exe"
$lastSatCheck = [datetime]::MinValue
$freezePending = $false

# Battery guard (owner's rule, 2026-08-29): never run on battery. On battery -> docker pause;
# back on AC -> docker unpause. Pause is atomic, so the run resumes exactly where it was.
Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
function On-Battery {
    try { return ([System.Windows.Forms.SystemInformation]::PowerStatus.PowerLineStatus -eq "Offline") } catch { return $false }
}
$pausedBattery = $false

# Host-side push (HANDOFF section 2.2 intent): the container only commits into the mounted
# /work and /findings; the host pushes them with the owner's own git credentials, so no GitHub
# token ever enters the container.
function Push-Repo([string]$path) {
    if (-not (Test-Path (Join-Path $path ".git"))) { return }
    $ahead = cmd /c "git -C `"$path`" rev-list --count @{u}..HEAD 2>&1"
    if ($ahead -match '^\d+$' -and [int]$ahead -gt 0) {
        $out = cmd /c "git -C `"$path`" push -q origin HEAD 2>&1"
        if ($LASTEXITCODE -eq 0) { Say "pushed $ahead commit(s) from $path" }
        else { Say "push FAILED for ${path}: $out" }
    }
}
$lastPush = Get-Date

function Read-Cap {
    $cap = 50.0
    if (Test-Path $EnvFile) {
        foreach ($line in Get-Content $EnvFile) {
            if ($line -match '^\s*OPENAI_MONTHLY_CAP_USD\s*=\s*([0-9.]+)') { $cap = [double]$Matches[1] }
        }
    }
    return $cap
}

function Get-Spend {
    $p = Join-Path $Work "RUNSTATE.json"
    if (-not (Test-Path $p)) { return 0.0 }
    try { return [double]((Get-Content $p -Raw | ConvertFrom-Json).spend_usd) } catch { return 0.0 }
}

function Get-LastVerifiedAge {
    # minutes since the last "record" event in events.jsonl; $null if no events file
    $p = Join-Path $Work "events.jsonl"
    if (-not (Test-Path $p)) { return $null }
    $last = $null
    foreach ($line in (Get-Content $p -Tail 400)) {
        try {
            $o = $line | ConvertFrom-Json
            if ($o.kind -eq "accepted") { $last = [datetime]::Parse($o.ts).ToUniversalTime() }
        } catch {}
    }
    if ($null -eq $last) { return $null }
    return ((Get-Date).ToUniversalTime() - $last).TotalMinutes
}

function Container-Running {
    $s = docker inspect -f "{{.State.Status}}" $Container 2>$null
    return ($s -eq "running" -or $s -eq "paused")
}

function Container-UptimeSeconds {
    try {
        $st = docker inspect -f "{{.State.StartedAt}}" $Container 2>$null
        if (-not $st) { return 0 }
        return [int]((Get-Date).ToUniversalTime() - [datetime]::Parse($st).ToUniversalTime()).TotalSeconds
    } catch { return 0 }
}

function Get-DockerCpuRows([int]$TimeoutMs) {
    # Every container on the daemon, name -> percent of the whole machine, or $null if the
    # probe did not answer in time. docker stats has no timeout flag of its own and samples
    # every container, so it runs as a child process this function can kill.
    #
    # Why bound it: this call sits on the path that decides whether the run is paused, and
    # this daemon has been seen wedged and answering HTTP 500 on every endpoint. Measured
    # 2026-09-08 on a quiet host over five consecutive calls, the healthy cost is 1.41 s
    # minimum and 2.01 s median, so a 10 s poll becomes roughly 12 s and the 120 s heartbeat
    # window holds about ten samples instead of twelve. That is a skew, not a collapse; the
    # timeout is for the tail, not for the median. (An older note in this project quotes
    # 47 s. That was a saturated machine, and it is not the typical cost.)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "docker"
    $psi.Arguments = 'stats --no-stream --format "{{.Name}},{{.CPUPerc}}"'
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $text = $null
    $p = $null
    try {
        $p = [System.Diagnostics.Process]::Start($psi)
        # Start both reads before waiting. ReadToEnd() before WaitForExit() deadlocks the
        # moment the child fills a pipe buffer.
        $stdout = $p.StandardOutput.ReadToEndAsync()
        $stderr = $p.StandardError.ReadToEndAsync()
        if (-not $p.WaitForExit($TimeoutMs)) {
            try { $p.Kill() } catch {}
            return $null
        }
        if ($p.ExitCode -ne 0) { return $null }
        $null = $stderr
        $text = $stdout.Result
    } catch {
        return $null
    } finally {
        if ($p) { try { $p.Dispose() } catch {} }
    }
    $rows = @{}
    foreach ($line in ($text -split "`r?`n")) {
        $line = $line.Trim()
        if (-not $line) { continue }
        # A Docker container name cannot contain a comma, so the last one splits the row.
        $i = $line.LastIndexOf(',')
        if ($i -lt 1) { continue }
        $name = $line.Substring(0, $i).Trim()
        $s = $line.Substring($i + 1).Trim().TrimEnd('%')
        $pct = 0.0
        # docker prints 12.34%; a plain cast under a comma-decimal locale misparses it, and
        # a container with no reading prints -- which is not a number at all.
        if (-not [double]::TryParse($s, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$pct)) { $pct = 0.0 }
        # Same scale as Get-Counter '\Processor(_Total)\% Processor Time', which is what the
        # thresholds around this were tuned against on 2026-09-03.
        $rows[$name] = $pct / [Environment]::ProcessorCount
    }
    return $rows
}

function Write-CpuSample($rows) {
    # One sampler, both readers (harness-platform item 3), writer half only. A second
    # harness on this machine can read this file instead of making its own docker stats
    # call. Reader contract: a file older than about 2.5 polls counts as absent and the
    # reader samples for itself; no decision may ever wait on it. rk does not read it back,
    # because rk is what wrote it - reading it would only be rk reusing its own last
    # sample, which is the carried-forward value this project refuses everywhere else.
    # Failing to write it must never affect the guard, hence the blanket catch.
    try {
        if (-not $CpuSampleFile) { return }
        $doc = @{ ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
                  by = $Container
                  containers = $rows }
        $tmp = "$CpuSampleFile.tmp"
        Set-Content -Path $tmp -Value ($doc | ConvertTo-Json -Compress) -Encoding ascii
        Move-Item -LiteralPath $tmp -Destination $CpuSampleFile -Force
    } catch {}
}

# Resume (owner's ask, 2026-09-22). Every stop above used to be permanent: on 2026-09-17 the
# system-drive guard stopped the run and it stayed down for five days, logging "watchdog idle"
# every poll, because nothing ever started it again. Each stop this script makes is now
# recorded in $StateFile with the container's id and start time, and the same container is
# started again once the condition behind that stop has cleared. Only this script's own
# stops are resumed. A STOP file, a manual docker stop, the runner's own exit and Docker
# giving up on a crash loop are left alone, because none of them is a condition this script
# can watch clear. The record is on disk rather than in this process, so a watchdog started
# again by hand still knows what it stopped; start.ps1 and stop.ps1 delete it.
function UtcStamp { return [datetime]::UtcNow.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'", [Globalization.CultureInfo]::InvariantCulture) }

function Seconds-Since([string]$stamp) {
    # $null when the stamp does not parse, so a caller never acts on an age it made up.
    try {
        $t = [datetime]::Parse($stamp, [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::AdjustToUniversal -bor [Globalization.DateTimeStyles]::AssumeUniversal)
        return ([datetime]::UtcNow - $t).TotalSeconds
    } catch { return $null }
}

function Get-ContainerFacts {
    # Id, status and start time from one inspect, or $null when Docker does not answer.
    $raw = docker inspect -f "{{.Id}}|{{.State.Status}}|{{.State.StartedAt}}" $Container 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $raw) { return $null }
    $f = "$raw".Trim().Split('|')
    if ($f.Count -lt 3) { return $null }
    return @{ id = $f[0]; status = $f[1]; started = $f[2] }
}

function Read-WatchdogState {
    $s = @{ stop = $null; resumes = @() }
    try {
        if (Test-Path $StateFile) {
            $doc = Get-Content $StateFile -Raw | ConvertFrom-Json
            if ($doc.stop) { $s.stop = $doc.stop }
            if ($doc.resumes) { $s.resumes = @($doc.resumes) }
        }
    } catch { Say "watchdog state unreadable, starting from none: $StateFile" }
    return $s
}

function Write-WatchdogState {
    try {
        $tmp = "$StateFile.tmp"
        Set-Content -Path $tmp -Value ($script:wdState | ConvertTo-Json -Depth 4 -Compress) -Encoding ascii
        Move-Item -LiteralPath $tmp -Destination $StateFile -Force
    } catch { Say "watchdog state not written: $StateFile" }
}

function Recent-Resumes {
    return @($script:wdState.resumes | Where-Object { $a = Seconds-Since $_; $null -ne $a -and $a -le $ResumeWindowHours * 3600 })
}

function Free-GB-Work {
    try { return [double](Get-Item $Work -ErrorAction Stop).PSDrive.Free / 1GB } catch { return $null }
}

function Free-GB-System {
    try { return [double]((Get-PSDrive -Name $env:SystemDrive.TrimEnd(':') -ErrorAction Stop).Free) / 1GB } catch { return $null }
}

function Resume-Promise([string]$reason) {
    # What the log line for a stop says will bring the run back.
    if ($NoAutoResume) { return "auto-resume is off; start.ps1 brings it back" }
    switch ($reason) {
        "heartbeat" { return "resumes after ${ResumeCooldownSeconds}s" }
        "spend"     { return "start.ps1 brings it back once the cap in .env is raised" }
        "disk"      { return "resumes at $($MinFreeGB + $ResumeMarginGB) GB free" }
        "system"    { return "resumes at $($MinFreeSystemGB + $ResumeMarginGB) GB free" }
    }
    return "not resumed"
}

function Stop-Run([string]$reason, [string]$verb, [string]$why) {
    # Every stop this script makes comes through here, so none can go unrecorded. The id and
    # start time are read while the container is still up, and the record is written only
    # once Docker confirms the stop: a failed stop leaves no record to resume from.
    $facts = Get-ContainerFacts
    Say "$why -> docker $verb; $(Resume-Promise $reason)"
    docker $verb $Container | Out-Null
    if ($LASTEXITCODE -eq 0 -and $facts) {
        $script:wdState.stop = @{ reason = $reason; ts = (UtcStamp); id = $facts.id; started = $facts.started }
        Write-WatchdogState
    }
}

function Resume-Blocker($stop) {
    # Why the container must stay down, or "" when it may be started again.
    if ($NoAutoResume) { return "auto-resume is off; start.ps1 brings it back" }
    if (Test-Path (Join-Path $Work "STOP")) { return "a STOP file is present, so it stays down" }
    if ($freezePending) { return "an epoch freeze is pending, so it stays down" }
    if (-not $NoBatteryGuard -and (On-Battery)) { return "waiting for AC power" }
    $since = Seconds-Since ([string]$stop.ts)
    if ($null -eq $since) { return "the stop record carries no readable time; start.ps1 brings it back" }
    if ($since -lt $ResumeCooldownSeconds) { return "cooling down for ${ResumeCooldownSeconds}s" }
    switch ([string]$stop.reason) {
        "heartbeat" { }
        "spend" {
            # Not resumed. docker start keeps the environment the container was created with,
            # and the runner reads the cap from that environment before .env, so a raised cap
            # reaches it only through start.ps1, which recreates the container.
            return "a spend stop needs start.ps1, which recreates the container with the cap in .env"
        }
        "disk" {
            $free = Free-GB-Work; $need = $MinFreeGB + $ResumeMarginGB
            if ($null -eq $free) { return "free space on the work drive is unknown" }
            if ($free -lt $need) { return "resumes at $need GB free on the work drive, now $([math]::Round($free, 1))" }
        }
        "system" {
            $free = Free-GB-System; $need = $MinFreeSystemGB + $ResumeMarginGB
            if ($MinFreeSystemGB -gt 0) {
                if ($null -eq $free) { return "free space on $env:SystemDrive is unknown" }
                if ($free -lt $need) { return "resumes at $need GB free on $env:SystemDrive, now $([math]::Round($free, 1))" }
            }
        }
        default { return "a '$($stop.reason)' stop is not one this script resumes" }
    }
    # @() because a function returns a one-element array as the bare element, and indexing a
    # bare string below would take its last character rather than the last stamp.
    $recent = @(Recent-Resumes)
    if ($recent.Count -ge $ResumeMax) { return "restart limit reached: $ResumeMax in the last ${ResumeWindowHours}h, so it waits for the oldest to age out" }
    if ($recent.Count -gt 0) {
        # A docker start that fails leaves the record in place, and without this every poll
        # would retry and spend the whole budget in half a minute, for example while Docker
        # Desktop is still bringing its mounts back after sleep. Each restart in the window
        # doubles the wait since the last one.
        $gap = $ResumeCooldownSeconds * [math]::Pow(2, $recent.Count)
        $last = Seconds-Since ([string]$recent[-1])
        if ($null -ne $last -and $last -lt $gap) { return "backing off, next try ${gap}s after the last restart" }
    }
    return ""
}

function Resume-Run($stop) {
    $n = @(Recent-Resumes).Count + 1
    Say "$($stop.reason) stop at $($stop.ts) has cleared -> docker start (restart $n of at most $ResumeMax in ${ResumeWindowHours}h)"
    $out = docker start $Container 2>&1
    $ok = ($LASTEXITCODE -eq 0)
    $script:wdState.resumes = @(Recent-Resumes) + @(UtcStamp)
    if ($ok) { $script:wdState.stop = $null } else { Say "docker start FAILED: $out" }
    Write-WatchdogState
}

$script:idleKey = ""
$script:idleAt = [datetime]::MinValue
function Say-Idle([string]$key, [string]$msg) {
    # A stopped container used to print the same line every poll, 8,640 a day. Now a line is
    # printed when what the watchdog is waiting on changes, and every ten minutes while it holds.
    if ($key -ne $script:idleKey -or ((Get-Date) - $script:idleAt).TotalMinutes -ge 10) {
        Say $msg
        $script:idleKey = $key
        $script:idleAt = Get-Date
    }
}

function Handle-Down([string]$status) {
    # The container is neither running nor paused. Resume it only if this script stopped it.
    $stop = $script:wdState.stop
    if (-not $status) { Say-Idle "noanswer" "docker did not answer; watchdog idle"; return }
    if (-not $stop) { Say-Idle "down" "container not running ($status); watchdog idle"; return }
    $facts = Get-ContainerFacts
    if (-not $facts) { Say-Idle "noanswer" "docker did not answer; watchdog idle"; return }
    if ($facts.id -ne $stop.id -or $facts.started -ne $stop.started) {
        # Recreated or started again since this script stopped it, so that stop is over.
        $script:wdState.stop = $null
        Write-WatchdogState
        Say-Idle "down" "container not running ($status); watchdog idle"
        return
    }
    $blocker = Resume-Blocker $stop
    if ($blocker) {
        Say-Idle "wait:$($blocker.Split(',')[0])" "container stopped by the watchdog ($($stop.reason), $($stop.ts)); $blocker"
        return
    }
    Resume-Run $stop
    $script:idleKey = ""
}

# One file per container, so a -Once pass against a test container cannot overwrite the record
# of the run.
if (-not $StateFile) {
    $stateName = if ($Container -eq "rk") { "watchdog-state.json" } else { "watchdog-state-$Container.json" }
    $StateFile = Join-Path (Split-Path $HarnessRoot -Parent) $stateName
}
$script:wdState = Read-WatchdogState

$cap = Read-Cap
$highSince = $null
$lowSince = $null
$cpuSamples = New-Object System.Collections.ArrayList
$alerted = $false
# A peer list is a name list, and a wrong name silently subtracts nothing. The banner names
# the requested set and the first successful poll names the resolved one.
$peerList = @($PeerContainers -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$peersReported = $false
$statsFailing = $false
$lastSysWarn = [datetime]::MinValue
if (-not $CpuSampleFile) { $CpuSampleFile = Join-Path (Split-Path $HarnessRoot -Parent) "docker-cpu.json" }
$sysPolicy = if ($MinFreeSystemGB -gt 0) { "guard at ${MinFreeSystemGB}GB" } else { "report only" }
Rotate-Log
Say "watchdog: container=$Container work=$Work cap=$cap USD poll=${PollSeconds}s heartbeat-stale=${HeartbeatStaleSeconds}s min-free=${MinFreeGB}GB push=${PushMinutes}min cpu-pause spike ${CpuHigh}/${CpuLow}% for ${CpuSustainSeconds}s, avg ${CpuHighAvg}/${CpuLowAvg}% over ${CpuAvgWindowSeconds}s battery-guard=$(-not $NoBatteryGuard)"
Say "watchdog: peers=[$($peerList -join ', ')] docker-stats-timeout=${StatsTimeoutMs}ms system-drive=$sysPolicy cpu-sample=$CpuSampleFile"
$resumePolicy = if ($NoAutoResume) { "off" } else { "at most $ResumeMax per ${ResumeWindowHours}h, disk margin ${ResumeMarginGB}GB, cooldown ${ResumeCooldownSeconds}s" }
Say "watchdog: auto-resume $resumePolicy state=$StateFile$(if ($script:wdState.stop) { " (holds a $($script:wdState.stop.reason) stop from $($script:wdState.stop.ts))" })"

while ($true) {
    if (-not $Once) { Start-Sleep -Seconds $PollSeconds }
    if (((Get-Date) - $script:LastRotate).TotalMinutes -ge 10) { Rotate-Log }
    # 0. Host-side push of completed commits every $PushMinutes (or on every -Once pass).
    if ($Once -or ((Get-Date) - $lastPush).TotalMinutes -ge $PushMinutes) {
        Push-Repo $Work
        Push-Repo $Findings
        $lastPush = Get-Date
    }

    # 0c. Epoch saturation: ask rk_harness.saturation every $SaturationCheckSeconds whether
    # the epoch has stopped producing; on the freeze threshold, drop STOP for a graceful
    # stop, then mark the epoch frozen and push once the container has exited.
    if (-not $NoSaturation -and $SaturationCheckSeconds -gt 0 -and ((Get-Date) - $lastSatCheck).TotalSeconds -ge $SaturationCheckSeconds -and (Test-Path $VenvPython)) {
        $lastSatCheck = Get-Date
        $env:RK_WORK_DIR = $Work
        $env:PYTHONPATH = $HarnessRoot
        $satRaw = & $VenvPython -m rk_harness.saturation --check 2>$null
        $sat = $null
        try { $sat = $satRaw | ConvertFrom-Json } catch {}
        if ($sat -and $sat.action -eq "freeze" -and $AutoFreeze) {
            Say "SATURATION freeze threshold met ($($sat.consecutive)/$($sat.consecutive_needed) checks, last progress $($sat.hours_since_progress)h ago); dropping STOP for a graceful epoch freeze"
            Set-Content -Path (Join-Path $Work "STOP") -Value "stop" -Encoding ascii
            $freezePending = $true
        } elseif ($sat -and $sat.action -eq "freeze") {
            Say "saturation ADVISORY: freeze threshold met ($($sat.consecutive) checks) but auto-freeze is off (owner ruling 2026-09-03); run continues"
        } elseif ($sat -and $sat.verdict -ne "FROZEN") {
            Say "saturation: $($sat.verdict) (progress $($sat.hours_since_progress)h ago, checks $($sat.consecutive)/$($sat.consecutive_needed))"
        }
    }
    if ($freezePending) {
        $stF = docker inspect -f "{{.State.Status}}" $Container 2>$null
        if ($stF -ne "running" -and $stF -ne "paused") {
            $env:RK_WORK_DIR = $Work
            $env:PYTHONPATH = $HarnessRoot
            & $VenvPython -m rk_harness.saturation --mark-frozen "no archive progress past the window and falsification concluded" | Out-Null
            Push-Repo $Work
            Push-Repo $Findings
            Say "EPOCH 1 FROZEN: run stopped cleanly, EPOCH_STATUS.json written and pushed"
            $freezePending = $false
        }
    }

    # Pause state is derived from docker every poll, never trusted from this process's own
    # variables: start.ps1 restarts the watchdog, and a fresh instance must adopt a paused
    # container instead of killing it or leaving it frozen.
    $status = (docker inspect -f "{{.State.Status}}" $Container 2>$null)
    if ($status -ne "running" -and $status -ne "paused") { Handle-Down $status; if ($Once) { break }; continue }
    $script:idleKey = ""
    if ($script:wdState.stop) {
        # Up again, whoever started it, so the recorded stop is over.
        $script:wdState.stop = $null
        Write-WatchdogState
    }
    $isPaused = ($status -eq "paused")
    if ($isPaused) { $resumedAt = $null }

    # 0b. Battery: pause while unplugged, resume on AC. Takes precedence over the CPU pause logic.
    if (-not $NoBatteryGuard) {
        if (On-Battery) {
            if (-not $isPaused) {
                Say "on battery -> docker pause"
                docker pause $Container | Out-Null
            }
            $pausedBattery = $true
            if ($Once) { break }; continue
        } elseif ($pausedBattery) {
            Say "back on AC -> docker unpause"
            if ($isPaused) { docker unpause $Container | Out-Null; $isPaused = $false; $resumedAt = Get-Date }
            $pausedBattery = $false
        }
    }

    # 1. Killfile: graceful stop at the cycle boundary (the runner polls STOP itself).
    if (Test-Path (Join-Path $Work "STOP")) {
        Say "STOP present; runner will stop at cycle boundary"
    }

    # 2. Heartbeat stale > 120 s -> docker kill.
    $hb = Join-Path $Work "HEARTBEAT"
    if (Test-Path $hb) {
        try {
            $ts = [datetime]::Parse((Get-Content $hb -Raw).Trim()).ToUniversalTime()
            $age = ((Get-Date).ToUniversalTime() - $ts).TotalSeconds
            # Startup grace: never kill a container younger than the staleness threshold - the
            # entrypoint gate runs before the runner's heartbeat thread exists.
            # Resume grace, for the same reason: a paused container's process is frozen, so the
            # heartbeat necessarily ages by the whole pause and the runner needs a poll interval
            # after thawing to write a fresh one. Without this the guard pauses the container and
            # then kills it for the silence it just caused.
            $resumeGrace = ($null -ne $resumedAt -and ((Get-Date) - $resumedAt).TotalSeconds -le $HeartbeatStaleSeconds)
            if ($age -gt $HeartbeatStaleSeconds -and -not $isPaused -and -not $resumeGrace -and (Container-UptimeSeconds) -gt $HeartbeatStaleSeconds) {
                Stop-Run "heartbeat" "kill" "heartbeat stale ${age}s"
                if ($Once) { break }; continue
            }
        } catch { Say "heartbeat unreadable" }
    }

    # 3. No verified candidate in 30 min -> log alert (escalation is the encourager's job).
    $ageMin = Get-LastVerifiedAge
    if ($null -ne $ageMin -and $ageMin -gt $NoCandidateMinutes) {
        if (-not $alerted) { Say "ALERT: no verified candidate for $([int]$ageMin) min"; $alerted = $true }
    } else { $alerted = $false }

    # 4. Spend over cap -> hard stop.
    $spend = Get-Spend
    if ($spend -gt $cap) {
        Stop-Run "spend" "stop" "spend $spend USD > cap $cap"
        if ($Once) { break }; continue
    }

    # 5. Disk free on the work volume < 5 GB -> hard stop.
    $drive = (Get-Item $Work).PSDrive
    $freeGB = [double]$drive.Free / 1GB
    if ($freeGB -lt $MinFreeGB) {
        Stop-Run "disk" "stop" "disk free ${freeGB} GB < $MinFreeGB"
        if ($Once) { break }; continue
    }

    # 5b. The system drive, which block 5 does not watch. Docker's VHDX lives there, so it
    # fills for reasons that have nothing to do with the run and takes the daemon with it.
    # Default 0 is report only: whether a low system drive should stop the research run is
    # the owner's call, and watchdog.min_free_system_gb makes it a value rather than an edit.
    $sysFree = $null
    try { $sysFree = [double]((Get-PSDrive -Name $env:SystemDrive.TrimEnd(':') -ErrorAction Stop).Free) / 1GB } catch { $sysFree = $null }
    if ($null -ne $sysFree) {
        $sysTxt = [math]::Round($sysFree, 1)
        if ($MinFreeSystemGB -gt 0 -and $sysFree -lt $MinFreeSystemGB) {
            Stop-Run "system" "stop" "system drive $env:SystemDrive free ${sysTxt} GB < $MinFreeSystemGB"
            if ($Once) { break }; continue
        } elseif ($MinFreeSystemGB -le 0 -and $sysFree -lt 5.0 -and ((Get-Date) - $lastSysWarn).TotalMinutes -ge 30) {
            Say "system drive $env:SystemDrive free ${sysTxt} GB and unguarded; set watchdog.min_free_system_gb to stop the run on it"
            $lastSysWarn = Get-Date
        }
    }

    # Pause watchdog (section 13.5, owner-tuned 2026-09-03). Two triggers each way:
    # pause on a spike (> $CpuHigh for $CpuSustainSeconds) OR a hot average (> $CpuHighAvg
    # over $CpuAvgWindowSeconds); resume on a quiet spike (< $CpuLow for $CpuSustainSeconds)
    # OR a quiet average (< $CpuLowAvg over the window). The sample buffer clears after any
    # action so the spike and average rules cannot flap against each other.
    $total = [double](Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples[0].CookedValue
    if ($isPaused) {
        # A paused container's cgroup is frozen, so its CPU share is zero and there is
        # nothing to subtract. Skipping the probe here is not only cheaper: it is what keeps
        # a wedged daemon from stranding a paused run, because the rule below decides
        # nothing when the probe fails and the resume would otherwise never be computed.
        $host_cpu = $total
    } else {
        $rows = Get-DockerCpuRows $StatsTimeoutMs
        if ($null -eq $rows) {
            # One line per outage, not one per poll: killing docker.exe leaves its request
            # in flight, so the next poll may well find the daemon busy again.
            if (-not $statsFailing) {
                Say "docker stats did not answer within ${StatsTimeoutMs}ms; pause guard idle until it does"
                $statsFailing = $true
            }
            # Decide nothing on a failed probe. Clearing the buffer is the same reset the
            # loop already does after a pause or an unpause, so the spike rule and the
            # average rule cannot flap against each other across the outage.
            $cpuSamples.Clear(); $highSince = $null; $lowSince = $null
            if ($Once) { break }
            continue
        }
        if ($statsFailing) { Say "docker stats is answering again; pause guard active"; $statsFailing = $false }
        if (-not $peersReported) {
            $seen = @(); $missing = @()
            foreach ($n in $peerList) {
                if ($rows.ContainsKey($n)) { $seen += "${n} $([math]::Round($rows[$n], 1))%" } else { $missing += $n }
            }
            $peerMsg = "peers subtracted from host load: " + $(if ($seen.Count) { $seen -join ", " } else { "none" })
            if ($missing.Count) { $peerMsg += "; requested but not running: " + ($missing -join ", ") }
            Say $peerMsg
            $peersReported = $true
        }
        # Only the named peers are subtracted. Every other container counts as foreground
        # load the run should yield to, which is why the default is rk alone: a crash-looping
        # third-party stack must not be able to run this machine hot while the guard reports
        # it quiet.
        $peerSum = 0.0
        foreach ($n in $peerList) { if ($rows.ContainsKey($n)) { $peerSum += [double]$rows[$n] } }
        $host_cpu = [math]::Max(0.0, $total - $peerSum)
        Write-CpuSample $rows
    }
    $now = Get-Date
    [void]$cpuSamples.Add(@{ t = $now; v = $host_cpu })
    while ($cpuSamples.Count -gt 0 -and ($now - $cpuSamples[0].t).TotalSeconds -gt $CpuAvgWindowSeconds) { $cpuSamples.RemoveAt(0) }
    $avgReady = ($cpuSamples.Count -ge 2 -and ($now - $cpuSamples[0].t).TotalSeconds -ge (0.8 * $CpuAvgWindowSeconds))
    $cpuAvg = ($cpuSamples | ForEach-Object { $_.v } | Measure-Object -Average).Average
    $avgTxt = [math]::Round($cpuAvg, 1)
    $winMin = [int]($CpuAvgWindowSeconds / 60)

    if ($host_cpu -gt $CpuHigh) { if ($null -eq $highSince) { $highSince = $now }; $lowSince = $null }
    elseif ($host_cpu -lt $CpuLow) { if ($null -eq $lowSince) { $lowSince = $now }; $highSince = $null }
    else { $highSince = $null; $lowSince = $null }

    $spikePause = ($null -ne $highSince -and ($now - $highSince).TotalSeconds -ge $CpuSustainSeconds)
    $avgPause = ($avgReady -and $cpuAvg -gt $CpuHighAvg)
    $spikeResume = ($null -ne $lowSince -and ($now - $lowSince).TotalSeconds -ge $CpuSustainSeconds)
    $avgResume = ($avgReady -and $cpuAvg -lt $CpuLowAvg)

    if (-not $isPaused -and ($spikePause -or $avgPause)) {
        $why = if ($spikePause) { "host CPU ${host_cpu}% > ${CpuHigh}% for ${CpuSustainSeconds}s" } else { "host CPU avg ${avgTxt}% > ${CpuHighAvg}% over ${winMin} min" }
        Say "$why -> docker pause"
        docker pause $Container | Out-Null
        $highSince = $null; $lowSince = $null; $cpuSamples.Clear()
    } elseif ($isPaused -and ($spikeResume -or $avgResume)) {
        $why = if ($spikeResume) { "host CPU ${host_cpu}% < ${CpuLow}% for ${CpuSustainSeconds}s" } else { "host CPU avg ${avgTxt}% < ${CpuLowAvg}% over ${winMin} min" }
        Say "$why -> docker unpause"
        docker unpause $Container | Out-Null
        $resumedAt = Get-Date
        $highSince = $null; $lowSince = $null; $cpuSamples.Clear()
    }
    if ($Once) { break }
}
