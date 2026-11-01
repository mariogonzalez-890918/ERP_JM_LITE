"""CXP/CXC por empresa, cargos y pagos parciales con trazabilidad e idempotencia."""
import hashlib,json,secrets,sqlite3
from decimal import Decimal
from comercial import amount,money,dumps
from fechas import iso_date
from requisiciones import Conflict,now,text

def cash(value):
 result=amount(value)
 if result!=Decimal(money(result)):raise ValueError('El importe debe tener hasta dos decimales.')
 return result

class Finance:
 def __init__(self,store,cm,po):
  self.store,self.cm,self.po=store,cm,po
  with store.connect() as db:
   db.executescript('''CREATE TABLE IF NOT EXISTS fn_concepts(id TEXT PRIMARY KEY,company INTEGER NOT NULL,book TEXT NOT NULL,name TEXT NOT NULL,revision INTEGER NOT NULL,UNIQUE(company,book,name));
   CREATE TABLE IF NOT EXISTS fn_accounts(id TEXT PRIMARY KEY,company INTEGER NOT NULL,book TEXT NOT NULL,party TEXT NOT NULL,reference TEXT NOT NULL,issued TEXT NOT NULL,due TEXT NOT NULL,currency TEXT NOT NULL,amount TEXT NOT NULL,cancelled INTEGER NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL,UNIQUE(company,book,party,reference));
   CREATE TABLE IF NOT EXISTS fn_payments(id TEXT PRIMARY KEY,account TEXT NOT NULL,kind TEXT NOT NULL,amount TEXT NOT NULL,date TEXT NOT NULL,reference TEXT NOT NULL,method TEXT NOT NULL,cancelled INTEGER NOT NULL,client_key TEXT NOT NULL UNIQUE,request_hash TEXT NOT NULL,actor TEXT NOT NULL,created TEXT NOT NULL);
   CREATE INDEX IF NOT EXISTS fn_company_book ON fn_accounts(company,book);''')
 def scope(self,actor,company,book,write=False):
  if book not in ('CXP','CXC'):raise ValueError('Selecciona CXP o CXC.')
  if book=='CXP':self.po.scope(actor,company)
  else:self.cm.module(actor,'ventasins');self.cm.company(company,actor)
  if actor['role'] not in ('superadmin','gerente','compras') or book=='CXC' and actor['role']=='compras':raise PermissionError('Solo Gerencia/Superadministrador operan CXC; Compras también opera CXP.')
 def parties(self,actor,company,book):
  return self.po.vendors(company,actor)['proveedores'] if book=='CXP' else self.cm.customers(company,actor,'ventasins')['clientes']
 def metadata(self,query,actor):
  company=int(query.get('empresa','0'));book=query.get('libro','CXP');self.scope(actor,company,book)
  with self.store.connect() as db:concepts=[{'id':i,'nombre':n,'revision':r} for i,n,r in db.execute('SELECT id,name,revision FROM fn_concepts WHERE company=? AND book=? ORDER BY name',(company,book))]
  sources=[]
  if book=='CXP':
   with self.store.connect() as db:
    for id,payload in db.execute("SELECT id,payload FROM po_moves WHERE kind='COMPRA' AND json_extract(payload,'$.empresa')=?",(company,)):
     v=json.loads(payload);sources.append({'id':id,'tercero':v['proveedorId'],'referencia':v['referencia'] or v['folio'],'importe':v['total'],'fecha':v['fecha']})
  return {'terceros':self.parties(actor,company,book),'conceptos':concepts,'compras':sources,'monedas':['MXN','USD','EUR'],'puedeCancelar':actor['role'] in ('superadmin','gerente')}
 def concept(self,data,actor):
  company=data.get('empresa');book=data.get('libro');self.scope(actor,company,book,True);name=text(data.get('nombre',''),160)
  if not name:raise ValueError('Indica el nombre del concepto.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');id=data.get('id') or secrets.token_hex(16);old=db.execute('SELECT company,book,revision FROM fn_concepts WHERE id=?',(id,)).fetchone()
   if old and old[:2]!=(company,book):raise PermissionError('Concepto de otra empresa.')
   if data.get('revision',0)!=(old[2] if old else 0):raise Conflict('El concepto cambió.')
   try:db.execute('INSERT INTO fn_concepts VALUES(?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET name=excluded.name,revision=fn_concepts.revision+1',(id,company,book,name))
   except sqlite3.IntegrityError:raise ValueError('Ya existe ese concepto.')
   self.cm.audit(db,actor,company,'concepto_financiero',{'id':id,'libro':book})
  return {'ok':True,'id':id}
 def row(self,db,id,actor):
  row=db.execute('SELECT id,company,book,party,reference,issued,due,currency,amount,cancelled,revision,payload FROM fn_accounts WHERE id=?',(id,)).fetchone()
  if not row:raise ValueError('Cuenta no disponible.')
  v=dict(zip(('id','empresa','libro','tercero','referencia','fecha','vencimiento','moneda','importe','cancelada','revision','datos'),row));self.scope(actor,v['empresa'],v['libro']);v['datos']=json.loads(v['datos'])
  v['pagos']=[dict(zip(('id','tipo','importe','fecha','referencia','metodo','cancelado','actor','creado'),r)) for r in db.execute('SELECT id,kind,amount,date,reference,method,cancelled,actor,created FROM fn_payments WHERE account=? ORDER BY rowid',(id,))]
  applied=sum((Decimal(p['importe'])*(1 if p['tipo']=='ABONO' else -1) for p in v['pagos'] if not p['cancelado']),Decimal(0));balance=Decimal(v['importe'])-applied
  v.update({'aplicado':money(applied),'saldo':money(balance),'estado':'CANCELADA' if v['cancelada'] else 'PAGADA' if balance==0 else 'VENCIDA' if v['vencimiento']<now()[:10] else 'PARCIAL' if applied else 'PENDIENTE'})
  return v
 def list(self,query,actor):
  company=int(query.get('empresa','0'));book=query.get('libro','CXP');self.scope(actor,company,book);rows=[];totals={}
  with self.store.connect() as db:
   for id, in db.execute('SELECT id FROM fn_accounts WHERE company=? AND book=? ORDER BY due,issued',(company,book)):
    v=self.row(db,id,actor)
    if query.get('tercero') and v['tercero']!=query['tercero'] or query.get('estado') and v['estado']!=query['estado']:continue
    rows.append(v)
    if not v['cancelada']:totals[v['moneda']]=totals.get(v['moneda'],Decimal(0))+Decimal(v['saldo'])
  return {'cuentas':rows,'saldosPorMoneda':{c:money(v) for c,v in totals.items()}}
 def account(self,data,actor):
  company=data.get('empresa');book=data.get('libro');self.scope(actor,company,book,True);party=data.get('tercero');reference=text(data.get('referencia',''),160);issued=iso_date(data.get('fecha'));due=iso_date(data.get('vencimiento'));currency=data.get('moneda','MXN');value=cash(data.get('importe','0'));source=data.get('compra','')
  if party not in [p['id'] for p in self.parties(actor,company,book)]:raise ValueError('Selecciona proveedor/cliente de esta empresa.')
  if not reference or not issued or not due or due<issued or currency not in ('MXN','USD','EUR') or value<=0:raise ValueError('Indica referencia, fechas válidas, moneda e importe positivo.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');concept=db.execute('SELECT name FROM fn_concepts WHERE id=? AND company=? AND book=?',(data.get('concepto'),company,book)).fetchone()
   if not concept:raise ValueError('Configura y selecciona un concepto de esta empresa.')
   if source:
    if book!='CXP':raise ValueError('La compra solo aplica a CXP.')
    row=db.execute("SELECT payload FROM po_moves WHERE id=? AND kind='COMPRA'",(source,)).fetchone();purchase=json.loads(row[0]) if row else {}
    if purchase.get('empresa')!=company or purchase.get('proveedorId')!=party:raise ValueError('La compra no pertenece al proveedor y empresa.')
    if currency!='MXN' or value!=Decimal(purchase['total']):raise ValueError('El importe de la compra ligada debe coincidir en MXN.')
    if db.execute("SELECT 1 FROM fn_accounts WHERE json_extract(payload,'$.compra')=?",(source,)).fetchone():raise ValueError('La compra ya tiene una cuenta registrada.')
   id=secrets.token_hex(16);payload={'concepto':concept[0],'compra':source,'observaciones':text(data.get('observaciones',''),4000),'actor':actor['email'],'creado':now()}
   try:db.execute('INSERT INTO fn_accounts VALUES(?,?,?,?,?,?,?,?,?,0,1,?)',(id,company,book,party,reference,issued,due,currency,money(value),dumps(payload)))
   except sqlite3.IntegrityError:raise ValueError('Ya existe esa referencia para este proveedor/cliente.')
   self.cm.audit(db,actor,company,'cuenta_registrada',{'id':id,'libro':book,'importe':money(value),'moneda':currency})
  return {'ok':True,'id':id}
 def payment(self,data,actor):
  key=text(data.get('clave',''),100);kind=data.get('tipo','ABONO');value=cash(data.get('importe','0'));date=iso_date(data.get('fecha'));method=data.get('metodo');reference=text(data.get('referencia',''),160);digest=hashlib.sha256(dumps(data).encode()).hexdigest()
  if len(key)<16 or kind not in ('ABONO','REEMBOLSO') or value<=0 or not date or not reference or method not in ('TRANSFERENCIA','EFECTIVO','TARJETA','CHEQUE','OTRO'):raise ValueError('Indica importe positivo, fecha, referencia, método y clave de operación.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');v=self.row(db,data.get('cuenta'),actor);self.scope(actor,v['empresa'],v['libro'],True)
   repeat=db.execute('SELECT id,request_hash FROM fn_payments WHERE client_key=?',(key,)).fetchone()
   if repeat:
    if repeat[1]!=digest:raise Conflict('La clave de pago ya se usó con otros datos.')
    return {'ok':True,'id':repeat[0],'repetido':True}
   if v['cancelada']:raise ValueError('La cuenta está cancelada.')
   if data.get('revision')!=v['revision']:raise Conflict('La cuenta cambió; actualiza el saldo.')
   if date<v['fecha']:raise ValueError('El pago no puede ser anterior al cargo.')
   if value>Decimal(v['saldo'] if kind=='ABONO' else v['aplicado']):raise ValueError('El pago excede el saldo o el reembolso excede lo aplicado.')
   id=secrets.token_hex(16);db.execute('INSERT INTO fn_payments VALUES(?,?,?,?,?,?,?,0,?,?,?,?)',(id,v['id'],kind,money(value),date,reference,method,key,digest,actor['email'],now()));db.execute('UPDATE fn_accounts SET revision=revision+1 WHERE id=?',(v['id'],));self.cm.audit(db,actor,v['empresa'],'pago_registrado',{'id':id,'cuenta':v['id'],'tipo':kind,'importe':money(value)})
  return {'ok':True,'id':id}
 def cancel(self,data,actor):
  if actor['role'] not in ('superadmin','gerente'):raise PermissionError('Solo Gerencia/Superadministrador cancelan cargos y pagos.')
  reason=text(data.get('motivo',''),500)
  if not reason:raise ValueError('Indica el motivo de cancelación.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');v=self.row(db,data.get('cuenta'),actor)
   if data.get('revision')!=v['revision']:raise Conflict('La cuenta cambió.')
   if v['cancelada']:raise ValueError('La cuenta ya está cancelada.')
   payment=data.get('pago')
   if payment:
    selected=next((p for p in v['pagos'] if p['id']==payment and not p['cancelado']),None)
    if not selected:raise ValueError('Pago no disponible.')
    net=Decimal(v['aplicado'])-Decimal(selected['importe'])*(1 if selected['tipo']=='ABONO' else -1)
    if not 0<=net<=Decimal(v['importe']):raise ValueError('Cancela antes los reembolsos o pagos posteriores que dependen de este movimiento.')
    db.execute('UPDATE fn_payments SET cancelled=1 WHERE id=?',(payment,))
   elif any(not p['cancelado'] for p in v['pagos']):raise ValueError('Cancela primero los movimientos de esta cuenta.')
   else:db.execute('UPDATE fn_accounts SET cancelled=1 WHERE id=?',(v['id'],))
   db.execute('UPDATE fn_accounts SET revision=revision+1 WHERE id=?',(v['id'],));self.cm.audit(db,actor,v['empresa'],'financiero_cancelado',{'cuenta':v['id'],'pago':payment,'motivo':reason})
  return {'ok':True}
