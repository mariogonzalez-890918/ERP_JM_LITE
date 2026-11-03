"""Carteras, oportunidades, seguimientos y métricas con aislamiento por vendedor."""
import json,secrets
from decimal import Decimal
from app_info import ADMIN_EMAIL,is_internal_admin
from comercial import amount,money,dumps
from fechas import iso_date
from requisiciones import Conflict,now,text
MANAGERS={'superadmin','gerente'}
STAGES=['PROSPECTO','CONTACTADO','COTIZACION','NEGOCIACION','GANADA','PERDIDA']

class CRM:
 def __init__(self,cm):
  self.cm=cm;self.store=cm.store
  with self.store.connect() as db:
   db.executescript('''CREATE TABLE IF NOT EXISTS cm_crm_items(id TEXT PRIMARY KEY,company INTEGER NOT NULL,customer TEXT NOT NULL,owner TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS cm_crm_followups(id TEXT PRIMARY KEY,opportunity TEXT NOT NULL,actor TEXT NOT NULL,created TEXT NOT NULL,payload TEXT NOT NULL);
   CREATE INDEX IF NOT EXISTS cm_crm_owner ON cm_crm_items(company,owner);''')
 def scope(self,actor,company):self.cm.module(actor,'ventasins');self.cm.company(company,actor)
 def owner(self,db,item):
  if item['cliente']:
   assigned=db.execute('SELECT seller FROM cm_customer_assignments WHERE customer=?',(item['cliente'],)).fetchone()
   return assigned[0] if assigned else ''
  return item['vendedor']
 def visible(self,db,item,actor):return actor['role'] in MANAGERS or self.owner(db,item)==actor['email']
 def item(self,db,id,actor):
  row=db.execute('SELECT company,customer,owner,revision,payload FROM cm_crm_items WHERE id=?',(id,)).fetchone()
  if not row:raise ValueError('Oportunidad no disponible.')
  self.scope(actor,row[0]);item={'id':id,'empresa':row[0],'cliente':row[1],'vendedor':row[2],'revision':row[3],**json.loads(row[4])}
  if not self.visible(db,item,actor):raise PermissionError('La oportunidad no pertenece a tu cartera.')
  item['vendedor']=self.owner(db,item);return item
 def metadata(self,actor,company):
  self.scope(actor,company)
  with self.store.connect() as db:
   sellers=[{'email':e,'nombre':n} for e,n in db.execute("SELECT email,name FROM users WHERE active=1 AND role IN ('ventas','ventasins','ventaspasteleria') ORDER BY name")] if actor['role'] in MANAGERS else []
   customers=self.cm.customers(company,actor,'ventasins')['clientes'];assignments={c:(s,r) for c,s,r in db.execute('SELECT customer,seller,revision FROM cm_customer_assignments')}
  for customer in customers:
   seller,revision=assignments.get(customer['id'],('',0));customer.update({'vendedor':seller,'revisionAsignacion':revision})
  return {'clientes':customers,'vendedores':sellers,'etapas':STAGES,'puedeAgregarClientes':actor['role'] in MANAGERS,'puedeAsignar':actor['role'] in MANAGERS,'vistaGlobal':actor['role'] in MANAGERS}
 def assign(self,data,actor):
  if actor['role'] not in MANAGERS:raise PermissionError('Solo Gerencia y Superadministrador asignan o reasignan clientes.')
  company=data.get('empresa');self.scope(actor,company);customer=data.get('cliente');seller=data.get('vendedor','')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');self.cm.customer(db,customer,company,actor)
   if not seller or not db.execute("SELECT 1 FROM users WHERE email=? AND active=1 AND role IN ('ventas','ventasins','ventaspasteleria')",(seller,)).fetchone():raise ValueError('Selecciona un vendedor activo.')
   access=self.cm.access({'email':seller})
   if company not in access['empresas']:raise ValueError('Asigna primero al vendedor acceso a esta empresa en Accesos comerciales.')
   old=db.execute('SELECT seller,revision FROM cm_customer_assignments WHERE customer=?',(customer,)).fetchone()
   if data.get('revision',0)!=(old[1] if old else 0):raise Conflict('La asignación cambió. Actualiza antes de reasignar.')
   db.execute('INSERT INTO cm_customer_assignments VALUES(?,?,?,?,?) ON CONFLICT(customer) DO UPDATE SET seller=excluded.seller,revision=excluded.revision,actor=excluded.actor,created=excluded.created',(customer,seller,(old[1] if old else 0)+1,actor['email'],now()));self.cm.audit(db,actor,company,'cliente_reasignado',{'cliente':customer,'anterior':old[0] if old else None,'vendedor':seller})
  return {'ok':True}
 def list(self,query,actor):
  company=int(query.get('empresa','0'));self.scope(actor,company);result=[];selected=query.get('vendedor','');since=iso_date(query.get('desde'));until=iso_date(query.get('hasta'))
  if selected and actor['role'] not in MANAGERS and selected!=actor['email']:raise PermissionError('Solo Gerencia y Sistemas consultan a otros vendedores.')
  if since and until and since>until:raise ValueError('Rango de fechas inválido.')
  with self.store.connect() as db:
   for id, in db.execute('SELECT id FROM cm_crm_items WHERE company=? ORDER BY rowid DESC',(company,)):
    try:item=self.item(db,id,actor)
    except PermissionError:continue
    date=item['creado'][:10]
    if selected and item['vendedor']!=selected or since and date<since or until and date>until or query.get('etapa') and item['etapa']!=query['etapa']:continue
    item['seguimientos']=[{'id':i,'actor':a,'fecha':f,**json.loads(p)} for i,a,f,p in db.execute('SELECT id,actor,created,payload FROM cm_crm_followups WHERE opportunity=? ORDER BY rowid',(id,))];result.append(item)
  return {'oportunidades':result}
 def save(self,data,actor):
  company=data.get('empresa');self.scope(actor,company);id=data.get('id');title=text(data.get('titulo',''),250);stage=data.get('etapa','PROSPECTO');customer=data.get('cliente','') or ''
  if not title or stage not in STAGES:raise ValueError('Indica oportunidad y etapa válida.')
  value={'titulo':title,'etapa':stage,'importe':money(amount(data.get('importe','0'))),'contacto':text(data.get('contacto',''),250),'observaciones':text(data.get('observaciones',''),4000),'proximoSeguimiento':iso_date(data.get('proximoSeguimiento'))}
  value['sku']=text(data.get('sku',''),80)
  if value['sku'] and value['sku'] not in {p['sku'] for p in self.cm.products(company,actor,'ventasins')['productos']}:raise ValueError('Selecciona un SKU de ventas disponible para esta empresa.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');old=self.item(db,id,actor) if id else None
   if old and old['empresa']!=company:raise PermissionError('Empresa de oportunidad no disponible.')
   if old and old['cliente']!=customer:raise ValueError('No se cambia el cliente de una oportunidad. Crea otra para conservar la trazabilidad.')
   if data.get('revision',0)!=(old['revision'] if old else 0):raise Conflict('La oportunidad cambió.')
   if customer:self.cm.customer(db,customer,company,actor)
   if old and old['etapa'] in ('GANADA','PERDIDA'):raise ValueError('Una oportunidad cerrada conserva su historial.')
   value.update({'creado':old['creado'] if old else now(),'actualizado':now()});owner=old['vendedor'] if old else actor['email']
   if id:db.execute('UPDATE cm_crm_items SET revision=revision+1,payload=? WHERE id=?',(dumps(value),id))
   else:id=secrets.token_hex(16);db.execute('INSERT INTO cm_crm_items VALUES(?,?,?,?,1,?)',(id,company,customer,owner,dumps(value)))
   self.cm.audit(db,actor,company,'oportunidad_guardada',{'id':id,'etapa':stage})
  return {'ok':True,'id':id}
 def follow(self,data,actor):
  note=text(data.get('nota',''),4000);kind=data.get('tipo','NOTA');date=iso_date(data.get('proximoSeguimiento'))
  if not note or kind not in ('NOTA','LLAMADA','VISITA','CORREO','REUNION'):raise ValueError('Indica tipo y nota del seguimiento. No se envían correos automáticamente.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');item=self.item(db,data.get('id'),actor)
   if item['revision']!=data.get('revision'):raise Conflict('La oportunidad cambió.')
   value={k:v for k,v in item.items() if k not in ('id','empresa','cliente','vendedor','revision')};value['proximoSeguimiento']=date;value['actualizado']=now()
   db.execute('INSERT INTO cm_crm_followups VALUES(?,?,?,?,?)',(secrets.token_hex(16),item['id'],actor['email'],now(),dumps({'tipo':kind,'nota':note})));db.execute('UPDATE cm_crm_items SET revision=revision+1,payload=? WHERE id=?',(dumps(value),item['id']));self.cm.audit(db,actor,item['empresa'],'seguimiento_registrado',{'id':item['id']})
  return {'ok':True}
 def dashboard(self,query,actor):
  company=int(query.get('empresa','0'));opportunities=self.list(query,actor)['oportunidades'];selected=query.get('vendedor','');filters={k:v for k,v in query.items() if k in ('desde','hasta')};orders=self.cm.documents(company,actor,'ventasins',filters)['documentos'];paid=[]
  with self.store.connect() as db:
   def seller(doc):
    customer=(doc.get('cliente') or {}).get('id');row=db.execute('SELECT seller FROM cm_customer_assignments WHERE customer=?',(customer,)).fetchone() if customer else None
    return row[0] if row else doc['creador']
   if selected:orders=[d for d in orders if seller(d)==selected]
   if 'expendios' in actor.get('modulos',[]):
    paid=[d for d in self.cm.documents(company,actor,'expendios',filters)['documentos'] if d['estado']=='PAGADA' and (not selected or seller(d)==selected)]
  live=[d for d in orders if d['estado']!='CANCELADO'];today=now()[:10]
  return {'prospectos':len(opportunities),'ganadas':sum(o['etapa']=='GANADA' for o in opportunities),'pedidos':sum(d['tipo']=='PEDIDO' for d in live),'presupuestos':sum(d['tipo']=='PRESUPUESTO' for d in live),'importePedidos':money(sum((Decimal(d['total']) for d in live if d['tipo']=='PEDIDO'),Decimal(0))),'ventasCobradasPDV':money(sum((Decimal(d['total']) for d in paid),Decimal(0))),'carteraAbierta':money(sum((Decimal(o['importe']) for o in opportunities if o['etapa'] not in ('GANADA','PERDIDA')),Decimal(0))),'seguimientosPendientes':sum(bool(o.get('proximoSeguimiento')) and o['proximoSeguimiento']<=today and o['etapa'] not in ('GANADA','PERDIDA') for o in opportunities),'alcance':'Todos los vendedores' if actor['role'] in MANAGERS and not selected else selected or actor['email']}
