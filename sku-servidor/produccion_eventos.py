"""Eventos atómicos de fabricación; nunca modifica el historial del Kárdex."""
import copy,json,re,uuid
from decimal import Decimal
from comercial import dumps,fingerprint
from inventarios import dec,fmt
from operaciones_base import reserved,reserve,consume_reserve,setting
from requisiciones import Conflict,now,text
from fechas import iso_date
ACTIONS={'crear':('crear','create'),'autorizar':('autorizar','authorize'),'editar':('editar','edit'),'surtir':('surtir','materials'),'devolver-material':('surtir','materials'),'consumir':('consumir','materials'),'reproceso':('reproceso','materials'),'cargo':('costos','expense'),'perdida':('merma','expense'),'fabricar':('fabricar','manufacture'),'calidad':('calidad','quality'),'recibir':('recibir','receive'),'cerrar':('cerrar','close'),'cancelar':('cancelar','cancel')}
def mutate(p,action,data,actor):
 if action not in ACTIONS:raise ValueError('Acción de producción desconocida.')
 cap,handler=ACTIONS[action];key=data.get('clave','')
 if not isinstance(key,str) or not re.fullmatch('[A-Za-z0-9_-]{16,100}',key):raise ValueError('Falta identificador único de operación.')
 with p.store.atomic() as db:
  if action=='crear':cfg,_=p.scope(db,actor,data.get('empresa'),cap);old=None
  else:old=p.order(db,data.get('id'),actor,cap);cfg=p.config(db,old['empresa'])
  repeat=db.execute('SELECT request_hash,payload FROM pr_events WHERE client_key=?',(key,)).fetchone();digest=fingerprint({'actor':actor['email'],**data,'accion':action})
  if repeat:
   if repeat[0]!=digest:raise Conflict('La operación ya se envió con otros datos.')
   return p.public(json.loads(repeat[1])['resultado'],actor)
  if old and data.get('revision')!=old['revision']:raise Conflict('La orden cambió. Actualiza antes de continuar.')
  if old and old['estado'] in ('CERRADA','CANCELADA') and action!='cancelar':raise ValueError('La orden conserva su historial y ya no admite movimientos.')
  if old and action not in ('cancelar','cerrar') and not cfg['activa']:raise ValueError('Producción está desactivada en esta empresa.')
  if old and old['estado']=='TERMINADA' and action in ('surtir','consumir','cargo','perdida','fabricar','reproceso'):raise ValueError('La producción ya fue recibida; cierra la orden antes de emitir otra.')
  o=copy.deepcopy(old) if old else None
  if old:cfg={**old.get('parametros',cfg),**{k:cfg[k] for k in ('activa','permisos','cancelar','editarAutorizadas')}}
  if old and action not in ('cancelar','calidad','autorizar','editar') and old['estado'] in ('BORRADOR','PENDIENTE_AUTORIZACION'):raise ValueError('Autoriza primero la orden.')
  if old and action in ('surtir','consumir','cargo','perdida','fabricar') and Decimal(o['cantidadRecibida'])>=Decimal(o['cantidadPlaneada'])*(1+Decimal(cfg['toleranciaProduccion'])/100):raise ValueError('La orden ya recibió su producción; cierra o registra otra orden.')
  o,movements=globals()[handler](p,db,o,cfg,data,actor,action)
  o['revision']=(old['revision'] if old else 0)+1;o['modificado']=now();o['cantidadPendiente']=fmt(max(Decimal(0),Decimal(o['cantidadPlaneada'])-Decimal(o['cantidadRecibida'])-Decimal(o['cantidadRechazada'])));o['cantidadPendienteRecepcion']=fmt(max(Decimal(0),Decimal(o['cantidadFabricada'])-Decimal(o['cantidadRechazada'])-Decimal(o['cantidadRecibida'])));o['costoReal']=fmt(Decimal(o['costoConsumido'])+Decimal(o['costoCargos'])-Decimal(o['costoPerdidas']));o['costoUnitario']=fmt(Decimal(o['costoAsignado'])/Decimal(o['cantidadRecibida'])) if Decimal(o['cantidadRecibida']) else None
  payload={k:v for k,v in o.items() if k not in ('id','revision')};db.execute('INSERT INTO pr_orders VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,revision=excluded.revision,payload=excluded.payload',(o['id'],o['empresa'],o['sucursal'],o['estado'],o['revision'],dumps(payload)))
  result={'ok':True,'orden':o};event={'datos':data,'anterior':old,'movimientos':movements,'resultado':result};db.execute('INSERT INTO pr_events VALUES(?,?,?,?,?,?,?,?,?)',(uuid.uuid4().hex,o['id'],o['empresa'],action,key,digest,actor['email'],now(),dumps(event)));p.cm.audit(db,actor,o['empresa'],'produccion_'+action,{'id':o['id'],'folio':o['folio']});return p.public(result,actor)
