"""Alta de vendedores, comisiones privadas y presupuesto mensual autorizado."""
import json,re,secrets,sqlite3
from decimal import Decimal
from crm import CRM,MANAGERS
from app_info import is_internal_admin
from comercial import amount,money,dumps
from requisiciones import Conflict,now,text

class CRMManagement(CRM):
 def __init__(self,cm):
  super().__init__(cm)
  with self.store.connect() as db:
   db.executescript('''CREATE TABLE IF NOT EXISTS crm_commissions(company INTEGER NOT NULL,customer TEXT NOT NULL,seller TEXT NOT NULL,percentage TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(company,customer,seller));
   CREATE TABLE IF NOT EXISTS crm_dashboard_access(company INTEGER NOT NULL,email TEXT NOT NULL,enabled INTEGER NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(company,email));
   CREATE TABLE IF NOT EXISTS crm_plans(id TEXT PRIMARY KEY,company INTEGER NOT NULL,month TEXT NOT NULL,customer TEXT NOT NULL,seller TEXT NOT NULL,kind TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL);
   CREATE UNIQUE INDEX IF NOT EXISTS crm_month_customer ON crm_plans(company,month,customer) WHERE kind='CLIENTE';''')
 def metadata(self,actor,company):
  value=super().metadata(actor,company);value['vendedores']=[v for v in value['vendedores'] if company in self.cm.access({'email':v['email']})['empresas']]
  value.update({'puedeAgregarVendedores':is_internal_admin(actor),'puedeComisiones':actor['role'] in MANAGERS,'puedeTableroMensual':self.insight_allowed(actor,company),'puedeAutorizarTablero':is_internal_admin(actor)})
  if actor['role'] in MANAGERS:
   with self.store.connect() as db:commissions={(c,s):(p,r) for c,s,p,r in db.execute('SELECT customer,seller,percentage,revision FROM crm_commissions WHERE company=?',(company,))}
   for c in value['clientes']:c['comision'],c['revisionComision']=commissions.get((c['id'],c['vendedor']),('0.00',0))
  if is_internal_admin(actor):
   with self.store.connect() as db:
    value['accesosTablero']=[{'email':e,'nombre':n,'habilitado':bool(a),'revision':r or 0} for e,n,a,r in db.execute('SELECT u.email,u.name,a.enabled,a.revision FROM users u LEFT JOIN crm_dashboard_access a ON a.email=u.email AND a.company=? WHERE u.active=1 AND u.email NOT IN (SELECT email FROM app_internal_admins) ORDER BY u.name',(company,))]
  return value
 def add_seller(self,data,actor):
  if not is_internal_admin(actor):raise PermissionError('Solo Sistemas da de alta vendedores con acceso.')
  company=data.get('empresa');self.scope(actor,company);email=str(data.get('email','')).strip().lower();co=self.cm.company(company,actor)
  with self.store.atomic() as db:
   if db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():raise ValueError('El usuario ya existe; asigna su empresa desde Accesos comerciales.')
   self.store.manage_user({'email':email,'name':data.get('nombre'),'role':'ventas','password':data.get('password'),'active':True},actor)
   self.cm.save_access({'email':email,'empresas':[company],'sucursales':co['sucursales'],'cajas':[],'acciones':[],'revision':0},actor);self.cm.audit(db,actor,company,'vendedor_creado',{'email':email})
  return {'ok':True}
 def commission(self,data,actor):
  if actor['role'] not in MANAGERS:raise PermissionError('Las comisiones son privadas para Gerencia y Superadministrador.')
  company=data.get('empresa');self.scope(actor,company);customer=data.get('cliente');seller=data.get('vendedor');rate=amount(data.get('porcentaje'))
  if rate>100 or rate!=Decimal(money(rate)):raise ValueError('El porcentaje debe estar entre 0 y 100 con hasta dos decimales.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');self.cm.customer(db,customer,company,actor);assignment=db.execute('SELECT seller FROM cm_customer_assignments WHERE customer=?',(customer,)).fetchone()
   if not assignment or assignment[0]!=seller:raise ValueError('Sistemas debe asignar primero el cliente al vendedor seleccionado.')
   old=db.execute('SELECT revision FROM crm_commissions WHERE company=? AND customer=? AND seller=?',(company,customer,seller)).fetchone()
   if data.get('revision',0)!=(old[0] if old else 0):raise Conflict('La comisión cambió. Actualiza antes de guardar.')
   db.execute('INSERT INTO crm_commissions VALUES(?,?,?,?,1) ON CONFLICT(company,customer,seller) DO UPDATE SET percentage=excluded.percentage,revision=crm_commissions.revision+1',(company,customer,seller,money(rate)))
   # La bitácora general no expone porcentajes a otros perfiles.
   self.cm.audit(db,actor,company,'comision_configurada',{'cliente':customer,'vendedor':seller})
  return {'ok':True}
 def insight_allowed(self,actor,company):
  if actor['role'] in MANAGERS:return True
  with self.store.connect() as db:return bool(db.execute('SELECT 1 FROM crm_dashboard_access WHERE company=? AND email=? AND enabled=1',(company,actor['email'])).fetchone())
 def grant_dashboard(self,data,actor):
  if not is_internal_admin(actor):raise PermissionError('Solo Sistemas autoriza el tablero mensual.')
  company=data.get('empresa');self.scope(actor,company);email=data.get('email');enabled=data.get('habilitado')
  if type(enabled) is not bool:raise ValueError('Indica si se habilita el acceso.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');user=db.execute('SELECT role FROM users WHERE email=? AND active=1 AND email NOT IN (SELECT email FROM app_internal_admins)',(email,)).fetchone()
   if not user or company not in self.cm.access({'email':email})['empresas']:raise ValueError('El usuario debe estar activo y tener acceso comercial a la empresa.')
   old=db.execute('SELECT revision FROM crm_dashboard_access WHERE company=? AND email=?',(company,email)).fetchone()
   if data.get('revision',0)!=(old[0] if old else 0):raise Conflict('El acceso cambió.')
   db.execute('INSERT INTO crm_dashboard_access VALUES(?,?,?,1) ON CONFLICT(company,email) DO UPDATE SET enabled=excluded.enabled,revision=crm_dashboard_access.revision+1',(company,email,int(enabled)));self.cm.audit(db,actor,company,'tablero_autorizado',{'email':email,'habilitado':enabled})
  return {'ok':True}
 def month(self,value):
  if not isinstance(value,str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',value):raise ValueError('Selecciona mes y año.')
  return value
 def plans(self,query,actor):
  company=int(query.get('empresa','0'));self.scope(actor,company)
  if not self.insight_allowed(actor,company):raise PermissionError('Sistemas no ha autorizado tu acceso al tablero mensual.')
  month=self.month(query.get('mes'));selected=query.get('vendedor','');rows=[]
  if selected and actor['role'] not in MANAGERS and selected!=actor['email']:raise PermissionError('Solo Gerencia y Sistemas consultan otras carteras.')
  with self.store.connect() as db:
   for id,customer,seller,kind,revision,payload in db.execute('SELECT id,customer,seller,kind,revision,payload FROM crm_plans WHERE company=? AND month=?',(company,month)):
    assignment=db.execute('SELECT seller FROM cm_customer_assignments WHERE customer=?',(customer,)).fetchone() if customer else None;seller=assignment[0] if assignment else seller
    if actor['role'] not in MANAGERS and seller!=actor['email'] or selected and seller!=selected:continue
    v={'id':id,'cliente':customer,'vendedor':seller,'tipo':kind,'revision':revision,**json.loads(payload)}
    if actor['role'] in MANAGERS:
     commission=db.execute('SELECT percentage FROM crm_commissions WHERE company=? AND customer=? AND seller=?',(company,customer,seller)).fetchone();v['porcentajeComision']=commission[0] if commission else '0.00';v['comisionEstimada']=money(Decimal(v['real'])*Decimal(v['porcentajeComision'])/100)
    rows.append(v)
  totals={kind:money(sum((Decimal(r['presupuesto']) for r in rows if r['tipo']==kind),Decimal(0))) for kind in ('CLIENTE','PROYECTO','PENDIENTE')};real=sum((Decimal(r['real']) for r in rows),Decimal(0));expected=Decimal(totals['CLIENTE'])+Decimal(totals['PROYECTO'])
  return {'registros':rows,'mes':month,'totales':{**totals,'real':money(real),'cierreEsperado':money(expected),'carteraTotal':money(expected+Decimal(totals['PENDIENTE'])),'cumplimiento':money(real/expected*100) if expected else '0.00'},'puedeComisiones':actor['role'] in MANAGERS}
 def save_plan(self,data,actor):
  company=data.get('empresa');self.scope(actor,company)
  if not self.insight_allowed(actor,company):raise PermissionError('Sistemas no ha autorizado la captura del tablero mensual.')
  month=self.month(data.get('mes'));kind=data.get('tipo');customer=data.get('cliente','') or '';title=text(data.get('titulo',''),250)
  if kind not in ('CLIENTE','PROYECTO','PENDIENTE') or not title or kind=='CLIENTE' and not customer:raise ValueError('Selecciona tipo, título y cliente cuando corresponda.')
  value={'titulo':title,'presupuesto':money(amount(data.get('presupuesto','0'))),'real':money(amount(data.get('real','0'))),'pago':text(data.get('pago',''),160),'pedidos':text(data.get('pedidos',''),250),'observaciones':text(data.get('observaciones',''),4000)}
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT company,month,customer,seller,kind,revision FROM crm_plans WHERE id=?',(data.get('id'),)).fetchone();seller=actor['email']
   if customer:
    self.cm.customer(db,customer,company,actor);assignment=db.execute('SELECT seller FROM cm_customer_assignments WHERE customer=?',(customer,)).fetchone();seller=assignment[0] if assignment else ''
    if not seller:raise ValueError('Asigna primero el cliente a un vendedor.')
   elif actor['role'] in MANAGERS:seller=data.get('vendedor') or actor['email']
   if old:
    if old[0:3]!=(company,month,customer) or old[4]!=kind:raise ValueError('No se cambia empresa, mes, cliente o tipo de un registro existente.')
    if actor['role'] not in MANAGERS and (seller if customer else old[3])!=actor['email']:raise PermissionError('No puedes modificar el plan de otra cartera.')
    if not customer:seller=old[3]
   if data.get('revision',0)!=(old[5] if old else 0):raise Conflict('El plan mensual cambió.')
   id=data.get('id') or secrets.token_hex(16)
   try:db.execute('INSERT INTO crm_plans VALUES(?,?,?,?,?,?,1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,revision=crm_plans.revision+1',(id,company,month,customer,seller,kind,dumps(value)))
   except sqlite3.IntegrityError:raise ValueError('El cliente ya tiene presupuesto para este mes. Edita el registro existente.')
   self.cm.audit(db,actor,company,'plan_mensual_guardado',{'id':id,'mes':month})
  return {'ok':True,'id':id}
