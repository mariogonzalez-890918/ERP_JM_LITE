"""Empresa, activación privada y restablecimiento integral del producto comercial."""
import base64,contextlib,datetime,hashlib,hmac,io,json,pathlib,re,secrets,sqlite3
from app_info import ADMIN_EMAIL,is_internal_admin
from requisiciones import Conflict,now,text
from sucursales import BRANCHES,save_branch
PRESERVED={'app_product_options','app_taxes','app_product_taxes','sku_taxonomy','app_internal_admins','user_2fa','users','sessions','role_modules','permission_features','app_branches','app_company','app_license','app_audit','app_meta','cm_companies','cm_revision','cm_sequences','cm_sequence_registry','req_branches','req_series_registry','req_areas','req_report_features','req_reports','sales_features','po_settings','po_features','inv_features','inv_concepts'}

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
  if not is_internal_admin(actor):raise PermissionError('Esta acción está reservada a Sistemas.')
 def edition(self):
  with self.store.connect() as db:row=db.execute("SELECT value FROM app_meta WHERE key='edition'").fetchone()
  code=row[0] if row and row[0] in ('lite','avanzada') else 'lite'
  return {'codigo':code,'nombre':'Avanzada' if code=='avanzada' else 'Lite'}
 def contract(self,actor):
  self.owner(actor)
  from permissions import MODULES
  with self.store.connect() as db:row=db.execute("SELECT value FROM app_meta WHERE key='module_contract'").fetchone()
  value=json.loads(row[0]) if row else {'revision':0,'modules':[] if getattr(self.store,'enforce_contract',False) else list(MODULES)}
  return {**value,'disponibles':MODULES,'configurado':bool(row)}
 def save_contract(self,data,actor):
  self.owner(actor)
  from permissions import MODULES
  modules=data.get('modules')
  if not isinstance(modules,list) or len(set(modules))!=len(modules) or any(not isinstance(m,str) or m not in MODULES for m in modules):raise ValueError('Selecciona módulos válidos.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');old=self.contract(actor)
   if data.get('revision')!=old['revision']:raise Conflict('Los módulos contratados cambiaron.')
   value={'revision':old['revision']+1,'modules':modules};db.execute("INSERT INTO app_meta VALUES('module_contract',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(value),));self.audit(db,actor,'modulos_contratados',{'modules':modules})
  return {'ok':True,**value}
 def save_edition(self,data,actor):
  self.owner(actor);code=data.get('edicion')
  if code not in ('lite','avanzada'):raise ValueError('Selecciona Lite o Avanzada.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');db.execute("INSERT INTO app_meta VALUES('edition',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(code,));self.audit(db,actor,'edicion_configurada',{'edicion':code})
  return self.edition()
 def admin(self,actor):
  if actor['role'] not in ('superadmin','auxti'):raise PermissionError('Solo administración consulta los datos de instalación.')
 def audit(self,db,actor,action,data):db.execute('INSERT INTO app_audit(actor,action,created,payload) VALUES(?,?,?,?)',(actor['email'],action,now(),json.dumps(data,ensure_ascii=False)))
 def get(self,actor):
  self.admin(actor)
  with self.store.connect() as db:
   revision,payload=db.execute('SELECT revision,payload FROM app_company WHERE id=1').fetchone();license=db.execute('SELECT activated,actor FROM app_license WHERE id=1').fetchone();companies=[{'id':i,'revision':r,**json.loads(p)} for i,r,p in db.execute('SELECT id,revision,payload FROM cm_companies') if not json.loads(p).get('eliminada')];branches=[{'nombre':n,'serie':s,'revision':r} for n,s,r in db.execute('SELECT name,series,revision FROM app_branches')]
   installation=db.execute("SELECT value FROM app_meta WHERE key='installation_id'").fetchone()[0]
  return {'empresa':{**json.loads(payload),'revision':revision},'razonesSociales':companies,'sucursales':branches,'instalacion':installation,'activacion':{'activa':bool(license),'fecha':license[0] if license else None},'puedeActivar':is_internal_admin(actor),'puedeRestablecer':is_internal_admin(actor),'puedeConfigurar':actor['role']=='superadmin'}
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
 def taxes(self,company,actor):
  self.admin(actor)
  # Valida existencia y acceso con la misma política de razones sociales.
  self.company_logo(company,actor)
  from impuestos import listed
  with self.store.connect() as db:
   products=[{'sku':s,'nombre':json.loads(p).get('nombre',''),'ambito':'ventas'} for s,p in db.execute('SELECT sku,payload FROM cm_products')]
   products += [{'sku':v.get('sku',''),'nombre':v.get('nombre',''),'ambito':'compras'} for p, in db.execute('SELECT payload FROM req_materials') for v in [json.loads(p)] if v.get('sku')]
   links=[{'ambito':s,'sku':k,'impuesto':t,'revision':r} for s,k,t,r in db.execute('SELECT scope,sku,tax,revision FROM app_product_taxes WHERE company=?',(company,))]
   return {'impuestos':listed(db,company),'productos':products,'vinculos':links,'puedeConfigurar':actor['role']=='superadmin'}
 def save_tax(self,data,actor):
  if actor['role']!='superadmin':raise PermissionError('Solo Superadministrador configura impuestos.')
  from impuestos import save,link
  with self.store.atomic() as db:
   self.company_logo(data.get('empresa'),actor)
   result=(link if data.get('vincular') is True else save)(db,data)
   self.audit(db,actor,'impuesto_empresa_configurado',{'empresa':data['empresa'],'vinculo':data.get('vincular') is True})
  return result
 def company_logo(self,company,actor):
  if type(company) is not int or company<=0:raise ValueError('Selecciona una razón social.')
  with self.store.connect() as db:
   if actor['role'] not in ('superadmin','auxti'):
    access=db.execute('SELECT payload FROM cm_access WHERE email=?',(actor['email'],)).fetchone()
    if not access or company not in json.loads(access[0]).get('empresas',[]):raise PermissionError('No tienes acceso a esta razón social.')
   co=db.execute('SELECT payload FROM cm_companies WHERE id=?',(company,)).fetchone()
   if not co or json.loads(co[0]).get('eliminada'):raise ValueError('Razón social no disponible.')
   row=db.execute("SELECT value FROM app_meta WHERE key=?",('company_logo:'+str(company),)).fetchone()
  return json.loads(row[0]) if row else {'revision':0,'imagen':''}
 def save_logo(self,data,actor):
  if actor['role']!='superadmin':raise PermissionError('Solo Superadministrador modifica los logos de las empresas.')
  from PIL import Image,ImageOps,UnidentifiedImageError
  company=data.get('empresa')
  if type(company) is not int or company<=0:raise ValueError('Selecciona una razón social.')
  encoded=data.get('contenido','');image=''
  if not isinstance(encoded,str) or len(encoded)>2800000:raise ValueError('Selecciona un PNG o JPG de hasta 2 MB.')
  if encoded:
   try:
    raw=base64.b64decode(encoded,validate=True)
    if len(raw)>2*1024*1024:raise ValueError('El logo supera 2 MB.')
    with Image.open(io.BytesIO(raw)) as source:
     if source.format not in ('PNG','JPEG') or source.width*source.height>16000000:raise ValueError('Usa PNG o JPG de hasta 16 millones de píxeles.')
     source.load();clean=ImageOps.exif_transpose(source).convert('RGBA');clean.thumbnail((800,400));out=io.BytesIO();clean.save(out,format='PNG');image='data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()
   except (UnidentifiedImageError,OSError,Image.DecompressionBombError,ValueError) as error:raise ValueError('Logo inválido. Usa una imagen PNG o JPG de hasta 2 MB.') from error
  with self.store.atomic() as db:
   old=self.company_logo(company,actor)
   if data.get('revision')!=old['revision']:raise Conflict('El logo cambió. Actualiza antes de guardar.')
   value={'revision':old['revision']+1,'imagen':image}
   db.execute('INSERT INTO app_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('company_logo:'+str(company),json.dumps(value)))
   self.audit(db,actor,'logo_empresa_guardado',{'empresa':company,'conLogo':bool(image)})
  return {'ok':True,**value}
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
  with contextlib.closing(sqlite3.connect(self.store.path,timeout=15)) as source,contextlib.closing(sqlite3.connect(backup)) as target:source.backup(target)
  with contextlib.closing(sqlite3.connect(backup)) as saved:backup_hash=self.fingerprint(saved)
  with self.store.atomic() as db:
   current=self.fingerprint(db)
   if data.get('huellaActual')!=current or backup_hash!=current:raise Conflict('Los datos cambiaron. Hay una copia conservada, pero no se eliminó nada; revisa nuevamente.')
   row=db.execute('SELECT salt,password_hash FROM users WHERE email=?',(actor['email'],)).fetchone();password=data.get('password','')
   if not isinstance(password,str) or not row or not hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(row[0]),310000).hex(),row[1]):raise PermissionError('Confirma tu contraseña de superusuario.')
   catalog_values={}
   for table in ('catalog','sales_catalog'):
    rev,payload=db.execute('SELECT revision,payload FROM '+table+' WHERE id=1').fetchone();value=json.loads(payload);state=value['state'];state['reservados']=sorted(set(state['reservados'])|{r['sku'] for r in state['registros'] if r.get('sku')});state['registros']=[]
    from respaldos import blank_master
    value['master']=blank_master('PRODUCTOS' if table=='catalog' else 'SUGERIDO');value.pop('historicosReinicio',None);catalog_values[table]=(rev+1,json.dumps(value,ensure_ascii=False))
   for table in self.tables(db):
    if table not in PRESERVED and not ('sequence' in table or table.endswith('_registry')):db.execute('DELETE FROM '+table)
   for table,(rev,payload) in catalog_values.items():db.execute('INSERT INTO '+table+' VALUES(1,?,?)',(rev,payload))
   db.execute("INSERT INTO cm_source VALUES(1,0,'{}','{}')");db.execute('UPDATE cm_revision SET revision=revision+1 WHERE id=1')
   from respaldos import blank_master
   report={'archivo':'PRODUCTOS VACIO.xlsx','hoja':'PRODUCTOS','total':0,'sinSku':0,'sinUnidad':0,'skuRepetidos':0,'inactivos':0}
   db.execute('INSERT INTO req_masters(filename,created_at,actor,content,report) VALUES(?,?,?,?,?)',(report['archivo'],now(),ADMIN_EMAIL,blank_master('PRODUCTOS'),json.dumps(report)))
   db.execute('DELETE FROM user_2fa WHERE email NOT IN (SELECT email FROM app_internal_admins)');db.execute('DELETE FROM users WHERE email NOT IN (SELECT email FROM app_internal_admins)');db.execute('DELETE FROM sessions WHERE email NOT IN (SELECT email FROM app_internal_admins)');db.execute("UPDATE users SET role='superadmin',active=1 WHERE email IN (SELECT email FROM app_internal_admins)");self.audit(db,actor,'restablecimiento_integral',{'respaldo':backup.name})
  return {'ok':True,'respaldoPrevio':backup.name}
