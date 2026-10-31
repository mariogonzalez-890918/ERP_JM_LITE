"""Empresa, activación privada y restablecimiento integral del producto comercial."""
import datetime,hashlib,hmac,json,pathlib,re,secrets,sqlite3
from app_info import ADMIN_EMAIL
from requisiciones import Conflict,now,text
from sucursales import BRANCHES,save_branch
PRESERVED={'users','sessions','role_modules','permission_features','app_branches','app_company','app_license','app_audit','app_meta','cm_companies','cm_sequences','cm_sequence_registry','req_branches','req_series_registry','req_areas','req_report_features','req_reports','sales_features','po_settings','inv_concepts'}

class Enterprise:
 def __init__(self,store):
  self.store=store
  with store.connect() as db:
   db.executescript('''CREATE TABLE IF NOT EXISTS app_company(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL,payload TEXT NOT NULL);
   INSERT OR IGNORE INTO app_company VALUES(1,1,'{}');
   CREATE TABLE IF NOT EXISTS app_license(id INTEGER PRIMARY KEY CHECK(id=1),salt TEXT NOT NULL,token_hash TEXT NOT NULL,activated TEXT NOT NULL,actor TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS app_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,action TEXT NOT NULL,created TEXT NOT NULL,payload TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);''')
   db.execute('INSERT OR IGNORE INTO app_meta VALUES(?,?)',('installation_id',secrets.token_hex(16)))
 def owner(self,actor):
  if actor['role']!='superadmin' or actor['email']!=ADMIN_EMAIL:raise PermissionError('Esta acción está reservada a Mario González.')
 def admin(self,actor):
  if actor['role'] not in ('superadmin','auxti'):raise PermissionError('Solo administración consulta los datos de instalación.')
 def audit(self,db,actor,action,data):db.execute('INSERT INTO app_audit(actor,action,created,payload) VALUES(?,?,?,?)',(actor['email'],action,now(),json.dumps(data,ensure_ascii=False)))
 def get(self,actor):
  self.admin(actor)
  with self.store.connect() as db:
   revision,payload=db.execute('SELECT revision,payload FROM app_company WHERE id=1').fetchone();license=db.execute('SELECT activated,actor FROM app_license WHERE id=1').fetchone();companies=[{'id':i,'revision':r,**json.loads(p)} for i,r,p in db.execute('SELECT id,revision,payload FROM cm_companies') if not json.loads(p).get('eliminada')];branches=[{'nombre':n,'serie':s,'revision':r} for n,s,r in db.execute('SELECT name,series,revision FROM app_branches')]
   installation=db.execute("SELECT value FROM app_meta WHERE key='installation_id'").fetchone()[0]
  return {'empresa':{**json.loads(payload),'revision':revision},'razonesSociales':companies,'sucursales':branches,'instalacion':installation,'activacion':{'activa':bool(license),'fecha':license[0] if license else None},'puedeActivar':actor['role']=='superadmin' and actor['email']==ADMIN_EMAIL,'puedeRestablecer':actor['role']=='superadmin' and actor['email']==ADMIN_EMAIL,'puedeConfigurar':actor['role']=='superadmin'}
 def save(self,data,actor):
  if actor['role']!='superadmin':raise PermissionError('Solo Superadministrador modifica la empresa.')
  value={key:text(data.get(key,''),limit) for key,limit in [('nombre',200),('rfc',30),('domicilio',700),('rubro',150),('responsable',200),('correo',160),('telefono',60)]}
  if not value['nombre'] or not value['responsable'] or not value['rubro']:raise ValueError('Indica empresa, rubro y responsable.')
  if value['correo'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value['correo']):raise ValueError('Correo de empresa inválido.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');rev=db.execute('SELECT revision FROM app_company WHERE id=1').fetchone()[0]
   if data.get('revision')!=rev:raise Conflict('La empresa cambió. Actualiza antes de guardar.')
   db.execute('UPDATE app_company SET revision=revision+1,payload=? WHERE id=1',(json.dumps(value,ensure_ascii=False),));self.audit(db,actor,'empresa_guardada',{'revision':rev+1})
  return {'ok':True}
 def activate(self,data,actor):
  self.owner(actor);token=data.get('token')
  if not isinstance(token,str) or not 16<=len(token)<=250:raise ValueError('Token de activación inválido.')
  verifier=self.store.directory/'activation-verifier.json'
  if not verifier.exists():raise ValueError('El administrador debe provisionar el verificador privado de activación en el servidor.')
  expected=json.loads(verifier.read_text(encoding='utf-8-sig'));salt=expected.get('salt','');digest=expected.get('token_hash','')
  if not re.fullmatch('[0-9a-f]{32}',salt) or not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Verificador privado inválido.')
  # El token nunca se escribe, devuelve ni incluye en el registro de auditoría.
  given=hashlib.pbkdf2_hmac('sha256',token.encode(),bytes.fromhex(salt),310000).hex()
  if not hmac.compare_digest(given,digest):raise PermissionError('Token de activación incorrecto.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');db.execute('INSERT OR REPLACE INTO app_license VALUES(1,?,?,?,?)',(salt,digest,now(),actor['email']));self.audit(db,actor,'producto_activado',{})
  return {'ok':True,'activa':True}
 def tables(self,db):return [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name") if re.fullmatch('[a-z_]+',r[0])]
 def fingerprint(self,db):
  digest=hashlib.sha256()
  for table in self.tables(db):
   if table in ('sessions','login_attempts'):continue
   digest.update(table.encode())
   for row in db.execute('SELECT * FROM '+table+' ORDER BY rowid'):
    digest.update(repr(tuple(row)).encode('utf8'))
  return digest.hexdigest()
 def reset(self,data,actor):
  self.owner(actor);apply=data.get('aplicar') is True
  if not apply:
   with self.store.connect() as db:
    db.execute('BEGIN');counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in self.tables(db) if t not in PRESERVED};fingerprint=self.fingerprint(db)
   return {'huellaActual':fingerprint,'tablas':counts,'conserva':['Superusuario Mario González','Datos de empresa y activación','Sucursales y configuración','Máximos de folios y SKU'],'confirmacion':'RESTABLECER TODO'}
  if data.get('texto')!='RESTABLECER TODO' or data.get('confirmar') is not True:raise ValueError('Escribe RESTABLECER TODO y confirma la vista previa.')
  folder=self.store.directory/'respaldos';folder.mkdir(exist_ok=True);backup=folder/('antes-restablecer-'+secrets.token_hex(16)+'.sqlite3')
  # La copia se toma antes de pedir el bloqueo de escritura; se valida de nuevo dentro de la transacción.
  with sqlite3.connect(self.store.path,timeout=15) as source,sqlite3.connect(backup) as target:source.backup(target)
  with sqlite3.connect(backup) as saved:backup_hash=self.fingerprint(saved)
  with self.store.atomic() as db:
   current=self.fingerprint(db)
   if data.get('huellaActual')!=current or backup_hash!=current:raise Conflict('Los datos cambiaron. Hay una copia conservada, pero no se eliminó nada; revisa nuevamente.')
   row=db.execute('SELECT salt,password_hash FROM users WHERE email=?',(ADMIN_EMAIL,)).fetchone();password=data.get('password','')
   if not isinstance(password,str) or not row or not hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(row[0]),310000).hex(),row[1]):raise PermissionError('Confirma tu contraseña de superusuario.')
   catalog_values={}
   for table in ('catalog','sales_catalog'):
    rev,payload=db.execute('SELECT revision,payload FROM '+table+' WHERE id=1').fetchone();value=json.loads(payload);state=value['state'];state['reservados']=sorted(set(state['reservados'])|{r['sku'] for r in state['registros'] if r.get('sku')});state['registros']=[]
    from respaldos import blank_master
    value['master']=blank_master('PRODUCTOS' if table=='catalog' else 'SUGERIDO');value.pop('historicosReinicio',None);catalog_values[table]=(rev+1,json.dumps(value,ensure_ascii=False))
   for table in self.tables(db):
    if table not in PRESERVED and not ('sequence' in table or table.endswith('_registry')):db.execute('DELETE FROM '+table)
   for table,(rev,payload) in catalog_values.items():db.execute('INSERT INTO '+table+' VALUES(1,?,?)',(rev,payload))
   from respaldos import blank_master
   report={'archivo':'PRODUCTOS VACIO.xlsx','hoja':'PRODUCTOS','total':0,'sinSku':0,'sinUnidad':0,'skuRepetidos':0,'inactivos':0}
   db.execute('INSERT INTO req_masters(filename,created_at,actor,content,report) VALUES(?,?,?,?,?)',(report['archivo'],now(),ADMIN_EMAIL,blank_master('PRODUCTOS'),json.dumps(report)))
   db.execute('DELETE FROM users WHERE email<>?',(ADMIN_EMAIL,));db.execute('DELETE FROM sessions WHERE email<>?',(ADMIN_EMAIL,));db.execute("UPDATE users SET role='superadmin',active=1 WHERE email=?",(ADMIN_EMAIL,));self.audit(db,actor,'restablecimiento_integral',{'respaldo':backup.name})
  return {'ok':True,'respaldoPrevio':backup.name}
