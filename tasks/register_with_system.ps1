<#
Register the maintenance task to run as SYSTEM (requires elevation).
Run this with administrator privileges.
#>

$action = New-ScheduledTaskAction -Execute "C:\Users\User\Desktop\PROYECTOS\smart_gallery_v2\tasks\run_maintenance.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At "03:00"
$principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest

try {
    Register-ScheduledTask -TaskName "SmartGallery_Maintenance" -Action $action -Trigger $trigger -Principal $principal -Force
    Write-Output "Scheduled task 'SmartGallery_Maintenance' created to run as SYSTEM daily at 03:00"
    exit 0
} catch {
    Write-Error "Failed to register scheduled task: $_"
    exit 1
}
