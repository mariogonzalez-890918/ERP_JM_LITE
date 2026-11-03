"""Producción configurable integrada con Inventarios y su costo promedio."""
import copy,json,re,uuid
from decimal import Decimal,ROUND_UP,ROUND_HALF_UP
from comercial import dumps,fingerprint
from inventarios import dec,fmt
from operaciones_base import initialize,reserved,reserve,consume_reserve,setting,save_setting,series
from permissions import require_module
from requisiciones import Conflict,now,text
from fechas import iso_date
METHODS=['DISCRETA','LOTES','BAJO_PEDIDO','PARA_INVENTARIO','ENSAMBLE','SUBENSAMBLES','PROCESOS','ETAPAS']
CAPS=['consultar','crear','autorizar','editar','surtir','consumir','fabricar','recibir','merma','reproceso','calidad','cerrar','cancelar','costos','reportes','configurar']
DEFAULT_CAPS={'superadmin':CAPS,'gerente':CAPS,'produccion':['consultar','crear','editar','surtir','consumir','fabricar','recibir','merma','reportes'],'almacenista':['consultar','surtir','consumir','recibir','reportes'],'calidad':['consultar','calidad','reportes']}
BOOLS=['activa','terminados','bajoPedido','paraStock','manual','desdePedidos','parcial','lotes','requiereAutorizacion','cierreAutomatico','mermas','desperdicios','reprocesos','cancelar','editarAutorizadas','entreSucursales','calidadMP','calidadProceso','calidadPT','subensambles']
def default_config():
 return {'revision':0,**{k:False for k in BOOLS},'terminados':True,'manual':True,'paraStock':True,'parcial':True,'requiereAutorizacion':True,'mermas':True,'cancelar':True,'subensambles':True,'metodos':['DISCRETA'],'etapas':[],'materiasPrimas':'','consumo':'','terminado':'','cuarentena':'','merma':'','alternativos':[],'toleranciaConsumo':'0','toleranciaProduccion':'0','decimales':6,'redondeo':'ARRIBA','permisos':{}}
