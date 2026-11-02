# Controles locales de la tarea de inicio automatico del ERP.
[CmdletBinding()]
param([ValidateSet('Start','Stop')][string]$Action = 'Stop')
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    try {
        Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -Verb RunAs -WindowStyle Hidden -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'),'-Action',$Action) | Out-Null
    } catch { exit 1 }
    exit 0
}
Add-Type -AssemblyName PresentationFramework
try {
    $task = Get-ScheduledTask -TaskName 'ERP-JM-Lite' -ErrorAction Stop
    if ($Action -eq 'Stop') {
        Stop-ScheduledTask -InputObject $task
        $deadline = (Get-Date).AddSeconds(20)
        do {
            $state = (Get-ScheduledTask -TaskName 'ERP-JM-Lite').State
            if ($state -ne 'Running') { break }
            Start-Sleep -Milliseconds 300
        } while ((Get-Date) -lt $deadline)
        if ($state -eq 'Running') { throw 'Windows aun reporta el servidor en ejecucion. Revisa la tarea ERP-JM-Lite.' }
        [System.Windows.MessageBox]::Show('ERP JM Lite detenido. Los datos se conservan. Para volver a entrar por web usa Iniciar servicio. Al reiniciar Windows arrancara automaticamente.','ERP JM Lite','OK','Information') | Out-Null
    } else {
        Start-ScheduledTask -InputObject $task
        $ready = $false
        $deadline = (Get-Date).AddSeconds(30)
        do {
            try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8098/' -UseBasicParsing -TimeoutSec 2; $ready = $response.StatusCode -eq 200 } catch { }
            if ($ready) { break }
            Start-Sleep -Milliseconds 500
        } while ((Get-Date) -lt $deadline)
        if (-not $ready) { throw 'El ERP no respondio en el puerto 8098. Revisa si el puerto esta ocupado y los registros en ProgramData\ERP JM Lite.' }
        [System.Windows.MessageBox]::Show('ERP JM Lite iniciado. Accede desde http://127.0.0.1:8098 o desde la IP del servidor con puerto 8098.','ERP JM Lite','OK','Information') | Out-Null
    }
} catch {
    [System.Windows.MessageBox]::Show($_.Exception.Message,'ERP JM Lite - No se pudo completar la accion','OK','Error') | Out-Null
    exit 1
}
