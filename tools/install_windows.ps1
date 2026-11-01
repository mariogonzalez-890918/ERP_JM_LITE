# Ejecutar desde la distribucion extraida, en PowerShell como administrador.
[CmdletBinding()]
param(
    [ValidateSet(8098)][int]$Port = 8098,
    [string]$InstallDir = (Join-Path $env:ProgramFiles 'ERP JM Lite'),
    [string]$DataRoot = (Join-Path $env:ProgramData 'ERP JM Lite'),
    [switch]$OpenFirewall,
    [string]$AdminSeed,
    [string]$ActivationVerifier
)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Ejecuta PowerShell como administrador.' }
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Esta distribucion requiere Windows x64.' }
if ([Environment]::OSVersion.Version -lt [Version]'10.0') { throw 'Este paquete requiere Windows 10 o Server 2016 en adelante. Server 2012 R2 necesita el paquete Legacy, aun pendiente de certificacion.' }
$source = Join-Path $PSScriptRoot 'ERP_JM_Lite.exe'
if (-not (Test-Path -LiteralPath $source)) { throw 'Falta ERP_JM_Lite.exe junto al instalador.' }
$manifest = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') | ConvertFrom-Json
foreach ($file in $manifest.files.PSObject.Properties) {
    $artifact = Join-Path $PSScriptRoot $file.Name
    if ((Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash -ne $file.Value) { throw "Archivo incompleto o modificado: $($file.Name)" }
}
$runtime = Join-Path $PSScriptRoot 'VC_redist.x64.exe'
$signature = Get-AuthenticodeSignature -LiteralPath $runtime
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') { throw 'El runtime C++ no tiene una firma valida de Microsoft.' }
$runtimeResult = Start-Process -FilePath $runtime -ArgumentList '/install','/quiet','/norestart' -WindowStyle Hidden -Wait -PassThru
if ($runtimeResult.ExitCode -notin @(0,1638,3010)) { throw "Error al instalar C++: $($runtimeResult.ExitCode)" }
New-Item -ItemType Directory -Path $InstallDir,$DataRoot -Force | Out-Null
# Solo SYSTEM y administradores pueden leer las bases y sus hashes de acceso.
& icacls.exe $DataRoot /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron proteger los datos.' }
$configPath = Join-Path $DataRoot 'config.json'
$config = @{host='0.0.0.0';port=8098;data_dir='data';log_dir='logs';require_activation=$true}
if (Test-Path -LiteralPath $configPath) {
    $existing = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
    foreach ($key in @('data_dir','log_dir')) { if ($null -ne $existing.$key) { $config[$key] = $existing.$key } }
}
$config.port=$Port
$taskName='ERP-JM-Lite'
$previous = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($previous) { Stop-ScheduledTask -TaskName $taskName; Start-Sleep -Seconds 2 }
$listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any,$Port)
try { $listener.Start() } catch { throw "El puerto $Port esta ocupado o no esta disponible. Libera el puerto y vuelve a instalar. No se utilizara otro puerto." } finally { $listener.Stop() }
$exe = Join-Path $InstallDir 'ERP_JM_Lite.exe'
Copy-Item -LiteralPath $source -Destination $exe -Force
$config | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
# El primer inicio pide la clave de Mario de forma oculta; nunca va en argumentos.
if ($AdminSeed) { & $exe --config $configPath --initialize --admin-seed $AdminSeed }
else { & $exe --config $configPath --initialize }
if ($LASTEXITCODE -ne 0) { throw 'No se pudo inicializar la base. No se registro el inicio automatico.' }
if ($ActivationVerifier) {
    $privateData = if ([IO.Path]::IsPathRooted($config.data_dir)) {$config.data_dir} else {Join-Path $DataRoot $config.data_dir}
    Copy-Item -LiteralPath $ActivationVerifier -Destination (Join-Path $privateData 'activation-verifier.json') -Force
}
$action = New-ScheduledTaskAction -Execute $exe -Argument ('--config "'+$configPath+'"') -WorkingDirectory $InstallDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
if ($OpenFirewall) {
    Get-NetFirewallRule -Name 'ERP-JM-Lite-Web' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -Name 'ERP-JM-Lite-Web' -DisplayName 'ERP JM Lite Web' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Program $exe -Profile Any -RemoteAddress Any | Out-Null
}
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 3
try { Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 15 | Out-Null } catch { throw 'La aplicacion no respondio. Revisa la tarea ERP-JM-Lite antes de dar la instalacion por terminada.' }
Write-Host "ERP JM Lite instalado: http://NOMBRE-O-IP-DEL-SERVIDOR:$Port"
Write-Host "Administrador: mario.gonzalez@jad-ayt.com. Datos y configuracion: $DataRoot"
if ($runtimeResult.ExitCode -eq 3010) { Write-Host 'Microsoft C++ solicita reiniciar Windows; no se reinicio automaticamente.' }