def create(p,db,o,cfg,data,actor,action):
 r=p.recipe(db,data.get('receta'),data['empresa']);quantity=dec(data.get('cantidad'),True);method=data.get('metodo',cfg['metodos'][0]);pedido=data.get('pedido','')
 if not r['activo'] or r['vigencia']>now()[:10] or method not in cfg['metodos']:raise ValueError('Receta sin vigencia o método no habilitado.')
 if not cfg['subensambles'] and r.get('tipo')=='SUBENSAMBLE' or not cfg.get('terminados',True) and r.get('tipo','TERMINADO')=='TERMINADO':raise ValueError('La fabricación de este tipo de producto está desactivada para esta empresa.')
 if pedido:
  if not cfg['desdePedidos'] or not cfg['bajoPedido']:raise ValueError('La empresa no habilitó fabricación desde pedidos.')
  doc=p.cm.document(db,pedido,actor,'ventasins')
  if doc['empresa']!=data['empresa'] or doc['tipo']!='PEDIDO' or doc['estado']=='CANCELADO' or not any(l['sku']==r['producto'] for l in doc['partidas']):raise ValueError('Pedido incompatible con esta fabricación.')
 elif not cfg['manual'] or not cfg['paraStock']:raise ValueError('La empresa no habilitó órdenes manuales para inventario.')
 locations={k:data.get(k) or cfg[k] for k in ('materiasPrimas','consumo','terminado')};infos={k:p.inv.scope(actor,w,db,True) for k,w in locations.items()}
 if any(w['empresa']!=data['empresa'] for w in infos.values()) or infos['consumo']['funcion']!='PRODUCCION' or infos['terminado']['funcion'] not in ('GENERAL','PT'):raise ValueError('Revisa empresa y función de los almacenes de producción.')
 if not cfg['entreSucursales'] and len({w['sucursal'] for w in infos.values()})>1:raise ValueError('Producción entre sucursales desactivada.')
 if pedido:
  mode=data.get('seleccion','PARCIAL')
  if mode not in ('FALTANTE','COMPLETA','PARCIAL'):raise ValueError('Selecciona fabricación completa, parcial o por faltante.')
  delivered=Decimal(0)
  for payload, in db.execute("SELECT payload FROM cm_documents WHERE company=? AND state<>'CANCELADO' AND json_extract(payload,'$.tipo')='REMISION'",(data['empresa'],)):
   delivered+=sum((Decimal(l['cantidad']) for l in json.loads(payload).get('partidas',[]) if l.get('pedidoId')==pedido and l['sku']==r['producto']),Decimal(0))
  demand=max(Decimal(0),sum((Decimal(l['cantidad']) for l in doc['partidas'] if l['sku']==r['producto']),Decimal(0))-delivered)
  pending=Decimal(0)
  for payload, in db.execute("SELECT payload FROM pr_orders WHERE company=? AND state NOT IN ('CANCELADA','CERRADA') AND json_extract(payload,'$.pedido')=?",(data['empresa'],pedido)):
   previous=json.loads(payload)
   if previous['producto']==r['producto']:pending+=max(Decimal(0),Decimal(previous['cantidadPlaneada'])-Decimal(previous['cantidadRecibida'])-Decimal(previous['cantidadRechazada']))
  maximum=max(Decimal(0),demand-pending)
  if mode=='FALTANTE':
   balance=p.inv.balance(db,locations['terminado'],r['producto']);available=max(Decimal(0),Decimal(balance['cantidad'])-reserved(db,locations['terminado'],r['producto'],pedido)) if balance else Decimal(0);maximum=max(Decimal(0),maximum-available);quantity=maximum
  elif mode=='COMPLETA':quantity=maximum
  if quantity<=0:raise ValueError('El pedido ya está cubierto por existencias u órdenes de producción pendientes.')
  if quantity>maximum:raise ValueError('La cantidad supera el pendiente del pedido descontando la producción ya programada.')
 _,cost=p.explosion(db,r,quantity,locations['materiasPrimas'],cfg);row=db.execute('SELECT payload FROM cm_companies WHERE id=?',(data['empresa'],)).fetchone();company=json.loads(row[0])
 if not company.get('activa',True) or company.get('eliminada'):raise ValueError('La razón social no está activa.')
 company['logo']=setting(db,'company_logo:'+str(data['empresa']),{}).get('imagen','')
 o={'id':uuid.uuid4().hex,'empresa':data['empresa'],'sucursal':infos['consumo']['sucursal'],'emisor':company,'folio':'','estado':'BORRADOR','fecha':now(),'producto':r['producto'],'nombre':r['nombre'],'unidad':r['unidad'],'receta':r,'metodo':method,'pedido':pedido,'cantidadPlaneada':fmt(quantity),'cantidadFabricada':'0','cantidadRecibida':'0','cantidadRechazada':'0','responsable':text(data.get('responsable',actor.get('name',actor['email'])),160),'inicio':iso_date(data.get('inicio')) or now()[:10],'fin':iso_date(data.get('fin')),'observaciones':text(data.get('observaciones',''),10000),'costoEstimado':fmt(cost) if cost is not None else None,'costoConsumido':'0','costoCargos':'0','costoPerdidas':'0','costoAsignado':'0','costoRedondeo':'0','costoCargosAsignado':'0','costoPerdidasAsignadas':'0','detalleCostos':{},'parametros':{k:v for k,v in cfg.items() if k not in ('permisos','activa','revision')},'consumos':{},'etapas':{},'calidad':{},'lotes':[],'ciclos':{w['id']:w['ciclo'] for w in infos.values()},**locations}
 if o['fin'] and o['fin']<o['inicio']:raise ValueError('La terminación no puede ser anterior al inicio.')
 o['estado']='PENDIENTE_AUTORIZACION' if cfg['requiereAutorizacion'] else 'AUTORIZADA'
 if not cfg['requiereAutorizacion']:p.authorize(db,o,cfg,actor)
 return o,[]
