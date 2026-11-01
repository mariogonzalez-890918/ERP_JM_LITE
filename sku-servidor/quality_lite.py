"""QualityLite integrado: misma sesión, permisos y SQLite de ERP JM Lite."""
import base64,hashlib,json,pathlib,re,secrets
from fechas import iso_date
from requisiciones import Conflict,now,text
from permissions import require_module
MODULES={'documents':'Documentos','forms':'Diseñador de formatos','records':'Registros','audits':'Auditorías','findings':'No conformidades','actions':'Acciones correctivas'}
FIELDS={'documents':['tipo','area','proceso','elaborador','revisor','aprobador','fecha_vigencia','proxima_revision','motivo'],'forms':['area','responsable','descripcion','instrucciones'],'audits':['fecha','alcance','proceso','auditor','lista_verificacion'],'findings':['area','proceso','descripcion','clasificacion','auditoria','responsable','fecha_compromiso','causa','accion_inmediata'],'actions':['no_conformidad','responsable','fecha_compromiso','accion_correctiva','verificacion_eficacia'],'records':['formato','valores']}
STATES={'documents':['BORRADOR','APROBADO','OBSOLETO'],'forms':['BORRADOR','APROBADO','OBSOLETO'],'records':['BORRADOR','REGISTRADO'],'audits':['PROGRAMADA','EN_CURSO','CERRADA'],'findings':['ABIERTA','EN_ANALISIS','CERRADA'],'actions':['ABIERTA','EN_PROCESO','VERIFICADA','CERRADA']}
TYPES=['texto','texto_largo','fecha','hora','numero','lista','multiple','casilla','si_no_na','responsable','tabla','fotografia','archivo','evidencia','comentarios','observaciones']
EXTRA_MODULES={
 'inspections':('Inspecciones y liberación',['fecha','producto','lote','proveedor','criterios','resultado','responsable','observaciones']),
 'risks':('Riesgos y oportunidades',['proceso','riesgo','probabilidad','impacto','controles','responsable','fecha_compromiso','seguimiento']),
 'calibrations':('Equipos y calibraciones',['equipo','serie','ubicacion','responsable','fecha','proxima_revision','patron','resultado','certificado']),
 'maintenance':('Mantenimiento de equipos',['equipo','tipo','responsable','fecha','proxima_revision','trabajos','resultado']),
 'training':('Capacitación y competencias',['tema','instructor','participantes','fecha','evaluacion','resultado','responsable','proxima_revision']),
 'complaints':('Quejas y devoluciones',['cliente','producto','lote','fecha','descripcion','responsable','fecha_compromiso','causa','respuesta']),
 'supplier_reviews':('Evaluación de proveedores',['proveedor','periodo','calidad','entrega','servicio','resultado','responsable','proxima_revision']),
 'changes':('Control de cambios',['proceso','descripcion','justificacion','riesgos','responsable','fecha_compromiso','verificacion']),
 'improvements':('Mejora continua',['proceso','situacion_actual','objetivo','indicador','responsable','fecha_compromiso','resultado'])}
for key,(label,fields) in EXTRA_MODULES.items():MODULES[key]=label;FIELDS[key]=fields;STATES[key]=['BORRADOR','REGISTRADO']