class Production:
 def __init__(self,store,inv,cm):
  self.store,self.inv,self.cm=store,inv,cm
  with store.connect() as db:initialize(db,True)
 def config(self,db,company):return {**default_config(),**setting(db,'production:'+str(company),{})}
 def scope(self,db,actor,company,cap='consultar',active=True):
  require_module(actor,'produccion');self.inv.scope(actor)
  if type(company) is not int:raise ValueError('Selecciona una razón social.')
  allowed=[]
  for id, in db.execute('SELECT id FROM inv_warehouses WHERE company=?',(company,)).fetchall():
   try:allowed.append(self.inv.scope(actor,id,db,active))
   except PermissionError:continue
  if not allowed:raise PermissionError('No tienes almacenes asignados en esta razón social.')
  cfg=self.config(db,company);caps=CAPS if actor['role']=='superadmin' else cfg['permisos'].get(actor['email'],DEFAULT_CAPS.get(actor['role'],[]))
  if cap not in caps or cap in ('costos','configurar','autorizar','cancelar') and actor['role'] not in ('superadmin','gerente'):raise PermissionError('No tienes permiso de Producción para '+cap+'.')
  if active and not cfg['activa']:raise ValueError('Producción está desactivada para esta empresa; sus ventas no requieren fabricación.')
  return cfg,allowed
 def public(self,value,actor):
  if actor['role']=='superadmin':return value
  company=value.get('empresa') or value.get('orden',{}).get('empresa') if isinstance(value,dict) else None
  allowed=actor['role']=='gerente'
  if allowed and company:
   with self.store.connect() as db:cfg=self.config(db,company);allowed='costos' in cfg['permisos'].get(actor['email'],DEFAULT_CAPS['gerente'])
  if isinstance(value,dict) and 'ordenes' in value:return {**value,'ordenes':[self.public(o,actor) for o in value['ordenes']]}
  return value if allowed else self.inv.public(value,{'role':'produccion'})
 def metadata(self,actor):
  require_module(actor,'produccion');warehouses=self.inv.warehouses(actor)['almacenes'];companies={w['empresa']:w['razonSocial'] for w in warehouses}
  with self.store.connect() as db:
   configs=[]
   for id,name in companies.items():
    try:cfg,_=self.scope(db,actor,id,active=False)
    except PermissionError:continue
    caps=CAPS if actor['role']=='superadmin' else cfg['permisos'].get(actor['email'],DEFAULT_CAPS.get(actor['role'],[]));configs.append({'id':id,'nombre':name,'configuracion':cfg if actor['role'] in ('superadmin','gerente') else {k:v for k,v in cfg.items() if k!='permisos'},'permisos':caps})
   units=[{'nombre':n} for n, in db.execute("SELECT name FROM app_product_options WHERE kind='unidad' AND active=1")]
   users=[{'email':e,'nombre':n,'perfil':r} for e,n,r in db.execute('SELECT email,name,role FROM users WHERE active=1 AND email NOT IN (SELECT email FROM app_internal_admins)')] if actor['role'] in ('superadmin','gerente') else []
  materials=list(self.inv.materials().values())
  if actor['role']!='superadmin':materials=self.inv.public(materials,{'role':'produccion'})
  return self.public({'empresas':configs,'almacenes':warehouses,'metodos':METHODS,'acciones':CAPS,'permisosPredeterminados':DEFAULT_CAPS,'unidades':units,'usuarios':users,'materiales':materials},actor)
 def save_config(self,data,actor):
  company=data.get('empresa')
  with self.store.atomic() as db:
   self.scope(db,actor,company,'configurar',False);cfg=copy.deepcopy(self.config(db,company))
   for k in BOOLS:
    if k in data:
     if type(data[k]) is not bool:raise ValueError('Opción inválida: '+k)
     cfg[k]=data[k]
   for k in ('metodos','etapas','alternativos','permisos','decimales','redondeo','materiasPrimas','consumo','terminado','cuarentena','merma'):cfg[k]=data.get(k,cfg[k])
   if not isinstance(cfg['metodos'],list) or not cfg['metodos'] or any(v not in METHODS for v in cfg['metodos']):raise ValueError('Selecciona métodos válidos.')
   if not isinstance(cfg['etapas'],list) or len(cfg['etapas'])>30 or any(not isinstance(v,str) or not v.strip() or len(v)>100 for v in cfg['etapas']) or len(set(cfg['etapas']))!=len(cfg['etapas']):raise ValueError('Configura etapas distintas y no vacías.')
   if 'ETAPAS' in cfg['metodos'] and not cfg['etapas']:raise ValueError('El método por etapas requiere una secuencia.')
   if type(cfg['decimales']) is not int or not 0<=cfg['decimales']<=6 or cfg['redondeo'] not in ('ARRIBA','MITAD'):raise ValueError('Configura de cero a seis decimales y el redondeo.')
   for k in ('toleranciaConsumo','toleranciaProduccion'):
    cfg[k]=fmt(dec(data.get(k,cfg[k])))
    if Decimal(cfg[k])>100:raise ValueError('La tolerancia máxima es 100 %.')
   for k in ('criteriosAceptacion','criteriosRechazo'):cfg[k]=text(data.get(k,cfg.get(k,'')),10000)
   if not isinstance(cfg['permisos'],dict):raise ValueError('Permisos inválidos.')
   for email,caps in cfg['permisos'].items():
    if not db.execute('SELECT 1 FROM users WHERE email=? AND active=1',(email,)).fetchone() or not isinstance(caps,list) or any(v not in CAPS for v in caps):raise ValueError('Selecciona usuarios activos y permisos válidos.')
   if not isinstance(cfg['alternativos'],list):raise ValueError('Almacenes alternativos inválidos.')
   locations=[]
   for k in ('materiasPrimas','consumo','terminado','cuarentena','merma'):
    if cfg[k]:
     w=self.inv.scope(actor,cfg[k],db,True)
     if w['empresa']!=company:raise ValueError('Los almacenes deben pertenecer a esta empresa.')
     locations.append(w);expected={'consumo':('PRODUCCION',),'terminado':('PT','GENERAL'),'cuarentena':('CUARENTENA',),'merma':('MERMA',)}
     if k in expected and w['funcion'] not in expected[k]:raise ValueError('Revisa la función del almacén: '+k)
   for id in cfg['alternativos']:
    if self.inv.scope(actor,id,db,True)['empresa']!=company:raise ValueError('Almacén alternativo de otra empresa.')
   if cfg['activa'] and any(not cfg[k] for k in ('materiasPrimas','consumo','terminado')):raise ValueError('Configura almacenes de materias primas, Producción y producto terminado.')
   if not cfg['entreSucursales'] and len({w['sucursal'] for w in locations})>1:raise ValueError('Habilita producción entre sucursales para esta selección.')
   if cfg['calidadPT'] and not cfg['cuarentena']:raise ValueError('La inspección de PT requiere Cuarentena.')
   cfg=save_setting(db,'production:'+str(company),cfg,data.get('revision'));self.cm.audit(db,actor,company,'produccion_configurada',{'revision':cfg['revision']});return cfg
 def material(self,sku):
  m=self.inv.materials().get(str(sku or '').upper())
  if not m:raise ValueError('Selecciona un SKU inventariable activo: '+str(sku))
  return m
 def recipe(self,db,id,company,path=()):
  row=db.execute('SELECT company,payload FROM pr_recipes WHERE id=?',(id,)).fetchone()
  if not row or row[0]!=company:raise ValueError('Receta no disponible en esta empresa.')
  r=json.loads(row[1])
  if r['producto'] in path:raise ValueError('La receta contiene un ciclo entre subensambles.')
  for line in r['componentes']:
   if line.get('subreceta'):line['receta']=self.recipe(db,line['subreceta'],company,path+(r['producto'],))
  return {'id':id,**r}
 def recipes(self,company,actor):
  with self.store.connect() as db:
   self.scope(db,actor,company,active=False);return {'recetas':[{'id':id,**json.loads(p)} for id,p in db.execute('SELECT id,payload FROM pr_recipes WHERE company=? ORDER BY code,version DESC',(company,))]}
 def _save_recipe(self,data,actor):
  company=data.get('empresa');m=self.material(data.get('producto'));code=text(data.get('codigo',''),80).upper();base=dec(data.get('cantidadBase'),True);lines=data.get('componentes')
  if not code or not isinstance(lines,list) or not 1<=len(lines)<=200:raise ValueError('Indica código, rendimiento y componentes.')
  recipe_type=data.get('tipo','TERMINADO')
  if recipe_type not in ('TERMINADO','SUBENSAMBLE'):raise ValueError('Selecciona producto terminado o subensamble.')
  with self.store.connect() as db:
   cfg,_=self.scope(db,actor,company,'crear');prepared=[];seen=set();current=db.execute('SELECT MAX(version) FROM pr_recipes WHERE company=? AND code=?',(company,code)).fetchone()[0] or 0
   if data.get('versionAnterior',current)!=current:raise Conflict('Otra persona creó una versión. Actualiza las recetas.')
   units={n for n, in db.execute("SELECT name FROM app_product_options WHERE kind='unidad' AND active=1")}
   for line in lines:
    material=self.material(line.get('sku'));sku=material['sku'];qty=dec(line.get('cantidad'),True);merma=dec(line.get('merma','0'));unit=text(line.get('unidad',material['unidad']),100);factor=dec(line.get('factor','1'),True)
    if sku==m['sku'] or sku in seen or merma>100:raise ValueError('Componente repetido, cíclico o merma inválida.')
    if unit!=material['unidad'] and unit not in units:raise ValueError('Configura primero la unidad de consumo.')
    if unit==material['unidad'] and factor!=1:raise ValueError('En la misma unidad el factor debe ser 1.')
    alternate=line.get('alternativos',[])
    if not isinstance(alternate,list):raise ValueError('Alternativos inválidos.')
    for alt in alternate:
     if self.material(alt)['unidad']!=material['unidad']:raise ValueError('Los alternativos deben tener la misma unidad de inventario.')
    sub=line.get('subreceta','')
    if sub:
     child=self.recipe(db,sub,company,(m['sku'],))
     if not cfg['subensambles'] or child['producto']!=sku:raise ValueError('La subreceta no corresponde al componente o están desactivados los subensambles.')
    seen.add(sku);prepared.append({'sku':sku,'nombre':material['nombre'],'cantidad':fmt(qty),'unidad':unit,'unidadInventario':material['unidad'],'factor':fmt(factor),'merma':fmt(merma),'subreceta':sub,'alternativos':alternate})
   id=uuid.uuid4().hex;value={'codigo':code,'version':current+1,'producto':m['sku'],'nombre':m['nombre'],'unidad':m['unidad'],'cantidadBase':fmt(base),'vigencia':iso_date(data.get('vigencia')) or now()[:10],'instrucciones':text(data.get('instrucciones',''),20000),'activo':data.get('activo',True) is True,'componentes':prepared,'creador':actor['email'],'fecha':now()}
   value['tipo']=recipe_type;db.execute('INSERT INTO pr_recipes VALUES(?,?,?,?,?)',(id,company,code,current+1,dumps(value)));self.cm.audit(db,actor,company,'receta_versionada',{'id':id,'version':current+1});return {'id':id,**value}
 def required(self,recipe,quantity,cfg):
  quantum=Decimal(1).scaleb(-cfg['decimales']);rounding=ROUND_UP if cfg['redondeo']=='ARRIBA' else ROUND_HALF_UP
  return [{**line,'requerido':fmt((quantity/Decimal(recipe['cantidadBase'])*Decimal(line['cantidad'])*Decimal(line['factor'])*(1+Decimal(line['merma'])/100)).quantize(quantum,rounding=rounding))} for line in recipe['componentes']]
 def explosion(self,db,recipe,quantity,w,cfg,document='',level=0,pool=None):
  if level>30:raise ValueError('La receta supera 30 niveles.')
  if pool is None:pool={}
  rows=[];total=Decimal(0);missing_cost=False
  for line in self.required(recipe,quantity,cfg):
   q=Decimal(line['requerido']);balance=self.inv.balance(db,w,line['sku']);physical=Decimal(balance['cantidad']) if balance else Decimal(0);held=reserved(db,w,line['sku'],document);available=max(Decimal(0),physical-held-pool.get(line['sku'],Decimal(0)));missing=max(Decimal(0),q-available);pool[line['sku']]=pool.get(line['sku'],Decimal(0))+min(q,available);m=self.material(line['sku']);cost=Decimal(balance['costo']) if balance else dec(m['costo']) if m.get('costo') is not None else None;children=[]
   if line.get('receta') and missing>0:
    children,estimated=self.explosion(db,line['receta'],missing,w,cfg,document,level+1,pool);own=min(q,available)*(cost or Decimal(0))+estimated if estimated is not None else None
   else:own=q*cost if cost is not None else None
   rows.append({**{k:v for k,v in line.items() if k!='receta'},'nivel':level,'fisico':fmt(physical),'reservado':fmt(held),'disponible':fmt(available),'faltante':fmt(missing),'porFabricar':fmt(missing) if line.get('receta') else '0','costoEstimado':fmt(own) if own is not None else None});rows.extend(children)
   if own is None:missing_cost=True
   else:total+=own
  return rows,None if missing_cost else total
 def plan(self,data,actor):
  with self.store.connect() as db:
   cfg,_=self.scope(db,actor,data.get('empresa'));recipe=self.recipe(db,data.get('receta'),data['empresa']);quantity=dec(data.get('cantidad'),True);w=self.inv.scope(actor,data.get('almacen') or cfg['materiasPrimas'],db)
   if w['empresa']!=data['empresa']:raise ValueError('Almacén de otra empresa.')
   rows,cost=self.explosion(db,recipe,quantity,w['id'],cfg)
   return self.public({'empresa':data['empresa'],'receta':recipe,'cantidad':fmt(quantity),'unidad':recipe['unidad'],'explosionado':rows,'costoEstimado':fmt(cost) if cost is not None else None,'almacen':w},actor)
 def order(self,db,id,actor,cap='consultar'):
  row=db.execute('SELECT company,revision,payload FROM pr_orders WHERE id=?',(id,)).fetchone()
  if not row:raise ValueError('Orden de producción inexistente.')
  self.scope(db,actor,row[0],cap,False);value={'id':id,'revision':row[1],**json.loads(row[2])};self.inv.scope(actor,value['consumo'],db);return value
 def list(self,query,actor):
  company=int(query.get('empresa',0));start=iso_date(query.get('desde'));end=iso_date(query.get('hasta'));out=[]
  if start and end and start>end:raise ValueError('Revisa el rango de fechas.')
  with self.store.connect() as db:
   self.scope(db,actor,company,active=False)
   for id, in db.execute('SELECT id FROM pr_orders WHERE company=? ORDER BY rowid DESC',(company,)).fetchall():
    try:o=self.order(db,id,actor)
    except PermissionError:continue
    if query.get('estado') and o['estado']!=query['estado'] or query.get('producto') and o['producto']!=query['producto'] or query.get('almacen') and query['almacen'] not in (o['consumo'],o['terminado'],o['materiasPrimas']):continue
    if start and o['fecha'][:10]<start or end and o['fecha'][:10]>end:continue
    if query.get('sucursal') and o['sucursal']!=query['sucursal']:continue
    if query.get('pedido'):
     source=db.execute('SELECT payload FROM cm_documents WHERE id=?',(o['pedido'],)).fetchone();folio=json.loads(source[0]).get('folio','') if source else ''
     if query['pedido'].upper() not in (o['pedido']+' '+folio).upper():continue
    out.append(o)
  return self.public({'ordenes':out},actor)
 def pending_cost(self,o):return max(Decimal(0),Decimal(o['costoConsumido'])+Decimal(o['costoCargos'])-Decimal(o['costoPerdidas'])-Decimal(o['costoAsignado']))
 def location(self,db,id,o,actor,functions=None):
  w=self.inv.scope(actor,id,db,True)
  if w['empresa']!=o['empresa'] or not w['activo']:raise ValueError('El almacén debe estar activo en la misma empresa.')
  if o.get('ciclos',{}).get(id,w['ciclo'])!=w['ciclo']:raise Conflict('El almacén cambió de ciclo desde la emisión de la orden.')
  o.setdefault('ciclos',{}).setdefault(id,w['ciclo'])
  if functions and w['funcion'] not in functions:raise ValueError('La función del almacén no corresponde a esta operación.')
  return w
 def authorize(self,db,o,cfg,actor):
  for id in (o['materiasPrimas'],o['consumo'],o['terminado']):self.location(db,id,o,actor)
  if not o['folio']:o['folio']=self.cm.next_number(db,o['empresa'],'PRODUCCION:'+o['sucursal'])
  for line in self.required(o['receta'],Decimal(o['cantidadPlaneada']),cfg):
   balance=self.inv.balance(db,o['materiasPrimas'],line['sku']);available=max(Decimal(0),Decimal(balance['cantidad'])-reserved(db,o['materiasPrimas'],line['sku'],o['id'])) if balance else Decimal(0)
   held_in_production=sum((Decimal(q) for sku,q in db.execute('SELECT sku,qty FROM op_reservations WHERE document=? AND warehouse=?',(o['id'],o['consumo'])) if sku in [line['sku'],*line.get('alternativos',[])]),Decimal(0));needed=max(Decimal(0),Decimal(line['requerido'])-Decimal(o['consumos'].get(line['sku'],'0'))-held_in_production);reserve(db,o['id'],o['materiasPrimas'],line['sku'],min(available,needed))
  if o['estado'] in ('BORRADOR','PENDIENTE_AUTORIZACION','AUTORIZADA'):o['estado']='AUTORIZADA'
  o['autorizacion']={'actor':actor['email'],'fecha':now()}
 def series(self,data,actor,save=False):
  with self.store.atomic() as db:
   self.scope(db,actor,data.get('empresa'),'configurar',False);branch=data.get('sucursal')
   if not any(w['sucursal']==branch for w in self.inv.warehouses(actor)['almacenes'] if w['empresa']==data['empresa']):raise ValueError('Selecciona una sucursal autorizada.')
   return series(self.cm,db,data['empresa'],'PRODUCCION:'+branch,data if save else None)
 def detail(self,id,actor):
  with self.store.connect() as db:
   o=self.order(db,id,actor);events=[{'tipo':kind,'fecha':date,'actor':who,'movimientos':json.loads(p).get('movimientos',[]),'datos':json.loads(p).get('datos',{})} for kind,date,who,p in db.execute('SELECT kind,created,actor,payload FROM pr_events WHERE document=? ORDER BY rowid',(id,))];return self.public({'orden':o,'eventos':events,'requeridos':self.required(o['receta'],Decimal(o['cantidadPlaneada']),self.config_for_sheet(o))},actor)
 def mutate(self,action,data,actor):
  from produccion_eventos import mutate
  return mutate(self,action,data,actor)

 def save_recipe(self,data,actor):
  with self.store.atomic():return self._save_recipe(data,actor)

 def config_for_sheet(self,o):return o.get("parametros",default_config())
