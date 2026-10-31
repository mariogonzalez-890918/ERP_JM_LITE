param([string]$DataRoot=(Join-Path $env:ProgramData 'ERP JM Lite'),[switch]$BeforeReboot)
$ErrorActionPreference='Stop'
$config=Get-Content -Raw -LiteralPath (Join-Path $DataRoot 'config.json') | ConvertFrom-Json
$task=Get-ScheduledTask -TaskName 'ERP-JM-Lite'
$info=Get-ScheduledTaskInfo -TaskName 'ERP-JM-Lite'
$boot=(Get-CimInstance Win32_OperatingSystem).LastBootUpTime
$response=Invoke-WebRequest -Uri "http://127.0.0.1:$($config.port)/" -UseBasicParsing -TimeoutSec 20
$result=[ordered]@{os=(Get-CimInstance Win32_OperatingSystem).Caption;boot=$boot.ToString('o');taskState=[string]$task.State;taskRun=$info.LastRunTime.ToString('o');systemAccount=$task.Principal.UserId;startupTrigger=(@($task.Triggers | Where-Object {$_.CimClass.CimClassName -eq 'MSFT_TaskBootTrigger'}).Count -gt 0);httpStatus=$response.StatusCode;port=$config.port;databasePresent=(Test-Path -LiteralPath (Join-Path $DataRoot 'data\sku.sqlite3'))}
if($task.State -ne 'Running' -or -not $result.startupTrigger -or $response.StatusCode -ne 200 -or -not $result.databasePresent) { throw 'La instalacion no supera la verificacion de arranque y acceso web.' }
$baseline=Join-Path $DataRoot 'before-reboot.json'
if($BeforeReboot) { $result | ConvertTo-Json | Set-Content -LiteralPath $baseline -Encoding UTF8 }
elseif(Test-Path -LiteralPath $baseline) {
    $before=Get-Content -Raw -LiteralPath $baseline | ConvertFrom-Json
    if($boot -le [datetime]$before.boot -or $info.LastRunTime -lt $boot) { throw 'No se ha demostrado un nuevo arranque de Windows y de la aplicacion.' }
    $result['rebootVerified']=$true
}
$result | ConvertTo-Json