def authorize(p,db,o,cfg,data,actor,action):
 if o['estado'] not in ('BORRADOR','PENDIENTE_AUTORIZACION'):raise ValueError('La orden ya fue autorizada.')
 p.authorize(db,o,cfg,actor);return o,[]
def edit(p,db,o,cfg,data,actor,action):
 if o['estado'] not in ('BORRADOR','PENDIENTE_AUTORIZACION') and (not cfg['editarAutorizadas'] or actor['role'] not in ('gerente','superadmin')):raise PermissionError('No puedes modificar esta orden autorizada.')
 quantity=dec(data.get('cantidad'),True)
 if quantity<Decimal(o['cantidadFabricada']) or quantity<Decimal(o['cantidadRecibida']):raise ValueError('No reduzcas el plan por debajo del avance real.')
 if not text(data.get('motivo',''),2000):raise ValueError('Indica motivo de la modificación.')
 o['cantidadPlaneada']=fmt(quantity);o['observaciones']=text(data.get('observaciones',o['observaciones']),10000)
 if o['estado'] not in ('BORRADOR','PENDIENTE_AUTORIZACION'):
  db.execute('DELETE FROM op_reservations WHERE document=? AND warehouse=?',(o['id'],o['materiasPrimas']));p.authorize(db,o,cfg,actor)
 return o,[]
