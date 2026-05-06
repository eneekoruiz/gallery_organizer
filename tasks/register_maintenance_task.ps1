<#
Register a Windows Scheduled Task that runs the maintenance runner daily.

Usage examples:
  - To auto-detect Python: .\register_maintenance_task.ps1
  - To specify Python executable: .\register_maintenance_task.ps1 -PythonExe 'C:\Path\To\python.exe'

This creates a task named "SmartGallery_Maintenance" scheduled daily at 03:00.
#>

[CmdletBinding()]
param(
    [string] $PythonExe,
    [string] $TaskName = 'SmartGallery_Maintenance',
    [string] $ScheduleTime = '03:00'
)

function Get-PythonExe {
    param($candidate)
    if ($candidate -and (Test-Path $candidate)) { return $candidate }
    try {
        $cmd = Get-Command python -ErrorAction Stop
        return $cmd.Source
    } catch {
        Write-Error "No python executable found in PATH. Provide -PythonExe parameter."
        return $null
    }
}

$py = Get-PythonExe -candidate $PythonExe
if (-not $py) { exit 1 }

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $repo '..')
$scriptPath = Join-Path $repoRoot 'smart_gallery_v2\tools\maintenance_runner.py'

if (-not (Test-Path $scriptPath)) {
    Write-Error "maintenance_runner.py not found at $scriptPath"
    exit 2
}

$action = New-ScheduledTaskAction -Execute $py -Argument "`"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At $ScheduleTime
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest

try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force
    Write-Output "Scheduled task '$TaskName' created to run daily at $ScheduleTime (executes: $py $scriptPath)"
    exit 0
} catch {
    Write-Error "Failed to register scheduled task: $_"
    exit 3
}
