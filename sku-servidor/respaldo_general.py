"""Copia SQLite consistente en línea, con configuración portable y manifiesto."""
import contextlib,datetime,hashlib,json,pathlib,sqlite3,tempfile,zipfile
from app_info import is_internal_admin,VERSION

def sha256(path):
 digest=hashlib.sha256()
 with path.open('rb') as source:
  for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
 return digest.hexdigest()

@contextlib.contextmanager
def create(store,actor):
 if not is_internal_admin(actor):raise PermissionError('Solo Sistemas puede descargar el respaldo general de la instalación.')
 with tempfile.TemporaryDirectory(prefix='jm-respaldo-general-') as folder:
  root=pathlib.Path(folder);data=root/'data';data.mkdir();snapshot=data/'sku.sqlite3'
  # No se copia directamente el archivo vivo ni sus archivos WAL/SHM.
  with contextlib.closing(sqlite3.connect(store.path,timeout=30)) as source,contextlib.closing(sqlite3.connect(snapshot)) as target:
   source.backup(target,pages=256,sleep=.01)
   for table in ('sessions','login_attempts'):
    if target.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():target.execute('DELETE FROM '+table)
   target.commit()
   if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('No se pudo validar la integridad del respaldo general.')
  config={'host':'0.0.0.0','port':8098,'data_dir':'data','require_activation':getattr(store,'require_activation',False),'require_module_contract':getattr(store,'enforce_contract',False)}
  (root/'config.json').write_text(json.dumps(config,indent=2),encoding='utf8')
  verifier=store.directory/'activation-verifier.json'
  if verifier.is_file():(data/verifier.name).write_bytes(verifier.read_bytes())
  (root/'LEEME_RESTAURACION.txt').write_text('''ERP JM Lite - Respaldo general
Incluye la base completa: empresas, logos, impuestos, unidades, SKU, compras,
inventarios, ventas, TPV, CRM, comisiones, CXP/CXC, Calidad y sus archivos,
usuarios, hashes de contrasenas, 2FA, permisos y configuracion de la aplicacion.
No contiene sesiones activas. Se debera iniciar sesion despues de recuperar.

Recuperacion por Sistemas (no importar este ZIP como un respaldo de modulo):
1. Verifica los hashes de manifest.json antes de usar los archivos.
2. Deten ERP-JM-Lite o el proceso servidor. Conserva una copia de la carpeta
   de datos actual completa antes de reemplazar cualquier archivo.
3. Con el servidor detenido, retira la carpeta de datos anterior conservandola
   como copia; crea una carpeta de datos nueva y copia alli el contenido de data.
   No mezcles archivos -wal o -shm anteriores con la base recuperada.
4. Conserva la configuracion del servidor y su ruta de datos. config.json es
   una referencia portable para un arranque nuevo, con puerto 8098.
5. Usa la misma version del programa o una compatible, inicia el servidor,
   entra con una cuenta recuperada y comprueba los modulos antes de operar.

El EXE, runtime C++, registros y respaldos anteriores se distribuyen aparte.
Los catalogos oficiales SAT forman parte del programa. Los archivos maestros
e imagenes operativos estan dentro de SQLite; rutas externas de sincronizacion
pueden necesitar configurarse nuevamente en otra computadora.
Este ZIP contiene informacion de toda la instalacion y datos de acceso;
conservalo en un lugar seguro.
''',encoding='utf8')
  files={p.relative_to(root).as_posix():sha256(p) for p in root.rglob('*') if p.is_file()}
  stamp=datetime.datetime.now(datetime.timezone.utc)
  manifest={'formato':'JM-RESPALDO-GENERAL','version':1,'versionAplicacion':VERSION,'creadoUTC':stamp.isoformat(),'archivos':files,'sesionesIncluidas':False}
  (root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
  archive=root/'respaldo.zip'
  with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
   for name in [*files,'manifest.json']:output.write(root/name,name)
  yield archive,'ERP_JM_Respaldo_General_'+stamp.strftime('%Y%m%d_%H%M%S')+'.zip'