def materials(p,db,o,cfg,data,actor,action):
 lines=data.get('partidas')
 if not isinstance(lines,list) or not 1<=len(lines)<=200:raise ValueError('Captura partidas reales.')
 required={l['sku']:l for l in p.required(o['receta'],Decimal(o['cantidadPlaneada']),cfg)};seen=set();movements=[]
 for line in lines:
  sku=str(line.get('sku','')).upper();m=p.material(sku);q=dec(line.get('cantidad'),True);original=line.get('componente',sku);component=required.get(original);waste=dec(line.get('merma','0'))
  if sku in seen or waste>q:raise ValueError('Producto repetido o merma mayor al consumo.')
  seen.add(sku)
  if not component or sku!=original and sku not in component['alternativos']:raise ValueError('El material no corresponde a la receta ni a sus alternativas autorizadas.')
  source=o['consumo'] if action in ('consumir','devolver-material') else o['materiasPrimas'];target=o['materiasPrimas'] if action=='devolver-material' else o['consumo']
  if action=='reproceso':
   if not cfg['reprocesos'] or actor['role'] not in ('superadmin','gerente'):raise PermissionError('Reproceso requiere configuración y autorización de Gerencia.')
   source=data.get('origen');p.location(db,source,o,actor,('MERMA','DEVOLUCIONES','CUARENTENA'))
  if action!='consumir' and source==target:raise ValueError('Origen y destino deben ser distintos; si el material ya está en Producción, registra su consumo.')
  p.location(db,source,o,actor);balance=p.inv.balance(db,source,sku)
  if not balance:raise ValueError('Faltan existencias del material '+sku)
  if action=='consumir':
   if cfg['calidadMP'] and o['calidad'].get('MP',{}).get('estado')!='APROBADO':raise ValueError('Falta aprobación de materias primas por Calidad.')
   prior=Decimal(o['consumos'].get(original,'0'));limit=Decimal(component['requerido'])*(1+Decimal(cfg['toleranciaConsumo'])/100)
   if prior+q>limit and (actor['role'] not in ('gerente','superadmin') or not data.get('autorizarAdicional') or not text(data.get('motivo',''),2000)):raise ValueError('El consumo supera la receta/tolerancia; requiere autorización y motivo.')
   kind='PRODUCCION_CONSUMO';o['consumos'][original]=fmt(prior+q)
  else:kind='PRODUCCION_REPROCESO' if action=='reproceso' else 'PRODUCCION_DEVOLUCION' if action=='devolver-material' else 'PRODUCCION_SURTIDO'
  extra={'ordenProduccion':o['id'],'reservaDocumento':o['id']};move=p.inv.post(db,source,m,-q,Decimal(balance['costo']),kind+':'+data['clave']+':'+sku,kind,actor,o['folio'],text(data.get('motivo',''),2000),extra);movements.append({'almacen':source,**move});consume_reserve(db,o['id'],source,sku,q)
  if action=='consumir':
   o['calidad'].pop('PROCESO',None);o['calidad'].pop('PT',None);o['costoConsumido']=fmt(Decimal(o['costoConsumido'])-Decimal(move['importe']))
   detail=o['detalleCostos'].setdefault(original,{'consumido':'0','asignado':'0','costoConsumido':'0','costoAsignado':'0'});detail['consumido']=fmt(Decimal(detail['consumido'])+q);detail['costoConsumido']=fmt(Decimal(detail['costoConsumido'])-Decimal(move['importe']))
   if waste:
    if not cfg['mermas'] or not cfg['merma']:raise ValueError('Configura el registro de merma y su almacén.')
    p.location(db,cfg['merma'],o,actor,('MERMA',));movement=p.inv.post(db,cfg['merma'],m,waste,Decimal(0),'produccion-merma:'+data['clave']+':'+sku,'PRODUCCION_MERMA',actor,o['folio'],text(data.get('motivo',''),2000),extra);movements.append({'almacen':cfg['merma'],**movement})
  else:
   p.location(db,target,o,actor);incoming=p.inv.post(db,target,m,q,Decimal(move['costoUnitario']),kind+'-entrada:'+data['clave']+':'+sku,kind,actor,o['folio'],text(data.get('motivo',''),2000),extra);movements.append({'almacen':target,**incoming})
   if target==o['consumo']:
    o['calidad'].pop('MP',None)
    held=db.execute('SELECT qty FROM op_reservations WHERE document=? AND warehouse=? AND sku=?',(o['id'],target,sku)).fetchone();reserve(db,o['id'],target,sku,(Decimal(held[0]) if held else Decimal(0))+q)
 o['estado']='EN_PROCESO';return o,movements