class QualityLite:
 def __init__(self,store):
  self.store=store
  with store.connect() as db:
   db.executescript('''CREATE TABLE IF NOT EXISTS q_items(id TEXT PRIMARY KEY,module TEXT NOT NULL,code TEXT NOT NULL,title TEXT NOT NULL,version INTEGER NOT NULL,state TEXT NOT NULL,payload TEXT NOT NULL,author TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL,revision INTEGER NOT NULL,UNIQUE(module,code,version));
   CREATE TABLE IF NOT EXISTS q_events(id INTEGER PRIMARY KEY AUTOINCREMENT,item TEXT NOT NULL,actor TEXT NOT NULL,action TEXT NOT NULL,created TEXT NOT NULL,payload TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS q_files(id TEXT PRIMARY KEY,item TEXT NOT NULL,name TEXT NOT NULL,mime TEXT NOT NULL,sha256 TEXT NOT NULL,content BLOB NOT NULL,author TEXT NOT NULL,created TEXT NOT NULL);
   CREATE INDEX IF NOT EXISTS q_module_state ON q_items(module,state,updated);''')
 def scope(self,actor,write=False):
  require_module(actor,'calidad')
  if write and actor['role'] not in ('superadmin','calidad'):raise PermissionError('Solo Calidad y Superadministrador modifican QualityLite.')
 def dashboard(self,actor):
  self.scope(actor);today=now()[:10];counts={key:0 for key in MODULES};pending=[]
  with self.store.connect() as db:
   for id,module,code,title,state,payload in db.execute('SELECT id,module,code,title,state,payload FROM q_items'):
    counts[module]=counts.get(module,0)+1;value=json.loads(payload);due=value.get('fecha_compromiso') or value.get('proxima_revision')
    if due and due<=today and state not in ('CERRADA','OBSOLETO','REGISTRADO'):pending.append({'id':id,'modulo':module,'codigo':code,'titulo':title,'fecha':due,'responsable':value.get('responsable') or value.get('aprobador','')})
  return {'totales':counts,'vencidosPendientes':sorted(pending,key=lambda v:v['fecha'])[:100]}
 def event(self,db,id,actor,action,payload):db.execute('INSERT INTO q_events(item,actor,action,created,payload) VALUES(?,?,?,?,?)',(id,actor['email'],action,now(),json.dumps(payload,ensure_ascii=False)))
 def row(self,db,id):
  row=db.execute('SELECT id,module,code,title,version,state,payload,author,created,updated,revision FROM q_items WHERE id=?',(id,)).fetchone()
  if not row:raise ValueError('Registro de calidad no disponible.')
  value=dict(zip(('id','modulo','codigo','titulo','version','estado','datos','autor','creado','actualizado','revision'),row));value['datos']=json.loads(value['datos']);return value
 def get(self,query,actor):
  self.scope(actor);module=query.get('modulo','documents')
  if module not in MODULES:raise ValueError('Módulo de calidad inválido.')
  with self.store.connect() as db:
   if query.get('id'):
    value=self.row(db,query['id']);value['eventos']=[{'actor':a,'accion':c,'fecha':f} for a,c,f in db.execute('SELECT actor,action,created FROM q_events WHERE item=? ORDER BY id',(value['id'],))];value['archivos']=[{'id':i,'nombre':n,'sha256':s,'fecha':f} for i,n,s,f in db.execute('SELECT id,name,sha256,created FROM q_files WHERE item=?',(value['id'],))];return value
   since=iso_date(query.get('desde'));until=iso_date(query.get('hasta'))
   if since and until and since>until:raise ValueError('Rango de fechas inválido.')
   clauses=['module=?'];args=[module]
   for key,value in [('state',query.get('estado')),('author',query.get('responsable'))]:
    if value:clauses.append(key+'=?');args.append(value)
   if since:clauses.append('substr(created,1,10)>=?');args.append(since)
   if until:clauses.append('substr(created,1,10)<=?');args.append(until)
   if query.get('q'):clauses.append('(instr(lower(code),lower(?))>0 OR instr(lower(title),lower(?))>0)');args.extend([query['q'],query['q']])
   ids=[r[0] for r in db.execute('SELECT id FROM q_items WHERE '+' AND '.join(clauses)+' ORDER BY updated DESC LIMIT 1000',args)]
   return {'modulos':MODULES,'campos':FIELDS,'estados':STATES,'tipos':TYPES,'registros':[self.row(db,id) for id in ids],'puedeEditar':actor['role'] in ('superadmin','calidad')}
 def schema(self,fields):
  if not isinstance(fields,list) or not 1<=len(fields)<=100:raise ValueError('Define entre 1 y 100 campos del formato.')
  result=[];seen=set()
  for field in fields:
   if not isinstance(field,dict):raise ValueError('Campo de formato inválido.')
   id=text(field.get('id',''),40);label=text(field.get('label',''),160);kind=field.get('type');options=field.get('options',[])
   if not re.fullmatch('[a-zA-Z][a-zA-Z0-9_]{0,39}',id) or id in seen or not label or kind not in TYPES or not isinstance(options,list) or len(options)>30 or any(not isinstance(v,str) or len(v)>160 for v in options):raise ValueError('Identificador, etiqueta, tipo u opciones inválidos.')
   seen.add(id);result.append({'id':id,'label':label,'type':kind,'section':text(field.get('section','Datos'),100),'required':field.get('required') is True,'options':options})
  return result
 def record_values(self,db,data):
  form=self.row(db,data.get('formato',''))
  if form['modulo']!='forms' or form['estado']!='APROBADO':raise ValueError('Selecciona una versión aprobada del formato.')
  values=data.get('valores',{})
  if not isinstance(values,dict) or set(values)-{f['id'] for f in form['datos']['schema']}:raise ValueError('Los valores no corresponden al formato.')
  cleaned={}
  for field in form['datos']['schema']:
   v=values.get(field['id'],'');kind=field['type']
   if field['required'] and (v is None or v=='' or v==[]):raise ValueError('Falta '+field['label'])
   if v in ('',None):cleaned[field['id']]='';continue
   if kind=='fecha':v=iso_date(v)
   elif kind=='hora' and (not isinstance(v,str) or not re.fullmatch('(?:[01][0-9]|2[0-3]):[0-5][0-9]',v)):raise ValueError('Hora inválida: '+field['label'])
   elif kind=='numero':
    from decimal import Decimal,InvalidOperation
    try:
     n=Decimal(str(v))
     if not n.is_finite() or abs(n)>10**15:raise ValueError()
    except (InvalidOperation,ValueError):raise ValueError('Número inválido: '+field['label'])
   elif kind in ('lista','si_no_na') and v not in (field['options'] if kind=='lista' else ['SI','NO','NA']):raise ValueError('Opción inválida: '+field['label'])
   elif kind=='multiple' and (not isinstance(v,list) or set(v)-set(field['options'])):raise ValueError('Selección inválida.')
   elif kind=='casilla' and type(v) is not bool:raise ValueError('Casilla inválida.')
   elif kind=='tabla' and (not isinstance(v,list) or len(v)>100 or any(not isinstance(r,list) or len(r)>8 or any(not isinstance(c,str) or len(c)>1000 for c in r) for r in v)):raise ValueError('Tabla inválida.')
   elif kind not in ('multiple','tabla','casilla'):v=text(v,8000)
   cleaned[field['id']]=v
  return {'formato':form['id'],'versionFormato':form['version'],'codigoFormato':form['codigo'],'schema':form['datos']['schema'],'valores':cleaned}
 def save(self,data,actor):
  self.scope(actor,True);module=data.get('modulo');id=data.get('id') or secrets.token_hex(16);code=text(data.get('codigo',''),80);title=text(data.get('titulo',''),250)
  if module not in MODULES or not code or not title:raise ValueError('Indica módulo, código y título.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');exists=db.execute('SELECT 1 FROM q_items WHERE id=?',(id,)).fetchone();old=self.row(db,id) if exists else None
   if data.get('revision',0)!=(old['revision'] if old else 0):raise Conflict('El registro cambió. Actualiza antes de guardar.')
   if old and (old['modulo']!=module or old['estado'] in ('APROBADO','OBSOLETO','REGISTRADO','CERRADA')):raise ValueError('Esta versión está cerrada. Crea una nueva versión cuando corresponda.')
   raw=data.get('datos',{})
   if not isinstance(raw,dict):raise ValueError('Datos de calidad inválidos.')
   values={k:text(raw.get(k,''),8000) for k in FIELDS[module] if k!='valores'} if module!='records' else self.record_values(db,raw)
   if module=='forms':values['schema']=self.schema(raw.get('schema',[]))
   for key in ('fecha','fecha_vigencia','proxima_revision','fecha_compromiso'):
    if values.get(key):values[key]=iso_date(values[key])
   for key,target in [('auditoria','audits'),('no_conformidad','findings')]:
    if values.get(key) and self.row(db,values[key])['modulo']!=target:raise ValueError('Referencia de calidad incorrecta.')
   state=old['estado'] if old else STATES[module][0];stamp=now();version=old['version'] if old else 1
   if old:db.execute('UPDATE q_items SET code=?,title=?,payload=?,updated=?,revision=revision+1 WHERE id=?',(code,title,json.dumps(values,ensure_ascii=False),stamp,id))
   else:db.execute('INSERT INTO q_items VALUES(?,?,?,?,?,?,?,?,?,?,1)',(id,module,code,title,version,state,json.dumps(values,ensure_ascii=False),actor['email'],stamp,stamp))
   self.event(db,id,actor,'guardado',{'revision':(old['revision'] if old else 0)+1})
  return {'ok':True,'id':id}
 def transition(self,data,actor):
  self.scope(actor,True)
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');item=self.row(db,data.get('id',''));state=data.get('estado')
   if item['revision']!=data.get('revision'):raise Conflict('El registro cambió.')
   transitions={'BORRADOR':['APROBADO'] if item['modulo'] in ('documents','forms') else ['REGISTRADO'],'APROBADO':['OBSOLETO'],'PROGRAMADA':['EN_CURSO'],'EN_CURSO':['CERRADA'],'ABIERTA':['EN_ANALISIS'] if item['modulo']=='findings' else ['EN_PROCESO'],'EN_ANALISIS':['CERRADA'],'EN_PROCESO':['VERIFICADA'],'VERIFICADA':['CERRADA']}
   if state not in transitions.get(item['estado'],[]):raise ValueError('Transición de estado no permitida.')
   if state=='CERRADA' and item['modulo']=='actions' and not item['datos'].get('verificacion_eficacia'):raise ValueError('Registra la verificación de eficacia antes de cerrar.')
   db.execute('UPDATE q_items SET state=?,updated=?,revision=revision+1 WHERE id=?',(state,now(),item['id']));self.event(db,item['id'],actor,'estado',{'antes':item['estado'],'estado':state})
  return {'ok':True}
 def new_version(self,data,actor):
  self.scope(actor,True)
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');item=self.row(db,data.get('id',''))
   if item['modulo'] not in ('forms','documents') or item['estado'] not in ('APROBADO','OBSOLETO'):raise ValueError('Solo documentos o formatos aprobados tienen nueva versión.')
   if item['revision']!=data.get('revision'):raise Conflict('El documento cambió.')
   version=db.execute('SELECT max(version)+1 FROM q_items WHERE module=? AND code=?',(item['modulo'],item['codigo'])).fetchone()[0];id=secrets.token_hex(16);stamp=now()
   db.execute('INSERT INTO q_items VALUES(?,?,?,?,?,?,?,?,?,?,1)',(id,item['modulo'],item['codigo'],item['titulo'],version,'BORRADOR',json.dumps(item['datos'],ensure_ascii=False),actor['email'],stamp,stamp));self.event(db,id,actor,'nueva_version',{'origen':item['id']})
  return {'ok':True,'id':id}
 def attach(self,data,actor):
  self.scope(actor,True)
  try:content=base64.b64decode(data.get('contenido',''),validate=True)
  except Exception:raise ValueError('Archivo inválido.')
  name=pathlib.PureWindowsPath(text(data.get('nombre',''),150)).name
  if not name or not 1<=len(content)<=10*1024*1024:raise ValueError('Adjunta un archivo de hasta 10 MB.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');item=self.row(db,data.get('id',''))
   if item['revision']!=data.get('revision'):raise Conflict('El registro cambió.')
   if item['estado'] in ('APROBADO','OBSOLETO','REGISTRADO','CERRADA'):raise ValueError('No se agregan archivos a versiones cerradas.')
   id=secrets.token_hex(16);db.execute('INSERT INTO q_files VALUES(?,?,?,?,?,?,?,?)',(id,item['id'],name,'application/octet-stream',hashlib.sha256(content).hexdigest(),content,actor['email'],now()));db.execute('UPDATE q_items SET revision=revision+1,updated=? WHERE id=?',(now(),item['id']));self.event(db,item['id'],actor,'evidencia_agregada',{'nombre':name,'sha256':hashlib.sha256(content).hexdigest()})
  return {'ok':True,'id':id}
 def file(self,id,actor):
  self.scope(actor)
  with self.store.connect() as db:row=db.execute('SELECT content FROM q_files WHERE id=?',(id,)).fetchone()
  if not row:raise ValueError('Evidencia no disponible.')
  return bytes(row[0]),'application/octet-stream'
 def export(self,query,actor,pdf=False):
  from comercial_print import report_xlsx,report_pdf
  result=self.get({k:v for k,v in query.items() if k!='id'},actor);items=result['registros'];fields=[]
  for item in items:
   labels=[f['label'] for f in item['datos'].get('schema',[])] if item['modulo']=='records' else [k.replace('_',' ').capitalize() for k in item['datos'] if k!='schema']
   for label in labels:
    if label not in fields:fields.append(label)
  rows=[['Código','Título','Versión','Estado','Actualizado',*fields]]
  for item in items:
   values={f['label']:item['datos']['valores'].get(f['id'],'') for f in item['datos'].get('schema',[])} if item['modulo']=='records' else {k.replace('_',' ').capitalize():v for k,v in item['datos'].items() if k!='schema'}
   rows.append([item['codigo'],item['titulo'],item['version'],item['estado'],item['actualizado'],*[str(values.get(f,'')) for f in fields]])
  return (report_pdf(rows,'QualityLite · '+MODULES[query.get('modulo','documents')],subtitle='Reporte según filtros de calidad. Se conserva la versión y estado de cada registro.'),'application/pdf') if pdf else (report_xlsx(rows,'CALIDAD'),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
