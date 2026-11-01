"""Construir paquete Windows x64 moderno sin datos ni credenciales incorporadas."""
import argparse,hashlib,json,pathlib,runpy,secrets,shutil,subprocess,sys,tempfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parent.parent
GUIDE='''ERP JM Lite 0.1.0-dev - paquete piloto Windows x64

Compatible objetivo: Windows 10/11 y Server 2016/2019/2022/2025 x64.
Server 2012 R2 requiere una compilacion Legacy independiente; no esta certificada.
No se ha certificado todavia este paquete en toda la matriz Windows.

1. Extrae TODO el ZIP en una carpeta temporal local.
2. Abre PowerShell como administrador en esa carpeta y ejecuta:
   powershell -NoProfile -ExecutionPolicy Bypass -File .\\install_windows.ps1 -OpenFirewall
3. El puerto web es 8098. Define la clave de
   mario.gonzalez@jad-ayt.com en la consola (entrada oculta).
4. Abre http://NOMBRE-O-IP-DEL-SERVIDOR:PUERTO desde un navegador moderno.

El paquete incluye la aplicacion, Python/SQLite y sus dependencias nativas
integrados en el EXE y Microsoft Visual C++ x64 firmado por Microsoft.
No necesitas instalar Python, Node, Office ni SQLite en los equipos cliente.
Se instala el programa en Program Files y los datos en ProgramData\\ERP JM Lite.
La tarea ERP-JM-Lite arranca el servidor al encender Windows.
El servidor escucha en todas las interfaces IPv4, incluidas las VPN.
El firewall opcional permite TCP 8098 para este EXE en todos los perfiles,
incluidas redes ZeroTier, Radmin y Hamachi. La VPN debe permitir la conexion.
Si 8098 esta ocupado, se informa el problema y no se cambia de puerto.

ACTUALIZAR: detener la tarea, respaldar ProgramData\\ERP JM Lite y volver a
instalar conservando esa carpeta. Nunca se restablece la clave existente.
DESINSTALAR: detener y eliminar la tarea ERP-JM-Lite y la regla de firewall
ERP-JM-Lite-Web; retirar el programa. Conservar los datos y respaldos.
No desinstalar los componentes C++ que pueden compartir otras aplicaciones.

Paquete piloto, sin firma comercial propia. HTTPS, licenciamiento, configuracion
por empresa y carga de 40-50 usuarios siguen pendientes de validacion.
'''

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output-dir',type=pathlib.Path,default=ROOT/'dist-public')
 parser.add_argument('--vc-redist',type=pathlib.Path,required=True,help='Redistribuible x64 oficial de Microsoft para Windows moderno')
 args=parser.parse_args()
 if sys.platform!='win32' or sys.maxsize<=2**32:parser.error('Construye con Python Windows x64.')
 if not args.vc_redist.is_file():parser.error('Falta el redistribuible C++ oficial.')
 target=args.output_dir.resolve();target.mkdir(parents=True,exist_ok=True)
 subprocess.run(['node','sku/build-server.mjs'],cwd=ROOT,check=True)
 with tempfile.TemporaryDirectory(prefix='jm-public-') as folder:
  clean=pathlib.Path(folder);server=clean/'sku-servidor';server.mkdir();(clean/'sku').mkdir()
  for path in (ROOT/'sku-servidor').glob('*.py'):shutil.copy2(path,server/path.name)
  shutil.copy2(ROOT/'sku-servidor/catalogos.json',server/'catalogos.json')
  shutil.copytree(ROOT/'sku-servidor/public',server/'public',ignore=shutil.ignore_patterns('logo.png'))
  shutil.copy2(ROOT/'sku/ERP_JM_Lite.spec',clean/'sku/ERP_JM_Lite.spec')
  initializer=runpy.run_path(str(ROOT/'tools/inicializar.py'))
  initializer['create_initials'](server,secrets.token_urlsafe(32));(server/'initial-admin.json').unlink()
  subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','sku/ERP_JM_Lite.spec','--distpath',str(target),'--workpath',str(clean/'build')],cwd=clean,check=True)
 shutil.copy2(args.vc_redist,target/'VC_redist.x64.exe')
 
 for script in ('install_windows.ps1','verify_windows.ps1'):shutil.copy2(ROOT/'tools'/script,target/script)
 (target/'LEEME.txt').write_text(GUIDE,encoding='utf8')
 names=('ERP_JM_Lite.exe','VC_redist.x64.exe','install_windows.ps1','verify_windows.ps1','LEEME.txt')
 manifest={'product':'ERP JM Lite','version':'0.1.0-dev','profile':'windows-modern-x64','certified':False,'python':sys.version.split()[0],'files':{name:hashlib.sha256((target/name).read_bytes()).hexdigest() for name in names}}
 (target/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
 archive_path=target.parent/'ERP_JM_Lite_Windows_Piloto.zip'
 with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED) as archive:
  for name in (*names,'manifest.json'):archive.write(target/name,name)
 print('Paquete piloto sin datos ni credenciales:',archive_path)
if __name__=='__main__':main()