def expense(p,db,o,cfg,data,actor,action):
 value=dec(data.get('importe'),True);reason=text(data.get('motivo',''),2000)
 if not reason:raise ValueError('Indica el concepto y motivo del costo/pérdida.')
 if action=='cargo':
  if data.get('tipo') not in ('MANO_OBRA','INDIRECTOS','ADICIONAL'):raise ValueError('Selecciona mano de obra, indirectos o adicionales.')
  o['costoCargos']=fmt(Decimal(o['costoCargos'])+value)
 else:
  if actor['role'] not in ('gerente','superadmin') or not cfg['desperdicios']:raise PermissionError('La pérdida extraordinaria requiere configuración y autorización de Gerencia.')
  if value>p.pending_cost(o):raise ValueError('La pérdida supera el costo pendiente de distribuir.')
  o['costoPerdidas']=fmt(Decimal(o['costoPerdidas'])+value)
 return o,[]
def manufacture(p,db,o,cfg,data,actor,action):
 q=dec(data.get('cantidad'),True);rejected=dec(data.get('rechazado','0'));stage=data.get('etapa');maximum=Decimal(o['cantidadPlaneada'])*(1+Decimal(cfg['toleranciaProduccion'])/100)
 if rejected>q:raise ValueError('El rechazo no puede superar lo fabricado.')
 if cfg['calidadProceso'] and o['calidad'].get('PROCESO',{}).get('estado')!='APROBADO':raise ValueError('Falta aprobación de Calidad durante el proceso.')
 if (cfg['lotes'] or o['metodo']=='LOTES') and not text(data.get('lote',''),100):raise ValueError('Captura el lote de producción.')
 if o['metodo']=='ETAPAS':
  if stage not in cfg['etapas']:raise ValueError('Selecciona la etapa configurada.')
  position=cfg['etapas'].index(stage);prior=Decimal(o['etapas'].get(stage,'0'));limit=Decimal(o['etapas'].get(cfg['etapas'][position-1],'0')) if position else maximum
  if prior+q>limit:raise ValueError('La etapa supera lo disponible de la etapa anterior o el plan.')
  o['etapas'][stage]=fmt(prior+q-rejected)
  if position<len(cfg['etapas'])-1:q=Decimal(0);rejected=Decimal(0)
 if Decimal(o['cantidadFabricada'])+q>maximum:raise ValueError('La fabricación supera la cantidad/tolerancia autorizada.')
 if not cfg['parcial'] and q and q!=Decimal(o['cantidadPlaneada']):raise ValueError('Esta empresa no permite producción parcial.')
 if q and not any(Decimal(v)>0 for v in o['consumos'].values()):raise ValueError('Registra consumo real antes de fabricar.')
 if q:
  for component in p.required(o['receta'],Decimal(o['cantidadPlaneada']),cfg):
   need=Decimal(component['requerido'])*(Decimal(o['cantidadFabricada'])+q)/Decimal(o['cantidadPlaneada'])*(1-Decimal(cfg['toleranciaConsumo'])/100)
   if Decimal(o['consumos'].get(component['sku'],'0'))<need and (actor['role'] not in ('gerente','superadmin') or not data.get('autorizarRendimiento') or not text(data.get('motivo',''),2000)):raise ValueError('Falta consumo de '+component['sku']+' para la fabricación indicada; el rendimiento distinto requiere autorización y motivo.')
 if q:o['calidad'].pop('PT',None)
 o['cantidadFabricada']=fmt(Decimal(o['cantidadFabricada'])+q);o['cantidadRechazada']=fmt(Decimal(o['cantidadRechazada'])+rejected)
 o['lotes'].append({'lote':text(data.get('lote',''),100),'cantidad':fmt(q),'rechazado':fmt(rejected),'fecha':iso_date(data.get('fecha')) or now()[:10],'caducidad':iso_date(data.get('caducidad')),'etapa':stage or '', 'actor':actor['email']})
 if o['lotes'][-1]['caducidad'] and o['lotes'][-1]['caducidad']<o['lotes'][-1]['fecha']:raise ValueError('La caducidad no puede ser anterior a la fabricación.')
 movements=[]
 if rejected:
  if not cfg['mermas'] or not cfg['merma']:raise ValueError('Configura el almacén de merma para recibir el producto rechazado.')
  p.location(db,cfg['merma'],o,actor,('MERMA',));movement=p.inv.post(db,cfg['merma'],p.material(o['producto']),rejected,Decimal(0),'produccion-rechazo:'+data['clave'],'PRODUCCION_MERMA',actor,o['folio'],text(data.get('observaciones',''),4000),{'ordenProduccion':o['id'],'lote':text(data.get('lote',''),100)});movements.append({'almacen':cfg['merma'],**movement})
 o['estado']='PENDIENTE_RECEPCION' if q else 'EN_PROCESO';return o,movements

