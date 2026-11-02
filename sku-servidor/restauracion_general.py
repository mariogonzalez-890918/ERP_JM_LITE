"""Revisión de ZIP íntegro y recuperación completa con copia previa y exclusión."""
import contextlib,hashlib,hmac,json,pathlib,re,secrets,shutil,sqlite3,tempfile,time,zipfile
from app_info import ADMIN_EMAIL,VERSION,is_internal_admin
from respaldo_general import create,sha256
from requisiciones import Conflict

MAX_ZIP=128*1024*1024
MAX_EXPANDED=1024*1024*1024
ALLOWED={'data/sku.sqlite3','config.json','LEEME_RESTAURACION.txt','data/activation-verifier.json'}

class GeneralRestore:
 def __init__(self,store,enterprise,refresh,sync):
  self.store=store;self.enterprise=enterprise;self.refresh=refresh;self.sync=sync
  self.folder=store.directory/'restauracion-general';self.folder.mkdir(exist_ok=True)
  self.previous_folder=store.directory/'respaldos-generales-previos';self.previous_folder.mkdir(exist_ok=True)
 def owner(self,actor):
  if not is_internal_admin(actor):raise PermissionError('Solo Sistemas puede restaurar o descargar copias generales previas.')
 def schema(self,db):
  return db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
 def upgrade_warehouse_schema(self,path,incoming,current):
  from almacenes_config import LEGACY_SCHEMA,migrate
  # Única diferencia admitida: la definición exacta anterior del almacén.
  # Se adapta sólo la copia temporal, después de verificar el hash del ZIP.
  old=self.schema(incoming);new=self.schema(current)
  if [r for r in old if r[1]!='inv_warehouses']!=[r for r in new if r[1]!='inv_warehouses']:return
  if next((r[3] for r in old if r[1]=='inv_warehouses'),None)!=LEGACY_SCHEMA:return
  with contextlib.closing(sqlite3.connect(path)) as staged:migrate(staged)
 def summary(self,db):
  tables={'Empresas':'cm_companies','Sucursales':'app_branches','SKU de compra':'req_materials','Pedidos de compra':'po_orders','Documentos comerciales':'cm_documents','Movimientos de almacén':'inv_ledger','Registros de Calidad':'q_items','Archivos de Calidad':'q_files','Usuarios':'users'}
  return {label:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for label,table in tables.items()}
 @contextlib.contextmanager
 def validate(self,path):
  try:
   with zipfile.ZipFile(path) as archive,tempfile.TemporaryDirectory(prefix='jm-restaurar-') as folder:
    entries=archive.infolist();names=[x.filename for x in entries]
    if len(names)!=len(set(names)) or not {'manifest.json','data/sku.sqlite3','config.json','LEEME_RESTAURACION.txt'}<=set(names) or set(names)-ALLOWED-{'manifest.json'}:raise ValueError('ZIP general inválido: archivos duplicados, ajenos o faltantes.')
    if any(x.flag_bits&1 or x.file_size<0 or x.file_size>MAX_EXPANDED or (x.external_attr>>16)&0o170000==0o120000 for x in entries) or sum(x.file_size for x in entries)>MAX_EXPANDED:raise ValueError('El contenido del ZIP supera el límite de 1 GB o contiene archivos no permitidos.')
    if archive.getinfo('manifest.json').file_size>65536 or any(x.filename!='data/sku.sqlite3' and x.file_size>1024*1024 for x in entries):raise ValueError('Manifiesto o configuración demasiado grande.')
    manifest=json.loads(archive.read('manifest.json'))
    if not isinstance(manifest,dict) or manifest.get('formato')!='JM-RESPALDO-GENERAL' or manifest.get('version')!=1 or manifest.get('versionAplicacion')!=VERSION:raise ValueError('Usa un respaldo general de esta versión del ERP.')
    files=manifest.get('archivos')
    if not isinstance(files,dict) or set(files)!=set(names)-{'manifest.json'} or any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v) for v in files.values()):raise ValueError('Manifiesto de integridad inválido.')
    root=pathlib.Path(folder)
    for name,digest in files.items():
     # Nombres cerrados: nunca se extraen rutas suministradas por el usuario.
     target=root/('database.sqlite3' if name=='data/sku.sqlite3' else pathlib.PurePosixPath(name).name)
     with archive.open(name) as source,target.open('wb') as output:shutil.copyfileobj(source,output,1024*1024)
     if sha256(target)!=digest:raise ValueError('El respaldo está incompleto o modificado: '+name+'.')
    config=json.loads((root/'config.json').read_text(encoding='utf8'))
    if not isinstance(config,dict):raise ValueError('Configuración del respaldo inválida.')
    verifier=root/'activation-verifier.json'
    if verifier.exists():
     value=json.loads(verifier.read_text(encoding='utf-8-sig'))
     if not isinstance(value,dict) or not re.fullmatch('[0-9a-f]{32}',str(value.get('salt',''))) or not re.fullmatch('[0-9a-f]{64}',str(value.get('token_hash',''))):raise ValueError('Verificador de activación inválido.')
    target=root/'database.sqlite3'
    with contextlib.closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True)) as incoming,self.store.connect() as current:
     if incoming.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('La base del respaldo no supera la revisión de integridad.')
     if self.schema(incoming)!=self.schema(current):self.upgrade_warehouse_schema(target,incoming,current)
     if self.schema(incoming)!=self.schema(current):raise ValueError('La estructura del respaldo no coincide con esta instalación. Usa la misma versión del programa.')
     row=incoming.execute('SELECT role,active,salt,password_hash FROM users WHERE email=?',(ADMIN_EMAIL,)).fetchone()
     if not row or row[:2]!=('superadmin',1) or not re.fullmatch('[0-9a-f]{32}',str(row[2])) or not re.fullmatch('[0-9a-f]{64}',str(row[3])) or not incoming.execute('SELECT 1 FROM app_internal_admins WHERE email=?',(ADMIN_EMAIL,)).fetchone():raise ValueError('El respaldo no contiene la cuenta interna de recuperación válida.')
     summary=self.summary(incoming)
    yield root,manifest,summary
  except (zipfile.BadZipFile,UnicodeError,json.JSONDecodeError,sqlite3.DatabaseError) as error:raise ValueError('No se pudo validar el ZIP de respaldo general.') from error
 def upload(self,stream,length,actor):
  self.owner(actor)
  if not 0<length<=MAX_ZIP:raise ValueError('El respaldo general debe ser un ZIP de hasta 128 MB.')
  # Eliminar revisiones vencidas, sólo archivos planos de este directorio.
  for path in self.folder.iterdir():
   if re.fullmatch(r'[0-9a-f]{32}\.(zip|json)',path.name) and path.is_file() and time.time()-path.stat().st_mtime>3600:path.unlink(missing_ok=True)
  id=secrets.token_hex(16);path=self.folder/(id+'.zip')
  try:
   with path.open('xb') as output:
    left=length
    while left:
     block=stream.read(min(left,1024*1024))
     if not block:raise ValueError('La carga del ZIP quedó incompleta.')
     output.write(block);left-=len(block)
   with self.validate(path) as (_,manifest,summary):
    with self.store.connect() as db:
     db.execute('BEGIN');current=self.summary(db);fingerprint=self.enterprise.fingerprint(db)
    result={'id':id,'creadoUTC':manifest.get('creadoUTC',''),'version':manifest['versionAplicacion'],'actual':current,'respaldo':summary,'huellaActual':fingerprint}
    metadata={**result,'actor':actor['email'],'expires':time.time()+1800,'sha256':sha256(path)}
    (self.folder/(id+'.json')).write_text(json.dumps(metadata),encoding='utf8')
    return result
  except Exception:
   path.unlink(missing_ok=True);raise
 def copy_database(self,source,target):
  with contextlib.closing(sqlite3.connect(source,timeout=30)) as incoming,contextlib.closing(sqlite3.connect(target,timeout=30)) as destination:
   incoming.backup(destination,pages=256,sleep=.01)
   if destination.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Falló la comprobación de la base recuperada.')
 def restore_verifier(self,raw):
  target=self.store.directory/'activation-verifier.json'
  if raw is None:target.unlink(missing_ok=True)
  else:
   temporary=target.with_suffix('.nuevo');temporary.write_bytes(raw);temporary.replace(target)
 def confirm(self,data,actor):
  self.owner(actor)
  if data.get('texto')!='RESTAURAR TODO' or data.get('confirmar') is not True:raise ValueError('Confirma el reemplazo completo escribiendo RESTAURAR TODO.')
  id=data.get('id','')
  if not isinstance(id,str) or not re.fullmatch('[0-9a-f]{32}',id):raise ValueError('Revisa primero un respaldo general.')
  metadata=self.folder/(id+'.json');path=self.folder/(id+'.zip')
  if not metadata.is_file() or not path.is_file():raise Conflict('La revisión ya no está disponible. Vuelve a cargar el ZIP.')
  review=json.loads(metadata.read_text(encoding='utf8'))
  if review['actor']!=actor['email'] or review['expires']<time.time():raise Conflict('La revisión venció o pertenece a otra cuenta. Vuelve a revisar el respaldo.')
  # Es exclusivo también cuando se usa directamente desde pruebas o herramientas locales.
  with self.store.maintenance.exclusive() if self.store.maintenance.writer!=__import__('threading').get_ident() else contextlib.nullcontext():
   if self.sync.lock.locked():raise Conflict('Hay una sincronización en curso. Espera a que termine antes de restaurar.')
   with self.store.connect() as db:
    row=db.execute('SELECT salt,password_hash,role,active FROM users WHERE email=?',(actor['email'],)).fetchone()
    password=data.get('password')
    if not row or row[2:]!=('superadmin',1) or not isinstance(password,str) or len(password)>200 or not hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(row[0]),310000).hex(),row[1]):raise PermissionError('Contraseña actual de Sistemas incorrecta.')
    if self.enterprise.fingerprint(db)!=review['huellaActual']:raise Conflict('Hubo cambios desde la revisión. Vuelve a revisar el ZIP antes de restaurar.')
   if sha256(path)!=review['sha256']:raise ValueError('El archivo revisado cambió. Vuelve a cargar el respaldo.')
   with self.validate(path) as (root,manifest,summary),tempfile.TemporaryDirectory(prefix='jm-restaurar-rollback-') as folder:
    old=pathlib.Path(folder)/'before.sqlite3';self.copy_database(self.store.path,old)
    verifier=self.store.directory/'activation-verifier.json';old_verifier=verifier.read_bytes() if verifier.exists() else None
    previous_id=secrets.token_hex(16);previous=self.previous_folder/(previous_id+'.zip')
    with create(self.store,actor) as (archive,_):shutil.copy2(archive,previous)
    try:
     self.copy_database(root/'database.sqlite3',self.store.path)
     self.restore_verifier((root/'activation-verifier.json').read_bytes() if (root/'activation-verifier.json').exists() else None)
     with self.store.connect() as db:
      db.execute('DELETE FROM sessions');db.execute('DELETE FROM login_attempts')
      # Las rutas de otra computadora no deben iniciar importaciones automáticas.
      revision,payload,state=db.execute('SELECT revision,payload,state FROM cm_source WHERE id=1').fetchone();source=json.loads(payload);source['habilitada']=False
      if isinstance(source.get('maestroInicial'),dict):source['maestroInicial']['aplicado']=True
      db.execute('UPDATE cm_source SET payload=?,state=? WHERE id=1',(json.dumps(source),json.dumps({'enProceso':False,'mensaje':'Revisa la fuente de sincronización después de restaurar.'})))
     self.refresh()
    except Exception:
     self.copy_database(old,self.store.path);self.restore_verifier(old_verifier);self.refresh();raise
   # Cerrar el ZIP antes de retirarlo: Windows no elimina archivos abiertos.
   metadata.unlink(missing_ok=True)
   try:path.unlink(missing_ok=True)
   except OSError:pass  # Una revisión sin metadatos no puede volver a confirmarse.
   return {'ok':True,'respaldoPrevio':previous_id,'mensaje':'Restauración general completada. Inicia sesión con las credenciales del respaldo. La sincronización automática queda desactivada hasta revisarla.'}
 def previous(self,id,actor):
  self.owner(actor)
  if not re.fullmatch('[0-9a-f]{32}',id):raise ValueError('Copia previa inválida.')
  path=self.previous_folder/(id+'.zip')
  if not path.is_file():raise ValueError('Copia previa no encontrada.')
  return path,'ERP_JM_General_Previo_'+id+'.zip'
