# Solo crea una VM nueva. No modifica discos fisicos ni maquinas existentes.
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$Iso,
 [Parameter(Mandatory=$true)][string]$Package,
 [Parameter(Mandatory=$true)][string]$AdminSeed,
 [string]$LabRoot=(Join-Path $env:LOCALAPPDATA 'ERP-JM-Lite-Lab'),
 [string]$VmName='ERP-JM-Lite-Win11-Lab',
 [int]$Port=8090
)
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Path $LabRoot -Force | Out-Null
Start-Transcript -Path (Join-Path $LabRoot 'lab-transcript.log') -Append | Out-Null
$vhdMounted=$false;$isoMounted=$false
try {
 Import-Module Hyper-V
 if(Get-VM -Name $VmName -ErrorAction SilentlyContinue) { throw "Ya existe $VmName. No se modificara." }
 foreach($path in @($Iso,$Package,$AdminSeed)) { if(-not(Test-Path -LiteralPath $path)) { throw "Falta $path" } }
 $vmFolder=Join-Path $LabRoot $VmName
 if(Test-Path -LiteralPath $vmFolder) { throw 'Ya existe la carpeta del laboratorio. No se sobrescribe.' }
 New-Item -ItemType Directory -Path $vmFolder | Out-Null
 $ownerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
 & icacls.exe $vmFolder /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' ("*"+$ownerSid+':(OI)(CI)F') | Out-Null
 if($LASTEXITCODE -ne 0) { throw 'No se pudo proteger el laboratorio.' }
 $image=Mount-DiskImage -ImagePath (Resolve-Path -LiteralPath $Iso).Path -PassThru
 $isoMounted=$true
 $isoVolume=$image | Get-Volume
 $imageFile=Join-Path ($isoVolume.DriveLetter+':\') 'sources\install.wim'
 if(-not(Test-Path -LiteralPath $imageFile)) { $imageFile=Join-Path ($isoVolume.DriveLetter+':\') 'sources\install.esd' }
 $windowsImages=Get-WindowsImage -ImagePath $imageFile
 $windowsImage=$windowsImages | Where-Object {$_.ImageName -match 'Enterprise' -and $_.ImageName -notmatch ' N '} | Select-Object -First 1
 if(-not $windowsImage) { throw 'La ISO no contiene la edicion Enterprise de evaluacion esperada.' }
 $vhdPath=Join-Path $vmFolder 'system.vhdx'
 New-VHD -Path $vhdPath -Dynamic -SizeBytes 80GB | Out-Null
 $vhd=Mount-VHD -Path $vhdPath -PassThru;$vhdMounted=$true
 $disk=$vhd | Get-Disk
 # Comprobar el disco virtual recien creado antes de particionar y formatear.
 if((Get-VHD -DiskNumber $disk.Number).Path -ne $vhdPath -or $disk.PartitionStyle -ne 'RAW') { throw 'El disco no coincide con el VHDX nuevo.' }
 Initialize-Disk -Number $disk.Number -PartitionStyle GPT | Out-Null
 $efi=New-Partition -DiskNumber $disk.Number -Size 260MB -GptType '{c12a7328-f81f-11d2-ba4b-00a0c93ec93b}' -AssignDriveLetter
 $efi | Format-Volume -FileSystem FAT32 -NewFileSystemLabel 'JM-EFI' -Confirm:$false | Out-Null
 New-Partition -DiskNumber $disk.Number -Size 16MB -GptType '{e3c9e316-0b5c-4db8-817d-f92df00215ae}' | Out-Null
 $osPartition=New-Partition -DiskNumber $disk.Number -UseMaximumSize -AssignDriveLetter
 $osPartition | Format-Volume -FileSystem NTFS -NewFileSystemLabel 'JM-Win11-Lab' -Confirm:$false | Out-Null
 $osRoot=$osPartition.DriveLetter+':\'
 & dism.exe /Apply-Image ("/ImageFile:"+$imageFile) ("/Index:"+$windowsImage.ImageIndex) ("/ApplyDir:"+$osRoot) /CheckIntegrity
 if($LASTEXITCODE -ne 0) { throw 'No se pudo aplicar Windows al disco virtual.' }
 & bcdboot.exe ($osRoot+'Windows') /s ($efi.DriveLetter+':') /f UEFI
 if($LASTEXITCODE -ne 0) { throw 'No se pudo preparar el arranque UEFI.' }
 $randomBytes=New-Object byte[] 24;[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($randomBytes)
 $password='JmLab!7'+([BitConverter]::ToString($randomBytes).Replace('-',''))
 $credential=New-Object pscredential('ERPTest',(ConvertTo-SecureString $password -AsPlainText -Force))
 $credential | Export-Clixml -LiteralPath (Join-Path $vmFolder 'credential.xml')
 $unattend=@"
<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
 <settings pass="specialize"><component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"><ComputerName>ERP-JM-LAB</ComputerName><TimeZone>Central Standard Time (Mexico)</TimeZone></component></settings>
 <settings pass="oobeSystem"><component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"><OOBE><HideEULAPage>true</HideEULAPage><HideOnlineAccountScreens>true</HideOnlineAccountScreens><HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE><ProtectYourPC>3</ProtectYourPC></OOBE><UserAccounts><LocalAccounts><LocalAccount wcm:action="add"><Password><Value>$password</Value><PlainText>true</PlainText></Password><Description>Laboratorio aislado ERP JM Lite</Description><DisplayName>ERP Test</DisplayName><Group>Administrators</Group><Name>ERPTest</Name></LocalAccount></LocalAccounts></UserAccounts></component></settings>
</unattend>
"@
 New-Item -ItemType Directory -Path ($osRoot+'Windows\Panther') -Force | Out-Null
 $unattend | Set-Content -LiteralPath ($osRoot+'Windows\Panther\unattend.xml') -Encoding UTF8
 $guestPackage=$osRoot+'ERP-JM-Lite-Package'
 Copy-Item -LiteralPath $Package -Destination $guestPackage -Recurse
 Copy-Item -LiteralPath $AdminSeed -Destination ($osRoot+'admin-seed.json')
 Dismount-VHD -Path $vhdPath;$vhdMounted=$false
 Dismount-DiskImage -ImagePath (Resolve-Path -LiteralPath $Iso).Path;$isoMounted=$false
 $switchName='ERP-JM-Lite-Lab-Internal'
 $switch=Get-VMSwitch -Name $switchName -ErrorAction SilentlyContinue
 if($switch -and $switch.SwitchType -ne 'Internal') { throw 'El switch existente no es interno.' }
 if(-not $switch) { New-VMSwitch -Name $switchName -SwitchType Internal | Out-Null }
 $hostNic=Get-NetAdapter | Where-Object {$_.Name -eq ('vEthernet ('+$switchName+')')}
 if(-not(Get-NetIPAddress -InterfaceIndex $hostNic.ifIndex -IPAddress '192.168.241.1' -ErrorAction SilentlyContinue)) { New-NetIPAddress -InterfaceIndex $hostNic.ifIndex -IPAddress '192.168.241.1' -PrefixLength 24 | Out-Null }
 New-VM -Name $VmName -Generation 2 -MemoryStartupBytes 4GB -VHDPath $vhdPath -Path $vmFolder -SwitchName $switchName | Out-Null
 Set-VMProcessor -VMName $VmName -Count 2
 Set-VMMemory -VMName $VmName -DynamicMemoryEnabled $true -MinimumBytes 2GB -MaximumBytes 6GB
 Set-VM -Name $VmName -AutomaticStartAction Nothing -AutomaticStopAction ShutDown
 Set-VMKeyProtector -VMName $VmName -NewLocalKeyProtector
 Enable-VMTPM -VMName $VmName
 Start-VM -Name $VmName
 function Wait-Guest {
  $deadline=(Get-Date).AddMinutes(25)
  while((Get-Date) -lt $deadline) {
   try { $guestSession=New-PSSession -VMName $VmName -Credential $credential -ErrorAction Stop;return $guestSession } catch { Start-Sleep -Seconds 15 }
  }
  throw 'Windows no habilito PowerShell Direct en el tiempo previsto. Revisa la consola de la VM.'
 }
 $session=Wait-Guest
 try {
  Invoke-Command -Session $session -ArgumentList $Port -ScriptBlock {
   param($webPort)
   $ErrorActionPreference='Stop'
   $nic=Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object -First 1
   New-NetIPAddress -InterfaceIndex $nic.ifIndex -IPAddress '192.168.241.2' -PrefixLength 24 | Out-Null
   Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private
   & powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\ERP-JM-Lite-Package\install_windows.ps1' -Port $webPort -AdminSeed 'C:\admin-seed.json' -OpenFirewall
   if($LASTEXITCODE -ne 0) { throw 'El instalador fallo dentro de Windows.' }
   Remove-Item -LiteralPath 'C:\admin-seed.json' -Force
   & powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\ERP-JM-Lite-Package\verify_windows.ps1' -BeforeReboot
   if($LASTEXITCODE -ne 0) { throw 'Fallo la verificacion previa al reinicio.' }
  } | Out-File -LiteralPath (Join-Path $vmFolder 'before-reboot.log') -Encoding UTF8
 } finally { Remove-PSSession $session }
 # Solo reinicia la VM creada en esta ejecucion; nunca el equipo anfitrion.
 Restart-VM -Name $VmName -Force -Confirm:$false
 Start-Sleep -Seconds 30
 $session=Wait-Guest
 try {
  Invoke-Command -Session $session -ScriptBlock {
   Start-Sleep -Seconds 30
   & powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\ERP-JM-Lite-Package\verify_windows.ps1'
   if($LASTEXITCODE -ne 0) { throw 'Fallo la verificacion posterior al reinicio.' }
  } | Out-File -LiteralPath (Join-Path $vmFolder 'after-reboot.log') -Encoding UTF8
 } finally { Remove-PSSession $session }
 $web=Invoke-WebRequest -Uri ("http://192.168.241.2:"+$Port+'/') -UseBasicParsing -TimeoutSec 30
 if($web.StatusCode -ne 200) { throw 'No responde el acceso web desde el anfitrion.' }
 'PASS: instalacion, reinicio real de VM, arranque automatico y acceso web desde el anfitrion.' | Set-Content -LiteralPath (Join-Path $vmFolder 'result.txt')
} catch { $_ | Out-String | Set-Content -LiteralPath (Join-Path $LabRoot 'lab-error.txt');throw }
finally {
 if($vhdMounted) { Dismount-VHD -Path $vhdPath }
 if($isoMounted) { Dismount-DiskImage -ImagePath (Resolve-Path -LiteralPath $Iso).Path }
 Stop-Transcript | Out-Null
}