def quality(p,db,o,cfg,data,actor,action):
 checkpoint=data.get('punto');status=data.get('estado');reason=text(data.get('observaciones',''),4000)
 if checkpoint not in ('MP','PROCESO','PT') or status not in ('APROBADO','RECHAZADO','REVISION') or not reason:raise ValueError('Selecciona punto, dictamen y observaciones de Calidad.')
 o['calidad'][checkpoint]={'estado':status,'observaciones':reason,'actor':actor['email'],'fecha':now()};return o,[]
def receive(p,db,o,cfg,data,actor,action):
 q=dec(data.get('cantidad'),True);pending=Decimal(o['cantidadFabricada'])-Decimal(o['cantidadRechazada'])-Decimal(o['cantidadRecibida']);destination=data.get('destino') or (cfg['cuarentena'] if cfg['calidadPT'] else o['terminado'])
 if q>pending:raise ValueError('La recepción supera lo fabricado y no recibido.')
 if data.get('cerrarLote') is True and actor['role'] not in ('gerente','superadmin'):raise PermissionError('Sólo Gerencia puede cerrar anticipadamente la distribución de costos del lote.')
 lot=text(data.get('lote',''),100)
 if cfg['lotes'] or o['metodo']=='LOTES':
  produced=sum((Decimal(r['cantidad'])-Decimal(r['rechazado']) for r in o['lotes'] if r['lote']==lot),Decimal(0));received=sum((Decimal(json.loads(payload)['datos']['cantidad']) for payload, in db.execute("SELECT payload FROM pr_events WHERE document=? AND kind='recibir'",(o['id'],)) if json.loads(payload)['datos'].get('lote','')==lot),Decimal(0))
  if not lot or q>produced-received:raise ValueError('El lote no existe o la recepción supera lo fabricado pendiente de ese lote.')
 w=p.location(db,destination,o,actor,('GENERAL','PT','CUARENTENA'))
 if cfg['calidadPT'] and o['calidad'].get('PT',{}).get('estado')!='APROBADO' and w['funcion']!='CUARENTENA':raise ValueError('El PT sin aprobación debe recibirse en Cuarentena.')
 remaining=max(q,Decimal(o['cantidadFabricada'])-Decimal(o['cantidadRecibida'])-Decimal(o['cantidadRechazada']),Decimal(o['cantidadPlaneada'])-Decimal(o['cantidadRecibida'])-Decimal(o['cantidadRechazada']));final=data.get('cerrarLote') is True or q>=remaining;gross=Decimal(0);gross_pending=Decimal(0);required={l['sku']:Decimal(l['requerido']) for l in p.required(o['receta'],Decimal(o['cantidadPlaneada']),cfg)}
 for sku,detail in o['detalleCostos'].items():
  available_q=Decimal(detail['consumido'])-Decimal(detail['asignado']);available_cost=Decimal(detail['costoConsumido'])-Decimal(detail['costoAsignado']);expected=required[sku]*q/Decimal(o['cantidadPlaneada']);assigned_q=available_q if final else min(available_q,expected);assigned_cost=available_cost if final else available_cost*assigned_q/available_q if available_q else Decimal(0)
  gross_pending+=available_cost;gross+=assigned_cost;detail['asignado']=fmt(Decimal(detail['asignado'])+assigned_q);detail['costoAsignado']=fmt(Decimal(detail['costoAsignado'])+assigned_cost)
 extra=Decimal(o['costoCargos'])-Decimal(o['costoCargosAsignado']);extra_assigned=extra if final else extra*q/remaining;gross_pending+=extra;gross+=extra_assigned;o['costoCargosAsignado']=fmt(Decimal(o['costoCargosAsignado'])+extra_assigned)
 loss=Decimal(o['costoPerdidas'])-Decimal(o['costoPerdidasAsignadas']);assigned_loss=loss if final else min(loss,loss*gross/gross_pending) if gross_pending else Decimal(0);o['costoPerdidasAsignadas']=fmt(Decimal(o['costoPerdidasAsignadas'])+assigned_loss);allocated=max(Decimal(0),gross-assigned_loss);unit_cost=dec(fmt(allocated/q));m=p.material(o['producto'])
 move=p.inv.post(db,destination,m,q,unit_cost,'produccion-pt:'+data['clave'],'PRODUCCION_PT',actor,o['folio'],text(data.get('observaciones',''),4000),{'ordenProduccion':o['id'],'lote':text(data.get('lote',''),100)});o['costoAsignado']=fmt(Decimal(o['costoAsignado'])+allocated);o['costoRedondeo']=fmt(Decimal(o.get('costoRedondeo','0'))+Decimal(move['importe'])-allocated);o['cantidadRecibida']=fmt(Decimal(o['cantidadRecibida'])+q)
 o['estado']='TERMINADA' if Decimal(o['cantidadRecibida'])+Decimal(o['cantidadRechazada'])>=max(Decimal(o['cantidadPlaneada']),Decimal(o['cantidadFabricada'])) else 'PRODUCCION_PARCIAL'
 if cfg['cierreAutomatico'] and o['estado']=='TERMINADA' and p.pending_cost(o)<=Decimal('.000001'):o['estado']='CERRADA';db.execute('DELETE FROM op_reservations WHERE document=?',(o['id'],))
 return o,[{'almacen':destination,**move}]
