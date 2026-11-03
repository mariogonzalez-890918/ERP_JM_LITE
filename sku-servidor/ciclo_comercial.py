"""Ciclo documental comercial con salidas reales y CXC existente."""
import copy,json,re,uuid,pathlib
from decimal import Decimal
from comercial import dumps,money,tax_line,fingerprint
from inventarios import dec,fmt
from operaciones_base import setting,save_setting,reserved,reserve,consume_reserve,series
from requisiciones import Conflict,now,text
from fechas import iso_date
KINDS=('REMISION','FACTURA','NOTA_CREDITO','DEVOLUCION')
class CommercialFlow:
 def __init__(self,store,cm,inv,finance,production):self.store,self.cm,self.inv,self.finance,self.production=store,cm,inv,finance,production
 def config(self,db,company):return setting(db,'commercial_flow:'+str(company),{'revision':0,'autorizarCotizaciones':False,'autorizarPedidos':False,'facturarPedido':False,'consolidarRemisiones':True,'conceptoCXC':''})
 def manager(self,actor):
  if actor['role'] not in ('superadmin','gerente'):raise PermissionError('Sólo Gerencia y Superadministrador autorizan entregas, facturas y ajustes financieros.')
 def company(self,actor,company):self.cm.module(actor,'ventasins');return self.cm.company(company,actor)
 def metadata(self,company,actor):
  self.company(actor,company)
  with self.store.connect() as db:
   cfg=self.config(db,company);warehouses=[]
   for id,c,b,active in db.execute('SELECT id,company,branch,active FROM inv_warehouses WHERE company=?',(company,)).fetchall():
    try:
     co=self.cm.company(company,actor,db=db);self.cm.branch(co,b,actor)
    except PermissionError:continue
    from almacenes_config import details
    warehouses.append({'id':id,'sucursal':b,'activo':bool(active),**details(db,id,b)})
   concepts=[{'id':id,'nombre':name} for id,name in db.execute("SELECT id,name FROM fn_concepts WHERE company=? AND book='CXC'",(company,))] if actor['role'] in ('superadmin','gerente') else []
  from fiscal_comercial import catalogs
  return {'configuracion':cfg,'almacenes':warehouses,'conceptos':concepts,'clientes':self.cm.customers(company,actor,'ventasins')['clientes'],'puedeAutorizar':actor['role'] in ('superadmin','gerente'),'fiscal':catalogs()}
 def save_config(self,data,actor):
  self.manager(actor);self.company(actor,data.get('empresa'))
  with self.store.atomic() as db:
   cfg=self.config(db,data['empresa'])
   for k in ('autorizarCotizaciones','autorizarPedidos','facturarPedido','consolidarRemisiones'):
    if type(data.get(k,cfg[k])) is not bool:raise ValueError('Configuración comercial inválida.')
    cfg[k]=data.get(k,cfg[k])
   concept=data.get('conceptoCXC',cfg['conceptoCXC'])
   if concept and not db.execute("SELECT 1 FROM fn_concepts WHERE id=? AND company=? AND book='CXC'",(concept,data['empresa'])).fetchone():raise ValueError('Selecciona un concepto CXC de la empresa.')
   cfg['conceptoCXC']=concept;return save_setting(db,'commercial_flow:'+str(data['empresa']),cfg,data.get('revision'))
 def warehouse(self,db,id,actor,company,saleable=True):
  self.company(actor,company);w=self.inv.destination(db,id)
  if w['empresa']!=company:raise ValueError('Selecciona un almacén de la misma empresa.')
  self.cm.branch(self.cm.company(company,actor,db=db),w['sucursal'],actor)
  if saleable and w['funcion'] not in ('GENERAL','PT'):raise ValueError('Sólo General o PT aprobado están disponibles para surtir ventas.')
  if actor.get('internalAdmin') is not True and 'inventarios' not in self.store.module_contract()['modules']:raise PermissionError('La instalación no tiene Inventarios habilitado.')
  return w
 def docs(self,db,company,kind):return [dict(id=id,revision=rev,**json.loads(payload)) for id,rev,payload in db.execute("SELECT id,revision,payload FROM cm_documents WHERE company=? AND channel='ventasins' AND state<>'CANCELADO' AND json_extract(payload,'$.tipo')=?",(company,kind))]
 def used(self,db,company,kind,field,source,index_field):
  totals={}
  for d in self.docs(db,company,kind):
   for l in d['partidas']:
    if l.get(field)==source:
     index=l[index_field];totals[index]=totals.get(index,Decimal(0))+Decimal(l['cantidad'])
  return totals
 def status(self,db,order):
  shipped=self.used(db,order['empresa'],'REMISION','pedidoId',order['id'],'pedidoLinea');billed=self.used(db,order['empresa'],'FACTURA','pedidoId',order['id'],'pedidoLinea');out=[]
  for i,l in enumerate(order['partidas']):out.append({**l,'linea':i,'surtido':fmt(shipped.get(i,Decimal(0))),'pendienteSurtir':fmt(max(Decimal(0),Decimal(l['cantidad'])-shipped.get(i,Decimal(0)))),'facturado':fmt(billed.get(i,Decimal(0))),'pendienteFacturar':fmt(max(Decimal(0),Decimal(l['cantidad'])-billed.get(i,Decimal(0))))})
  return out
 def order_detail(self,id,actor,w=None):
  with self.store.connect() as db:
   order=self.cm.document(db,id,actor,'ventasins')
   if order['tipo']!='PEDIDO':raise ValueError('Selecciona un pedido.')
   rows=self.status(db,order)
   if w:
    self.warehouse(db,w,actor,order['empresa'])
    for line in rows:
     product=db.execute('SELECT payload FROM cm_products WHERE sku=?',(line['sku'],)).fetchone();service=bool(product and json.loads(product[0]).get('naturaleza')=='SERVICIO');balance=self.inv.balance(db,w,line['sku']);physical=Decimal(balance['cantidad']) if balance else Decimal(0);held=reserved(db,w,line['sku'],id);available=max(Decimal(0),physical-held);line.update({'servicio':service,'fisico':fmt(physical),'reservadoOtros':fmt(held),'disponible':fmt(available),'faltante':fmt(max(Decimal(0),Decimal(line['pendienteSurtir'])-available)) if not service else '0'})
   linked=[d for kind in KINDS for d in self.docs(db,order['empresa'],kind) if any(l.get('pedidoId')==id for l in d['partidas'])]
   production=[]
   if actor['role'] in ('superadmin','gerente') and 'produccion' in actor.get('modulos',[]):production=[{'id':i,'folio':v.get('folio'),'estado':v['estado'],'cantidadPlaneada':v['cantidadPlaneada'],'cantidadRecibida':v['cantidadRecibida']} for i,p in db.execute('SELECT id,payload FROM pr_orders WHERE company=?',(order['empresa'],)) if (v:=json.loads(p)).get('pedido')==id]
   return {'pedido':order,'partidas':rows,'relacionados':linked,'produccion':production}
 def header(self,db,source,actor,kind):
  value={k:copy.deepcopy(source.get(k)) for k in ('empresa','emisor','sucursal','cliente','lista','observaciones','condiciones','moneda','tipoCambio')};value['moneda']=value['moneda'] or 'MXN';value['tipoCambio']=value['tipoCambio'] or '1';value.update({'tipo':kind,'folio':self.cm.next_number(db,source['empresa'],kind),'fecha':now(),'fechaPedido':source.get('fechaPedido',now()[:10]),'fechaEntrega':now()[:10],'estado':'PENDIENTE_PAC' if kind in ('FACTURA','NOTA_CREDITO') else 'EMITIDA','creador':actor['email'],'bloqueado':True});return value
 def persist(self,db,value,actor,data):
  for k in ('base','impuesto','total'):value[k]=money(sum((Decimal(l[k]) for l in value['partidas']),Decimal(0)))
  return self.cm.persist(db,value,actor,'ventasins','flujo_'+data['clave'],fingerprint(data))['documento']
 def line(self,original,q,**extra):return {k:copy.deepcopy(v) for k,v in original.items() if k in ('sku','nombre','unidad','nota','tipoImpuesto','impuestoId')}|tax_line(q,original['precio'],original['iva'],original.get('descuento','0'))|extra
 def mutate(self,action,data,actor):
  self.cm.module(actor,'ventasins');self.cm.company(data.get('empresa'),actor,True)
  if action not in ('reservar','confirmar-pedido'):self.manager(actor)
  with self.store.atomic() as db:
   for field in ('pedido','id','factura','remision'):
    if data.get(field):self.cm.document(db,data[field],actor,'ventasins')
   request={'_accion':action,'_actor':actor['email'],**data};repeat=self.inv.repeat(db,request)
   if repeat:return repeat
   if action=='reservar':result=self.reserve_order(db,data,actor)
   elif action=='confirmar-pedido':result=self.confirm_order(db,data,actor)
   elif action=='dictamen-presupuesto':result=self.decide_quote(db,data,actor)
   elif action=='remision':result=self.ship(db,data,actor)
   elif action=='factura':result=self.invoice(db,data,actor)
   elif action=='nota-credito':result=self.credit(db,data,actor)
   elif action=='devolucion':result=self.physical_return(db,data,actor)
   elif action=='cancelar':result=self.cancel(db,data,actor)
   else:raise ValueError('Acción comercial desconocida.')
   return self.inv.remember(db,request,result)
 def reserve_order(self,db,data,actor):
  self.cm.action(actor,'ventasins','pedidos');order=self.cm.document(db,data.get('pedido'),actor,'ventasins')
  if order['tipo']!='PEDIDO' or order['estado']=='CANCELADO' or order['empresa']!=data['empresa']:raise ValueError('Pedido no disponible.')
  if data.get('liberar') is True:
   db.execute('DELETE FROM op_reservations WHERE document=?',(order['id'],));self.cm.audit(db,actor,order['empresa'],'reserva_liberada',{'pedido':order['id']});return {'ok':True,'reservas':[]}
  w=data.get('almacen');self.warehouse(db,w,actor,order['empresa']);pending={}
  for line in self.status(db,order):pending[line['sku']]=pending.get(line['sku'],Decimal(0))+Decimal(line['pendienteSurtir'])
  db.execute('DELETE FROM op_reservations WHERE document=? AND warehouse=?',(order['id'],w));out=[]
  for sku,quantity in pending.items():
   m=self.inv.materials().get(sku)
   if not m:continue
   balance=self.inv.balance(db,w,sku);available=max(Decimal(0),Decimal(balance['cantidad'])-reserved(db,w,sku,order['id'])) if balance else Decimal(0);own=sum((Decimal(q) for q, in db.execute('SELECT qty FROM op_reservations WHERE document=? AND sku=?',(order['id'],sku))),Decimal(0));q=min(available,max(Decimal(0),quantity-own));reserve(db,order['id'],w,sku,q);out.append({'sku':sku,'reservado':fmt(q),'faltante':fmt(max(Decimal(0),quantity-own-q))})
  self.cm.audit(db,actor,order['empresa'],'pedido_reservado',{'pedido':order['id'],'almacen':w});return {'ok':True,'reservas':out}
 def confirm_order(self,db,data,actor):
  order=self.cm.document(db,data.get('pedido'),actor,'ventasins');cfg=self.config(db,order['empresa'])
  if cfg['autorizarPedidos']:self.manager(actor)
  else:self.cm.action(actor,'ventasins','pedidos')
  if order['tipo']!='PEDIDO' or order['estado']=='CANCELADO' or data.get('revision')!=order['revision'] or order['empresa']!=data['empresa']:raise Conflict('El pedido cambió o no está disponible.')
  value={**order,'confirmacion':{'actor':actor['email'],'fecha':now()}};return self.cm.persist(db,value,actor,'ventasins','','',order)
 def decide_quote(self,db,data,actor):
  quote=self.cm.document(db,data.get('id'),actor,'ventasins');status=data.get('estado');due=iso_date(data.get('vigencia'))
  if quote['tipo']!='PRESUPUESTO' or quote.get('pedidoDestino') or quote['estado']=='CANCELADO' or status not in ('APROBADO','RECHAZADO') or data.get('revision')!=quote['revision'] or quote['empresa']!=data['empresa']:raise Conflict('El presupuesto cambió o ya tiene pedido.')
  value={**quote,'estado':'RECHAZADO' if status=='RECHAZADO' else 'PRESUPUESTO','vigencia':due or quote.get('vigencia',''),'aprobacion':{'estado':status,'actor':actor['email'],'fecha':now(),'motivo':text(data.get('motivo',''),2000)}};return self.cm.persist(db,value,actor,'ventasins','','',quote)
 def ship(self,db,data,actor):
  order=self.cm.document(db,data.get('pedido'),actor,'ventasins');cfg=self.config(db,order['empresa'])
  if order['empresa']!=data['empresa'] or order['tipo']!='PEDIDO' or order['estado']=='CANCELADO':raise ValueError('Pedido no disponible para surtido.')
  if cfg['autorizarPedidos'] and not order.get('confirmacion'):raise ValueError('Gerencia debe confirmar el pedido antes de surtir.')
  if data.get('revision')!=order['revision']:raise Conflict('El pedido cambió. Actualiza el surtido.')
  selections=data.get('partidas');rows=self.status(db,order);seen=set();prepared=[];w=None;person=text(data.get('preparo',''),160);reason=text(data.get('observaciones',''),4000)
  if not person or not isinstance(selections,list) or not selections:raise ValueError('Indica quién preparó la entrega y las cantidades entregadas.')
  value=self.header(db,order,actor,'REMISION');value.update({'pedido':order['id'],'almacen':data.get('almacen',''),'preparo':person,'autorizo':actor['email'],'observaciones':reason})
  for choice in selections:
   i=choice.get('linea');q=dec(choice.get('cantidad'),True)
   if type(i) is not int or not 0<=i<len(rows) or i in seen or q>Decimal(rows[i]['pendienteSurtir']):raise ValueError('Cantidad entregada superior al pendiente o partida inválida.')
   seen.add(i);line=rows[i];product=db.execute('SELECT payload FROM cm_products WHERE sku=?',(line['sku'],)).fetchone();nature=line.get('naturaleza') or (json.loads(product[0]).get('naturaleza','PRODUCTO') if product else 'PRODUCTO');extra={'pedidoId':order['id'],'pedidoLinea':i,'naturaleza':nature}
   if nature!='SERVICIO':
    if w is None:w=self.warehouse(db,data.get('almacen'),actor,order['empresa']);self.inv.scope(actor,w['id'],db,True)
    material={'sku':line['sku'],'nombre':line['nombre'],'unidad':line['unidad'],'materialId':None};move=self.inv.post(db,w['id'],material,-q,None,'remision:'+data['clave']+':'+str(i),'REMISION_VENTA',actor,value['folio'],reason,{'pedidoId':order['id'],'reservaDocumento':order['id'],'preparo':person,'autorizo':actor['email']});consume_reserve(db,order['id'],w['id'],line['sku'],q);extra['movimiento']=move['id'];extra['ciclo']=move['ciclo']
   prepared.append(self.line(line,q,**extra))
  value['partidas']=prepared;value['pedidoFolio']=order['folio'];document=self.persist(db,value,actor,data)
  pending={}
  for line in self.status(db,order):pending[line['sku']]=pending.get(line['sku'],Decimal(0))+Decimal(line['pendienteSurtir'])
  for sku,maximum in pending.items():
   for warehouse,qty in db.execute('SELECT warehouse,qty FROM op_reservations WHERE document=? AND sku=? ORDER BY warehouse',(order['id'],sku)).fetchall():
    keep=min(maximum,Decimal(qty));reserve(db,order['id'],warehouse,sku,keep);maximum-=keep
  return {'ok':True,'documento':document}
 def invoice(self,db,data,actor):
  cfg=self.config(db,data['empresa']);ids=data.get('origenes');selections=data.get('partidas')
  if not isinstance(ids,list) or not 1<=len(ids)<=100 or len(set(ids))!=len(ids):raise ValueError('Selecciona pedidos o remisiones distintos.')
  sources=[self.cm.document(db,id,actor,'ventasins') for id in ids];first=sources[0];customer=(first.get('cliente') or {}).get('id')
  if not customer:raise ValueError('Selecciona un cliente registrado con datos fiscales en el pedido.')
  if len(sources)>1 and (not cfg['consolidarRemisiones'] or any(s['tipo']!='REMISION' for s in sources)):raise ValueError('La consolidación sólo admite remisiones compatibles y habilitadas.')
  for source in sources:
   if source['empresa']!=data['empresa'] or (source.get('cliente') or {}).get('id')!=customer or source['estado']=='CANCELADO' or source.get('moneda','MXN')!=first.get('moneda','MXN') or source.get('tipoCambio','1')!=first.get('tipoCambio','1'):raise ValueError('Los documentos no pertenecen al mismo cliente, empresa, moneda y tipo de cambio.')
   if source['tipo'] not in ('PEDIDO','REMISION') or source['tipo']=='PEDIDO' and not cfg['facturarPedido']:raise ValueError('La empresa no permite facturar directamente este pedido.')
  from fiscal_comercial import validate
  current=self.cm.customer(db,customer,data['empresa'],actor,'ventasins');fiscal=validate({**current,**data.get('fiscal',{})},data)
  value=self.header(db,first,actor,'FACTURA')
  if fiscal['moneda']!=value['moneda'] or Decimal(fiscal['tipoCambio'])!=Decimal(value['tipoCambio']):raise ValueError('La moneda y tipo de cambio deben coincidir con los documentos de origen.')
  value.update({'cliente':{**current,**fiscal},'fiscal':fiscal,'estadoTimbrado':'PENDIENTE_PAC','origenes':ids,'origenFolios':[s['folio'] for s in sources],'vencimiento':iso_date(data.get('vencimiento')) or now()[:10],'partidas':[]})
  if value['vencimiento']<now()[:10]:raise ValueError('El vencimiento no puede ser anterior a la emisión.')
  choices=selections if isinstance(selections,list) else [{'origen':s['id'],'linea':i,'cantidad':l['cantidad']} for s in sources for i,l in enumerate(s['partidas'])]
  mapped={s['id']:s for s in sources};used_local={};seen=set()
  for choice in choices:
   source=mapped.get(choice.get('origen'));i=choice.get('linea');q=dec(choice.get('cantidad'),True)
   if not source or type(i) is not int or not 0<=i<len(source['partidas']) or (source['id'],i) in seen:raise ValueError('Partida de origen inválida o repetida.')
   seen.add((source['id'],i));line=source['partidas'][i];pedido=source['id'] if source['tipo']=='PEDIDO' else line['pedidoId'];index=i if source['tipo']=='PEDIDO' else line['pedidoLinea'];order=self.cm.document(db,pedido,actor,'ventasins');billed=self.used(db,data['empresa'],'FACTURA','pedidoId',pedido,'pedidoLinea');prior=self.used(db,data['empresa'],'FACTURA','origenDocumento',source['id'],'origenLinea');local=used_local.get((pedido,index),Decimal(0));remaining=Decimal(order['partidas'][index]['cantidad'])-billed.get(index,Decimal(0))-local
   if q>remaining or q>Decimal(line['cantidad'])-prior.get(i,Decimal(0)):raise ValueError('La cantidad ya fue facturada o supera el pendiente del documento.')
   used_local[(pedido,index)]=local+q;value['partidas'].append(self.line(line,q,pedidoId=pedido,pedidoLinea=index,origenDocumento=source['id'],origenLinea=i,naturaleza=line.get('naturaleza','PRODUCTO')))
  if not value['partidas']:raise ValueError('No hay cantidades pendientes de facturar.')
  doc=self.persist(db,value,actor,data);account=''
  if Decimal(doc['total'])>0:
   result=self.finance.account({'empresa':doc['empresa'],'libro':'CXC','tercero':customer,'referencia':doc['folio'],'fecha':doc['fecha'][:10],'vencimiento':doc['vencimiento'],'moneda':doc['moneda'],'importe':doc['total'],'baseComision':doc['base'],'concepto':data.get('concepto') or cfg['conceptoCXC'],'tipoDocumento':'FACTURA'},actor,invoice=doc);account=result['id']
  updated={**doc,'cuenta':account};doc=self.cm.persist(db,updated,actor,'ventasins','','',doc)['documento'];return {'ok':True,'documento':doc,'saldo':doc['total']}
 def credit(self,db,data,actor):
  invoice=self.cm.document(db,data.get('factura'),actor,'ventasins');reason=text(data.get('motivo',''),2000)
  if invoice['tipo']!='FACTURA' or invoice['estado']=='CANCELADO' or invoice['empresa']!=data['empresa'] or not reason:raise ValueError('Selecciona factura vigente y motivo de la nota de crédito.')
  used=self.used(db,invoice['empresa'],'NOTA_CREDITO','facturaId',invoice['id'],'facturaLinea');lines=[];seen=set()
  for choice in data.get('partidas',[]):
   i=choice.get('linea');q=dec(choice.get('cantidad'),True)
   if type(i) is not int or not 0<=i<len(invoice['partidas']) or i in seen or q>Decimal(invoice['partidas'][i]['cantidad'])-used.get(i,Decimal(0)):raise ValueError('La nota excede la cantidad facturada pendiente de acreditar.')
   seen.add(i);line=invoice['partidas'][i];lines.append(self.line(line,q,facturaId=invoice['id'],facturaLinea=i,pedidoId=line['pedidoId'],pedidoLinea=line['pedidoLinea']))
  if not lines:raise ValueError('Selecciona partidas para acreditar.')
  value=self.header(db,invoice,actor,'NOTA_CREDITO');value.update({'factura':invoice['id'],'partidas':lines,'observaciones':reason,'estadoTimbrado':'PENDIENTE_PAC'});doc=self.persist(db,value,actor,data)
  if invoice.get('cuenta') and Decimal(doc['total'])>0:
   payment=uuid.uuid4().hex;db.execute('INSERT INTO fn_payments VALUES(?,?,?,?,?,?,?,0,?,?,?,?)',(payment,invoice['cuenta'],'CREDITO',doc['total'],now()[:10],doc['folio'],'NOTA_CREDITO','credito_'+doc['id'],fingerprint(data),actor['email'],now()));db.execute('UPDATE fn_accounts SET revision=revision+1 WHERE id=?',(invoice['cuenta'],));doc=self.cm.persist(db,{**doc,'pagoCredito':payment,'cuenta':invoice['cuenta']},actor,'ventasins','','',doc)['documento']
  self.cm.audit(db,actor,doc['empresa'],'nota_credito_emitida',{'id':doc['id'],'factura':invoice['id']});return {'ok':True,'documento':doc}
 def physical_return(self,db,data,actor):
  source=self.cm.document(db,data.get('remision'),actor,'ventasins');reason=text(data.get('motivo',''),2000);condition=data.get('condicion');w=self.warehouse(db,data.get('almacen'),actor,data['empresa'],False);self.inv.scope(actor,w['id'],db,True)
  if source['tipo']!='REMISION' or source['estado']=='CANCELADO' or source['empresa']!=data['empresa'] or not reason or condition not in ('APROBADO','REVISION','RECHAZADO'):raise ValueError('Selecciona remisión vigente, condición y motivo de devolución.')
  if condition!='APROBADO' and w['funcion'] not in ('CUARENTENA','DEVOLUCIONES','MERMA'):raise ValueError('Una devolución sin aprobación debe ir a Cuarentena, Devoluciones o Merma.')
  if condition=='APROBADO' and w['funcion'] not in ('PT','GENERAL'):raise ValueError('La devolución aprobada debe recibirse en General o PT.')
  used=self.used(db,data['empresa'],'DEVOLUCION','remisionId',source['id'],'remisionLinea');value=self.header(db,source,actor,'DEVOLUCION');value.update({'remision':source['id'],'almacen':w['id'],'observaciones':reason,'condicion':condition,'autorizo':actor['email'],'partidas':[]});seen=set()
  for choice in data.get('partidas',[]):
   i=choice.get('linea');q=dec(choice.get('cantidad'),True)
   if type(i) is not int or not 0<=i<len(source['partidas']) or i in seen or q>Decimal(source['partidas'][i]['cantidad'])-used.get(i,Decimal(0)):raise ValueError('La devolución supera lo entregado y no devuelto.')
   seen.add(i);line=source['partidas'][i]
   if not line.get('movimiento'):raise ValueError('Un servicio no tiene devolución física de inventario.')
   row=db.execute('SELECT warehouse,payload FROM inv_ledger WHERE id=?',(line['movimiento'],)).fetchone();original=json.loads(row[1]);material={'sku':line['sku'],'nombre':line['nombre'],'unidad':line['unidad'],'materialId':None};move=self.inv.post(db,w['id'],material,q,Decimal(original['costoUnitario']),'devolucion-cliente:'+data['clave']+':'+str(i),'DEVOLUCION_CLIENTE',actor,value['folio'],reason,{'remisionId':source['id'],'movimientoOriginal':line['movimiento']});value['partidas'].append(self.line(line,q,remisionId=source['id'],remisionLinea=i,pedidoId=line['pedidoId'],pedidoLinea=line['pedidoLinea'],movimiento=move['id'],ciclo=move['ciclo']))
  if not value['partidas']:raise ValueError('Selecciona cantidades recibidas físicamente.')
  return {'ok':True,'documento':self.persist(db,value,actor,data)}
 def cancel(self,db,data,actor):
  doc=self.cm.document(db,data.get('id'),actor,'ventasins');reason=text(data.get('motivo',''),2000)
  if doc['tipo'] not in KINDS or doc['estado']=='CANCELADO' or doc['empresa']!=data['empresa'] or doc['revision']!=data.get('revision') or not reason:raise Conflict('El documento cambió, ya está cancelado o falta el motivo.')
  if doc['tipo']=='FACTURA':
   if any(d.get('factura')==doc['id'] for d in self.docs(db,doc['empresa'],'NOTA_CREDITO')):raise ValueError('Cancela primero las notas de crédito relacionadas.')
   if doc.get('cuenta'):
    account=self.finance.row(db,doc['cuenta'],actor);self.finance.cancel({'cuenta':doc['cuenta'],'revision':account['revision'],'motivo':reason},actor,linked=True)
  elif doc['tipo']=='NOTA_CREDITO':
   if doc.get('pagoCredito'):db.execute('UPDATE fn_payments SET cancelled=1 WHERE id=?',(doc['pagoCredito'],));db.execute('UPDATE fn_accounts SET revision=revision+1 WHERE id=?',(doc.get('cuenta'),))
  else:
   if doc['tipo']=='REMISION':
    if any(any(l.get('origenDocumento')==doc['id'] for l in invoice['partidas']) for invoice in self.docs(db,doc['empresa'],'FACTURA')):raise ValueError('Cancela primero las facturas relacionadas.')
    if any(r.get('remision')==doc['id'] for r in self.docs(db,doc['empresa'],'DEVOLUCION')):raise ValueError('Cancela primero las devoluciones físicas relacionadas.')
   for index,line in reversed(list(enumerate(doc['partidas']))):
    if not line.get('movimiento'):continue
    row=db.execute('SELECT warehouse,payload FROM inv_ledger WHERE id=?',(line['movimiento'],)).fetchone();original=json.loads(row[1]);w=self.inv.scope(actor,row[0],db,True)
    if not w['activo'] or original['ciclo']!=w['ciclo']:raise Conflict('El almacén cambió de ciclo; no se revierte el movimiento histórico.')
    material={'sku':line['sku'],'nombre':line['nombre'],'unidad':line['unidad'],'materialId':None};self.inv.post(db,w['id'],material,-Decimal(original['cantidad']),Decimal(original['costoUnitario']),'cancelacion-comercial:'+data['clave']+':'+str(index),'CANCELACION_COMERCIAL',actor,doc['folio'],reason,{'movimientoOriginal':line['movimiento']})
  value={**doc,'estado':'CANCELADO','cancelacion':{'motivo':reason,'actor':actor['email'],'fecha':now()}}
  return self.cm.persist(db,value,actor,'ventasins','','',doc)
 def list(self,q,actor):
  company=int(q.get('empresa',0));result=self.cm.documents(company,actor,'ventasins',q)
  for d in result['documentos']:
   if d['tipo']=='PEDIDO':
    with self.store.connect() as db:
     lines=self.status(db,d);pending=sum(Decimal(l['pendienteSurtir']) for l in lines);delivered=sum(Decimal(l['surtido']) for l in lines);d['surtidoEstado']='SURTIDO_COMPLETO' if not pending else 'PARCIALMENTE_SURTIDO' if delivered else 'CONFIRMADO' if not self.config(db,company)['autorizarPedidos'] or d.get('confirmacion') else 'PENDIENTE_AUTORIZACION'
   if d['tipo']=='FACTURA':d.update(self.balance(d,actor))
  if q.get('surtidoEstado'):result['documentos']=[d for d in result['documentos'] if d.get('surtidoEstado')==q['surtidoEstado']]
  if q.get('estadoCobro'):result['documentos']=[d for d in result['documentos'] if d.get('estadoCobro')==q['estadoCobro']]
  if q.get('tipo'):result['documentos']=[d for d in result['documentos'] if d['tipo']==q['tipo']]
  if q.get('pendienteFacturar'):result['documentos']=[d for d in result['documentos'] if d['estado']!='CANCELADO' and d['tipo'] in ('PEDIDO','REMISION') and any(Decimal(l['pendienteFacturar'])>0 for l in self.document_detail(d['id'],actor)['pendientesFacturar'])]
  if q.get('almacen'):result['documentos']=[d for d in result['documentos'] if d.get('almacen')==q['almacen']]
  result['cantidad']=len(result['documentos']);result['totales']={k:money(sum((Decimal(d[k]) for d in result['documentos'] if d['estado']!='CANCELADO'),Decimal(0))) for k in ('base','impuesto','total')}
  return result
 def balance(self,doc,actor):
  if not doc.get('cuenta'):return {'saldo':'0.00','pagos':[],'estadoCobro':'PAGADA'}
  with self.store.connect() as db:
   amount=db.execute('SELECT amount,revision,cancelled FROM fn_accounts WHERE id=?',(doc['cuenta'],)).fetchone()
   rows=[{'id':id,'tipo':kind,'importe':value,'fecha':date,'referencia':reference,'metodo':method,'cancelado':bool(cancelled),'folio':setting(db,'payment_folio:'+id,'REC-'+id.upper())} for id,kind,value,date,reference,method,cancelled in db.execute('SELECT id,kind,amount,date,reference,method,cancelled FROM fn_payments WHERE account=? ORDER BY rowid',(doc['cuenta'],))]
  applied=sum((Decimal(r['importe'])*(1 if r['tipo'] in ('ABONO','CREDITO') else -1) for r in rows if not r['cancelado']),Decimal(0));balance=Decimal(amount[0])-applied if amount else Decimal(0)
  if doc['estado']=='CANCELADO' or amount and amount[2]:return {'revisionCuenta':amount[1] if amount else 0,'saldo':'0.00','pagos':rows,'estadoCobro':'CANCELADA'}
  return {'revisionCuenta':amount[1] if amount else 0,'saldo':money(balance),'pagos':rows,'estadoCobro':'A_FAVOR' if balance<0 else 'PAGADA' if balance==0 else 'VENCIDA' if doc.get('vencimiento',now()[:10])<now()[:10] else 'PARCIAL' if applied else 'PENDIENTE'}
 def document_detail(self,id,actor):
  with self.store.connect() as db:
   doc=self.cm.document(db,id,actor,'ventasins');result={'documento':doc};company=doc['empresa']
   if doc['tipo'] in ('PEDIDO','REMISION'):
    prior=self.used(db,company,'FACTURA','origenDocumento',id,'origenLinea');lines=[]
    for i,line in enumerate(doc['partidas']):
     order=id if doc['tipo']=='PEDIDO' else line['pedidoId'];index=i if doc['tipo']=='PEDIDO' else line['pedidoLinea'];source=self.cm.document(db,order,actor,'ventasins');billed=self.used(db,company,'FACTURA','pedidoId',order,'pedidoLinea')
     pending=max(Decimal(0),min(Decimal(line['cantidad'])-prior.get(i,Decimal(0)),Decimal(source['partidas'][index]['cantidad'])-billed.get(index,Decimal(0))))
     lines.append({**line,'linea':i,'pendienteFacturar':fmt(pending)})
    result['pendientesFacturar']=lines
   for kind,field,index_field,key,label in [('NOTA_CREDITO','facturaId','facturaLinea','pendientesAcreditar','pendienteAcreditar'),('DEVOLUCION','remisionId','remisionLinea','pendientesDevolver','pendienteDevolver')]:
    if doc['tipo']!=('FACTURA' if kind=='NOTA_CREDITO' else 'REMISION'):continue
    used=self.used(db,company,kind,field,id,index_field);result[key]=[{**line,'linea':i,label:fmt(max(Decimal(0),Decimal(line['cantidad'])-used.get(i,Decimal(0))))} for i,line in enumerate(doc['partidas'])]
   if doc['tipo']=='FACTURA':result.update(self.balance(doc,actor))
   return result
 def cancel_payment(self,data,actor):
  self.manager(actor)
  with self.store.atomic() as db:
   doc=self.cm.document(db,data.get('factura'),actor,'ventasins')
   if doc['tipo']!='FACTURA' or doc['empresa']!=data.get('empresa') or doc['estado']=='CANCELADO' or not doc.get('cuenta'):raise ValueError('Selecciona una factura vigente de esta empresa.')
   account=self.finance.row(db,doc['cuenta'],actor)
   if not any(p['id']==data.get('pago') for p in account['pagos']):raise ValueError('El pago no pertenece a esta factura.')
   if data.get('revisionCuenta')!=account['revision']:raise Conflict('La cuenta cambió; actualiza antes de cancelar el pago.')
   return self.finance.cancel({'cuenta':doc['cuenta'],'pago':data['pago'],'revision':account['revision'],'motivo':data.get('motivo','')},actor)
 def pay(self,data,actor):
  self.manager(actor)
  with self.store.atomic() as db:
   doc=self.cm.document(db,data.get('factura'),actor,'ventasins')
   if doc['tipo']!='FACTURA' or doc['empresa']!=data['empresa'] or doc['estado']=='CANCELADO' or not doc.get('cuenta'):raise ValueError('La factura no tiene una cuenta activa por cobrar.')
   account=self.finance.row(db,doc['cuenta'],actor);result=self.finance.payment({**{k:data[k] for k in ('clave','importe','fecha','metodo','referencia')},'tipo':data.get('tipo','ABONO'),'cuenta':doc['cuenta'],'revision':data.get('revisionCuenta',account['revision'])},actor);result['factura']=doc['id'];return result
