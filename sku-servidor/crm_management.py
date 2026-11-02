"""Alta de vendedores, comisiones privadas y presupuesto mensual autorizado."""
import json,re,secrets,sqlite3
from decimal import Decimal
from crm import CRM,MANAGERS
from app_info import is_internal_admin
from comercial import amount,money,dumps
from requisiciones import Conflict,now,text
from fechas import iso_date

class CRMManagement(CRM):
 def __init__(self,cm):
  super().__init__(cm)
  with self.store.connect() as db:
   db.executescript('''CREATE TABLE IF NOT EXISTS crm_commissions(company INTEGER NOT NULL,customer TEXT NOT NULL,seller TEXT NOT NULL,percentage TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(company,customer,seller));
   CREATE TABLE IF NOT EXISTS crm_dashboard_access(company INTEGER NOT NULL,email TEXT NOT NULL,enabled INTEGER NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(company,email));
   CREATE TABLE IF NOT EXISTS crm_plans(id TEXT PRIMARY KEY,company INTEGER NOT NULL,month TEXT NOT NULL,customer TEXT NOT NULL,seller TEXT NOT NULL,kind TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL);
   CREATE UNIQUE INDEX IF NOT EXISTS crm_month_customer ON crm_plans(company,month,customer) WHERE kind='CLIENTE';''')
   if 'basis' not in [r[1] for r in db.execute('PRAGMA table_info(crm_commissions)')]:db.execute("ALTER TABLE crm_commissions ADD COLUMN basis TEXT NOT NULL DEFAULT 'FACTURADO'")
   if 'tax_basis' not in [r[1] for r in db.execute('PRAGMA table_info(crm_commissions)')]:db.execute("ALTER TABLE crm_commissions ADD COLUMN tax_basis TEXT NOT NULL DEFAULT 'NETO'")
 def metadata(self,actor,company):
  value=super().metadata(actor,company);value['vendedores']=[v for v in value['vendedores'] if company in self.cm.access({'email':v['email']})['empresas']]
  value['productos']=[{'sku':p['sku'],'nombre':p['nombre']} for p in self.cm.products(company,actor,'ventasins')['productos']]
  value.update({'puedeAgregarVendedores':is_internal_admin(actor),'puedeComisiones':actor['role'] in MANAGERS,'puedeTableroMensual':self.insight_allowed(actor,company),'puedeAutorizarTablero':is_internal_admin(actor)})
  if actor['role'] in MANAGERS:
   with self.store.connect() as db:commissions={(c,s):(p,r,b,t) for c,s,p,r,b,t in db.execute('SELECT customer,seller,percentage,revision,basis,tax_basis FROM crm_commissions WHERE company=?',(company,))}
   for c in value['clientes']:c['comision'],c['revisionComision'],c['baseComision'],c['impuestosComision']=commissions.get((c['id'],c['vendedor']),('0.00',0,'FACTURADO','NETO'))
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
  basis=data.get('base','FACTURADO');tax_basis=data.get('impuestos','NETO')
  if tax_basis not in ('NETO','BRUTO'):raise ValueError('Selecciona antes de impuestos o con impuestos.')
  if rate>100 or rate!=Decimal(money(rate)) or basis not in ('FACTURADO','COBRADO'):raise ValueError('Indica porcentaje de 0 a 100 con dos decimales y base FACTURADO o COBRADO.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');self.cm.customer(db,customer,company,actor);assignment=db.execute('SELECT seller FROM cm_customer_assignments WHERE customer=?',(customer,)).fetchone()
   if not assignment or assignment[0]!=seller:raise ValueError('Gerencia o Superadministrador deben asignar primero el cliente al vendedor seleccionado.')
   old=db.execute('SELECT revision FROM crm_commissions WHERE company=? AND customer=? AND seller=?',(company,customer,seller)).fetchone()
   if data.get('revision',0)!=(old[0] if old else 0):raise Conflict('La comisión cambió. Actualiza antes de guardar.')
   db.execute('INSERT INTO crm_commissions(company,customer,seller,percentage,revision,basis,tax_basis) VALUES(?,?,?,?,1,?,?) ON CONFLICT(company,customer,seller) DO UPDATE SET percentage=excluded.percentage,basis=excluded.basis,tax_basis=excluded.tax_basis,revision=crm_commissions.revision+1',(company,customer,seller,money(rate),basis,tax_basis))
   # La bitácora general no expone porcentajes a otros perfiles.
   self.cm.audit(db,actor,company,'comision_configurada',{'cliente':customer,'vendedor':seller})
  return {'ok':True}
 def commission_report(self,query,actor):
  if actor['role'] not in MANAGERS:raise PermissionError('Solo Gerencia y Superadministrador consultan reportes de comisiones.')
  company=int(query.get('empresa','0'));self.scope(actor,company);since=iso_date(query.get('desde'));until=iso_date(query.get('hasta'));seller=query.get('vendedor','')
  if not since or not until or since>until:raise ValueError('Selecciona un periodo válido para el reporte.')
  rows=[];totals={}
  with self.store.connect() as db:
   for id,customer,reference,issued,currency,total,payload in db.execute("SELECT id,party,reference,issued,currency,amount,payload FROM fn_accounts WHERE company=? AND book='CXC' AND cancelled=0",(company,)):
    value=json.loads(payload);rule=value.get('comision',{});email=rule.get('vendedor','')
    if not email or seller and email!=seller or value.get('tipoDocumento','FACTURA')!='FACTURA':continue
    rate=Decimal(rule.get('porcentaje','0'));basis=rule.get('base','FACTURADO');invoice_base=Decimal(total if rule.get('impuestos','NETO')=='BRUTO' else value.get('baseComision',total));paid=Decimal(0)
    for kind,payment,date in db.execute('SELECT kind,amount,date FROM fn_payments WHERE account=? AND cancelled=0',(id,)):
     if since<=date<=until:paid+=Decimal(payment)*(1 if kind=='ABONO' else -1)
    base=invoice_base if basis=='FACTURADO' and since<=issued<=until else paid*invoice_base/Decimal(total) if basis=='COBRADO' else Decimal(0)
    if not base:continue
    client=db.execute('SELECT payload FROM cm_customers WHERE id=?',(customer,)).fetchone();person=db.execute('SELECT name FROM users WHERE email=?',(email,)).fetchone();commission=Decimal(money(base*rate/100));totals[currency]=totals.get(currency,Decimal(0))+commission
    rows.append({'cuenta':id,'referencia':reference,'cliente':json.loads(client[0]).get('nombre',customer) if client else customer,'vendedor':email,'nombreVendedor':person[0] if person else email,'fechaFactura':issued,'moneda':currency,'regla':basis,'impuestos':('Con impuestos' if rule.get('impuestos','NETO')=='BRUTO' else 'Antes de impuestos'),'porcentaje':money(rate),'facturado':money(total),'cobradoPeriodo':money(paid),'baseComision':money(base),'comision':money(commission)})
  return {'registros':rows,'desde':since,'hasta':until,'totalesPorMoneda':{c:money(v) for c,v in totals.items()}}
 def commission_export(self,query,actor,format):
  from comercial_print import report_csv,report_xlsx,report_pdf
  result=self.commission_report(query,actor);keys=['referencia','cliente','nombreVendedor','fechaFactura','moneda','regla','impuestos','porcentaje','facturado','cobradoPeriodo','baseComision','comision']
  rows=[['Referencia','Cliente','Vendedor','Fecha factura','Moneda','Base','Impuestos','Porcentaje','Facturado','Cobrado periodo','Base comisión','Comisión'],*[[r[k] for k in keys] for r in result['registros']]]
  rows.extend([['TOTAL',currency,'','','','','','','','','',value] for currency,value in result['totalesPorMoneda'].items()])
  if format=='pdf':return report_pdf(rows,'ERP JM · Comisiones',subtitle=result['desde']+' a '+result['hasta']+'. Reglas históricas de CXC; cobros netos de reembolsos. Cada moneda se totaliza por separado.'),'application/pdf'
  if format=='csv':return report_csv(rows),'text/csv; charset=utf-8'
  return report_xlsx(rows,'COMISIONES'),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
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
    rows.append(v)
  totals={kind:money(sum((Decimal(r['presupuesto']) for r in rows if r['tipo']==kind),Decimal(0))) for kind in ('CLIENTE','PROYECTO','PENDIENTE')};real=sum((Decimal(r['real']) for r in rows),Decimal(0));expected=Decimal(totals['CLIENTE'])+Decimal(totals['PROYECTO'])
  return {'registros':rows,'mes':month,'totales':{**totals,'real':money(real),'cierreEsperado':money(expected),'carteraTotal':money(expected+Decimal(totals['PENDIENTE'])),'cumplimiento':money(real/expected*100) if expected else '0.00'},'puedeComisiones':False}
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