def close(p,db,o,cfg,data,actor,action):
 if p.pending_cost(o)>Decimal('.000001'):raise ValueError('Quedan costos por distribuir; recibe el lote o autoriza la pérdida extraordinaria correspondiente.')
 if Decimal(o['cantidadFabricada'])-Decimal(o['cantidadRechazada'])>Decimal(o['cantidadRecibida']):raise ValueError('Queda producción fabricada pendiente de recibir.')
 if Decimal(o['cantidadRecibida'])+Decimal(o['cantidadRechazada'])<Decimal(o['cantidadPlaneada']) and (not cfg['parcial'] or not text(data.get('motivo',''),2000)):raise ValueError('El cierre parcial requiere permiso y motivo.')
 o['estado']='CERRADA';db.execute('DELETE FROM op_reservations WHERE document=?',(o['id'],));return o,[]
def cancel(p,db,o,cfg,data,actor,action):
 if not cfg['cancelar'] or o['estado']=='CANCELADA' or not text(data.get('motivo',''),2000):raise ValueError('La cancelación no está permitida o falta su motivo.')
 prior=[];movements=[]
 for payload, in db.execute('SELECT payload FROM pr_events WHERE document=? ORDER BY rowid DESC',(o['id'],)).fetchall():prior.extend(reversed(json.loads(payload).get('movimientos',[])))
 for index,m in enumerate(prior):
  w=p.inv.scope(actor,m['almacen'],db,True)
  if not w['activo'] or w['ciclo']!=m['ciclo']:raise Conflict('No se cancela producción dentro de otro ciclo de inventario.')
  material={'sku':m['sku'],'nombre':m['nombre'],'unidad':m['unidad'],'materialId':m.get('materialId')};move=p.inv.post(db,w['id'],material,-Decimal(m['cantidad']),Decimal(m['costoUnitario']),'produccion-cancelacion:'+data['clave']+':'+str(index),'PRODUCCION_CANCELACION',actor,o['folio'],text(data['motivo'],2000),{'ordenProduccion':o['id'],'movimientoOriginal':m['id'],'reservaDocumento':o['id']});movements.append({'almacen':w['id'],**move})
 o['estado']='CANCELADA';db.execute('DELETE FROM op_reservations WHERE document=?',(o['id'],));return o,movements
