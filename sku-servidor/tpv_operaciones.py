"""Salidas TPV y preparación de globales. El PAC continúa fuera de esta etapa."""
import copy,datetime,hashlib,io,json,re
from decimal import Decimal
from comercial import dumps,fingerprint,money,tax_line
from operaciones_base import setting,save_setting,series
from requisiciones import Conflict,now,text,norm

SAT_RULE='https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/documentos2026/rmf/rmf/RMF_2026-DOF-28122025.pdf'
SAT_GUIDE='https://omawww.sat.gob.mx/tramitesyservicios/Paginas/documentos/Guia_llenado_CFDI_global.pdf'
FORMS={'EFECTIVO':'01','TRANSFERENCIA':'03','TARJETA_CREDITO':'04','TARJETA_DEBITO':'28'}

class POSOperations:
 def __init__(self,cm,inv):self.cm,self.inv,self.store=cm,inv,cm.store
 def scope(self,company,branch,actor,manage=False,db=None):
  self.cm.module(actor,'expendios')
  if manage and actor['role'] not in ('superadmin','gerente'):raise PermissionError('Solo Gerencia y Superadministrador administran la factura global y los ajustes TPV.')
  co=self.cm.company(company,actor,db=db);self.cm.branch(co,branch,actor);return co
 def config(self,db,company,branch):
  return setting(db,'tpv_branch:'+str(company)+':'+branch,{'revision':0,'almacen':str(company)+':'+branch,'facturaGlobal':False,'codigoPostal':'','regimenFiscal':''})
 def metadata(self,company,branch,actor):
  with self.store.connect() as db:
   self.scope(company,branch,actor,db=db);self.inv.sync(db);cfg=self.config(db,company,branch);warehouses=[]
   for id,active in db.execute('SELECT id,active FROM inv_warehouses WHERE company=? AND branch=?',(company,branch)):
    from almacenes_config import details
    d=details(db,id,branch)
    if d['funcion'] in ('GENERAL','PT'):warehouses.append({'id':id,'activo':bool(active),**d})
   seq=self.cm.sequence(db,company,'GLOBAL:'+branch) if actor['role'] in ('superadmin','gerente') else None
  return {'configuracion':cfg,'almacenes':warehouses,'serie':seq,'puedeConfigurar':actor['role'] in ('superadmin','gerente'),'pacDisponible':False}
 def save_config(self,data,actor):
  company=data.get('empresa');branch=data.get('sucursal')
  with self.store.atomic() as db:
   co=self.scope(company,branch,actor,True,db);old=self.config(db,company,branch);warehouse=data.get('almacen',old['almacen']);self.inv.sync(db)
   w=self.inv.destination(db,warehouse,False)
   if w['empresa']!=company or w['sucursal']!=branch or w['funcion'] not in ('GENERAL','PT'):raise ValueError('El almacén TPV debe ser General o PT de esta razón social y sucursal.')
   enabled=data.get('facturaGlobal',old['facturaGlobal']);postal=str(data.get('codigoPostal',old['codigoPostal'])).strip();regime=str(data.get('regimenFiscal',old['regimenFiscal']))
   if type(enabled) is not bool:raise ValueError('Indica si se habilita la factura global.')
   if enabled:
    if not re.fullmatch(r'[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}',co.get('rfc','').upper()):raise ValueError('Completa el RFC válido de la razón social antes de habilitar globales.')
    from fiscal_comercial import catalogs
    regimes={r['clave']:r for r in catalogs()['regimen']};person='fisica' if len(co['rfc'])==13 else 'moral'
    if not re.fullmatch(r'\d{5}',postal) or regime not in regimes or regimes[regime].get(person) is False:raise ValueError('Configura código postal de expedición y régimen fiscal compatibles con el emisor.')
   cfg=save_setting(db,'tpv_branch:'+str(company)+':'+branch,{'almacen':warehouse,'facturaGlobal':enabled,'codigoPostal':postal,'regimenFiscal':regime},data.get('revision'))
   if data.get('serie') is not None:series(self.cm,db,company,'GLOBAL:'+branch,data['serie'])
   self.cm.audit(db,actor,company,'tpv_configuracion',{'sucursal':branch,**cfg});return {'ok':True,'configuracion':cfg}
 def inventory_available(self,actor):
  if actor.get('internalAdmin') is not True and 'inventarios' not in self.store.module_contract()['modules']:raise PermissionError('El TPV requiere Inventarios habilitado para registrar la salida de mercancía.')
 def issue(self,db,doc,actor,key):
  self.scope(doc['empresa'],doc['sucursal'],actor,db=db)
  goods=[(i,l) for i,l in enumerate(doc['partidas']) if l.get('naturaleza','PRODUCTO')!='SERVICIO']
  if not goods:return {'version':1,'movimientos':[]}
  self.inventory_available(actor);self.inv.sync(db);cfg=self.config(db,doc['empresa'],doc['sucursal']);w=self.inv.destination(db,cfg['almacen'])
  if w['empresa']!=doc['empresa'] or w['sucursal']!=doc['sucursal'] or w['funcion'] not in ('GENERAL','PT'):raise ValueError('Configura el almacén General o PT de esta sucursal en Ajustes TPV.')
  cycle=db.execute('SELECT cycle FROM inv_warehouses WHERE id=?',(w['id'],)).fetchone()[0];moves=[]
  token=hashlib.sha256((actor['email']+':'+key).encode()).hexdigest()
  for i,line in goods:
   m={'sku':line['sku'],'nombre':line['nombre'],'unidad':line['unidad'],'materialId':None}
   move=self.inv.post(db,w['id'],m,-Decimal(line['cantidad']),None,'tpv:'+token+':'+str(i),'TPV_EMISION',actor,doc['folio'],'Emisión de nota TPV',{'empresa':doc['empresa'],'sucursal':doc['sucursal'],'linea':i})
   moves.append({'id':move['id'],'linea':i,'sku':line['sku'],'nombre':line['nombre'],'unidad':line['unidad'],'cantidad':line['cantidad']})
  return {'version':1,'almacen':w['id'],'ciclo':cycle,'movimientos':moves}
 def linked_global(self,db,id):
  for gid,p in db.execute("SELECT id,payload FROM cm_documents WHERE channel='expendios' AND state<>'CANCELADO' AND json_extract(payload,'$.tipo')='FACTURA_GLOBAL'"):
   if id in json.loads(p).get('notas',[]):return gid
  return None
 def reverse(self,db,doc,actor):
  if self.linked_global(db,doc['id']):raise ValueError('La nota está incluida en una factura global. Cancela primero la preparación global; si está timbrada requiere cancelación fiscal por PAC.')
  snapshot=doc.get('inventario')
  if not snapshot:return {'sinMovimientoHistorico':True} # Nunca inventar entradas de notas anteriores a esta versión.
  if not snapshot['movimientos']:return {'movimientos':[]}
  self.inventory_available(actor);w=snapshot['almacen'];row=db.execute('SELECT company,branch,cycle FROM inv_warehouses WHERE id=?',(w,)).fetchone()
  if not row or row[0]!=doc['empresa'] or row[1]!=doc['sucursal'] or row[2]!=snapshot['ciclo']:raise Conflict('El almacén cambió de ciclo. Solicita a Sistemas la conciliación; no se puede reingresar inventario histórico.')
  moves=[]
  for l in snapshot['movimientos']:
   original=db.execute('SELECT payload FROM inv_ledger WHERE id=? AND warehouse=?',(l['id'],w)).fetchone()
   entry=json.loads(original[0]) if original else {}
   if entry.get('tipo')!='TPV_EMISION' or entry.get('referencia')!=doc['folio'] or entry.get('sku')!=l['sku'] or Decimal(entry['cantidad'])!=-Decimal(l['cantidad']):raise Conflict('No coincide el movimiento original de la nota TPV.')
   m={k:l[k] for k in ('sku','nombre','unidad')}
   moves.append(self.inv.post(db,w,m,Decimal(l['cantidad']),Decimal(entry['costoUnitario']),'tpv-cancelacion:'+doc['id']+':'+str(l['linea']),'TPV_CANCELACION',actor,doc['folio'],'Regreso físico por cancelación autorizada',{'documento':doc['id'],'movimientoOriginal':l['id']}))
  return {'almacen':w,'movimientos':[m['id'] for m in moves]}
 def paid(self,data,actor):
  self.cm.action(actor,'expendios','caja')
  with self.store.atomic() as db:
   doc=self.cm.document(db,data.get('id'),actor,'expendios')
   if doc['tipo']!='VENTA' or doc['estado']!='EMITIDA':raise ValueError('Selecciona una nota emitida pendiente de cobro.')
   if doc['revision']!=data.get('revision'):raise Conflict('La nota cambió; actualiza antes de registrar el cobro.')
   self.cm.session(db,doc['sesion'],doc['empresa'],actor)
   form=data.get('formaPago');method=next((k for k,v in FORMS.items() if v==form),None)
   if not method:raise ValueError('Selecciona la forma real de pago: efectivo, transferencia, tarjeta de crédito o débito.')
   from comercial import amount
   received=amount(data.get('recibido','0')) if form=='01' else Decimal(doc['total'])
   if received<Decimal(doc['total']):raise ValueError('El importe recibido es menor al total de la nota.')
   value={**doc,'estado':'PAGADA','modo':'COBRO','pago':{'metodo':method,'formaPago':form,'recibido':money(received),'cambio':money(received-Decimal(doc['total'])),'fecha':now(),'actor':actor['email']}}
   result=self.cm.persist(db,value,actor,'expendios','','',doc);db.execute('UPDATE cm_sessions SET revision=revision+1 WHERE id=?',(doc['sesion'],));return result
 def period(self,data):
  from fechas import iso_date
  start=iso_date(data.get('desde'));end=iso_date(data.get('hasta'));period=data.get('periodicidad')
  if not start or not end or start>end or start[:7]!=end[:7]:raise ValueError('Selecciona un período dentro del mismo mes y año.')
  a,b=datetime.date.fromisoformat(start),datetime.date.fromisoformat(end)
  if end>=now()[:10]:raise ValueError('Selecciona operaciones de días cerrados; el período debe terminar antes de hoy.')
  if period not in ('01','02','04') or period=='01' and a!=b or period=='02' and (b-a).days!=6 or period=='04' and (a.day!=1 or (b+datetime.timedelta(days=1)).day!=1):raise ValueError('Selecciona diario (un día), semanal (7 días en el mismo mes) o mensual (mes completo).')
  return start,end,{'Periodicidad':period,'Meses':start[5:7],'Año':int(start[:4])}
 def global_preview(self,db,data,actor):
  company=data.get('empresa');branch=data.get('sucursal');co=self.scope(company,branch,actor,True,db);cfg=self.config(db,company,branch)
  if not cfg['facturaGlobal']:raise ValueError('Habilita Factura global en los ajustes de esta razón social y sucursal.')
  start,end,info=self.period(data);notes=[];excluded=[];lines=[];forms={}
  for id,revision,payload in db.execute("SELECT id,revision,payload FROM cm_documents WHERE company=? AND channel='expendios' ORDER BY created,id",(company,)):
   d=json.loads(payload)
   if d.get('tipo')!='VENTA' or d.get('sucursal')!=branch or not start<=d['fecha'][:10]<=end:continue
   reason=''
   customer=d.get('cliente') or {};form=d.get('pago',{}).get('formaPago') or FORMS.get(d.get('pago',{}).get('metodo'))
   if d['estado']=='CANCELADO':reason='Nota cancelada'
   elif d['estado']!='PAGADA':reason='Cobro completo pendiente de registrar'
   elif self.linked_global(db,id):reason='Ya incluida en una global vigente'
   elif d.get('facturaIndividual') or d.get('uuid') or customer.get('rfc','').strip().upper() not in ('','XAXX010101000'):reason='Cliente nominativo o factura individual; requiere revisión individual'
   elif d.get('moneda','MXN')!='MXN':reason='La preparación global admite MXN'
   elif form not in FORMS.values():reason='Falta forma real de pago (distinguir tarjeta de crédito y débito)'
   elif any(Decimal(l['iva'])<0 for l in d['partidas']):reason='Retenciones: se requiere facturación por operación'
   elif Decimal(d['total'])<=0:reason='Importe sin valor facturable'
   if not reason:
    try:
     for l in d['partidas']:self.fiscal_tax(l)
    except ValueError as e:reason=str(e)
   if reason:excluded.append({'id':id,'folio':d['folio'],'motivo':reason});continue
   notes.append({'id':id,'revision':revision,'folio':d['folio'],'fecha':d['fecha'],'total':d['total'],'formaPago':form})
   forms[form]=max(forms.get(form,Decimal(0)),Decimal(d['total']))
   for i,l in enumerate(d['partidas']):lines.append({**copy.deepcopy(l),'notaTPV':id,'folioNota':d['folio'],'lineaNota':i})
  # Hereda los límites documentales/restauración existentes; no truncar silenciosamente.
  if len(lines)>200:raise ValueError('La global supera 200 partidas. Reduce el período a un cierre diario o semanal; no se han apartado notas.')
  base=money(sum((Decimal(l['base']) for l in lines),Decimal(0)));tax=money(sum((Decimal(l['impuesto']) for l in lines),Decimal(0)));total=money(Decimal(base)+Decimal(tax))
  close=datetime.datetime.fromisoformat(end+'T23:59:59'+now()[-6:]);late=datetime.datetime.fromisoformat(now())>close+datetime.timedelta(hours=24)
  fiscal={'Version':'4.0','TipoDeComprobante':'I','Exportacion':'01','Moneda':'MXN','MetodoPago':'PUE','FormaPago':max(sorted(forms),key=lambda f:forms[f]) if forms else '', 'LugarExpedicion':cfg['codigoPostal'],'InformacionGlobal':info,'Emisor':{'Rfc':co.get('rfc','').upper(),'Nombre':co['nombre'],'RegimenFiscal':cfg['regimenFiscal']},'Receptor':{'Rfc':'XAXX010101000','Nombre':'PUBLICO EN GENERAL','DomicilioFiscalReceptor':cfg['codigoPostal'],'RegimenFiscalReceptor':'616','UsoCFDI':'S01'},'Conceptos':self.concepts(lines),'SubTotal':base,'TotalImpuestosTrasladados':tax,'Total':total,'estado':'PREPARACION_SIN_TIMBRAR'}
  review={'empresa':company,'sucursal':branch,'desde':start,'hasta':end,'notas':notes,'excluidas':excluded,'base':base,'impuesto':tax,'total':total,'fiscal':fiscal,'fueraPlazo':late,'advertencias':['Preparación comercial sin sello, UUID ni validez de CFDI. Timbrado PAC pendiente.']+(['El período supera el plazo ordinario de 24 horas desde el cierre. Revisar con el responsable fiscal; no se altera la fecha.'] if late else [])}
  review['huellaRevision']=fingerprint({'revisionConfiguracion':cfg['revision'],'revisionEmpresa':co['revision'],'revisionSerie':self.cm.sequence(db,company,'GLOBAL:'+branch)['revision'],**review})
  return review,lines,co
 def fiscal_tax(self,line):
  rate=Decimal(line['iva']);name=norm(line.get('tipoImpuesto',''))
  if rate<0:raise ValueError('Retenciones: facturación individual obligatoria')
  if name in ('IVA EXENTO','EXENTO') and rate==0:return {'Impuesto':'002','TipoFactor':'Exento'}
  if name.startswith('IVA') and rate in (0,8,16):return {'Impuesto':'002','TipoFactor':'Tasa','TasaOCuota':format(rate/100,'.6f')}
  if name.startswith('IEPS') and rate==8:return {'Impuesto':'003','TipoFactor':'Tasa','TasaOCuota':'0.080000'}
  if name=='NO OBJETO' and rate==0:return None
  raise ValueError('Impuesto ambiguo/no admitido para global: configura IVA 0/8/16, IEPS 8, IVA EXENTO o NO OBJETO')
 def concepts(self,lines):
  groups={}
  for l in lines:
   tax=self.fiscal_tax(l);key=(l['notaTPV'],dumps(tax));g=groups.setdefault(key,{'ClaveProdServ':'01010101','NoIdentificacion':l['folioNota'],'Cantidad':'1','ClaveUnidad':'ACT','Descripcion':'Venta','ObjetoImp':'02' if tax else '01','ValorUnitario':Decimal(0),'Importe':Decimal(0),'traslado':dict(tax) if tax else None,'impuesto':Decimal(0)})
   g['ValorUnitario']+=Decimal(l['base']);g['Importe']+=Decimal(l['base']);g['impuesto']+=Decimal(l['impuesto'])
  result=[]
  for g in groups.values():
   tax=g.pop('traslado');amount=g.pop('impuesto');g['ValorUnitario']=money(g['ValorUnitario']);g['Importe']=money(g['Importe'])
   if tax:
    tax['Base']=g['Importe']
    if tax['TipoFactor']!='Exento':tax['Importe']=money(amount)
    g['Traslados']=[tax]
   result.append(g)
  return result
 def preview(self,data,actor):
  with self.store.atomic() as db:return self.global_preview(db,data,actor)[0]
 def create(self,data,actor):
  key=str(data.get('clave',''));hash=fingerprint(data)
  if not re.fullmatch('[a-zA-Z0-9_-]{16,100}',key):raise ValueError('Falta clave única de preparación global.')
  with self.store.atomic() as db:
   self.scope(data.get('empresa'),data.get('sucursal'),actor,True,db)
   repeat=db.execute("SELECT id,fingerprint FROM cm_documents WHERE creator=? AND channel='expendios' AND client_key=?",(actor['email'],key)).fetchone()
   if repeat:
    if repeat[1]!=hash:raise Conflict('La clave se utilizó con otro contenido.')
    return {'ok':True,'repetido':True,'documento':self.cm.document(db,repeat[0],actor,'expendios')}
   review,lines,co=self.global_preview(db,data,actor)
   if data.get('huellaRevision')!=review['huellaRevision']:raise Conflict('Cambió el cierre o su configuración. Revisa otra vez antes de preparar la global.')
   if not lines:raise ValueError('No hay notas elegibles para la factura global.')
   if review['fueraPlazo'] and data.get('reconocerFueraPlazo') is not True:raise ValueError('Confirma la revisión con el responsable fiscal del período fuera del plazo ordinario.')
   doc={'empresa':data['empresa'],'emisor':co,'sucursal':data['sucursal'],'cliente':{'nombre':'PUBLICO EN GENERAL','rfc':'XAXX010101000'},'tipo':'FACTURA_GLOBAL','estado':'PENDIENTE_PAC','folio':self.cm.next_number(db,data['empresa'],'GLOBAL:'+data['sucursal']),'fecha':now(),'creador':actor['email'],'moneda':'MXN','tipoCambio':'1','partidas':lines,'notas':[n['id'] for n in review['notas']],'detalleNotas':review['notas'],'desde':review['desde'],'hasta':review['hasta'],'fiscal':review['fiscal'],'advertencias':review['advertencias'],'base':review['base'],'impuesto':review['impuesto'],'total':review['total']}
   return self.cm.persist(db,doc,actor,'expendios',key,hash)
 def globals(self,company,branch,actor):
  with self.store.connect() as db:
   self.scope(company,branch,actor,True,db);docs=[]
   for id,revision,payload in db.execute("SELECT id,revision,payload FROM cm_documents WHERE company=? AND channel='expendios' AND json_extract(payload,'$.tipo')='FACTURA_GLOBAL' ORDER BY created DESC",(company,)):
    value=json.loads(payload)
    if value['sucursal']==branch:docs.append({'id':id,'revision':revision,**value})
  return {'documentos':docs}
 def cancel_global(self,data,actor):
  with self.store.atomic() as db:
   d=self.cm.document(db,data.get('id'),actor,'expendios');self.scope(d['empresa'],d['sucursal'],actor,True,db)
   if d['tipo']!='FACTURA_GLOBAL' or d['estado']!='PENDIENTE_PAC' or d.get('uuid'):raise ValueError('Solo se puede cancelar aquí una preparación sin timbrar. Un CFDI requiere cancelación fiscal por PAC.')
   if d['revision']!=data.get('revision'):raise Conflict('La preparación cambió; actualiza.')
   reason=text(data.get('motivo',''),1000)
   if not reason:raise ValueError('Indica el motivo de cancelación.')
   return self.cm.persist(db,{**d,'estado':'CANCELADO','cancelacion':{'motivo':reason,'actor':actor['email'],'fecha':now()}},actor,'expendios','','',d)
 def document(self,id,actor):
  with self.store.connect() as db:
   d=self.cm.document(db,id,actor,'expendios');self.scope(d['empresa'],d['sucursal'],actor,True,db)
   if d['tipo']!='FACTURA_GLOBAL':raise ValueError('Selecciona una factura global.')
   return d
 def pdf(self,id,actor):
  from reportlab.lib import colors
  from reportlab.lib.styles import getSampleStyleSheet
  from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
  from xml.sax.saxutils import escape
  d=self.document(id,actor);styles=getSampleStyleSheet();out=io.BytesIO();story=[]
  def p(s,style='Normal'):return Paragraph(escape(str(s)),styles[style])
  story=[p('Preparación de factura global','Title'),p(d['folio']+' / '+d['estado']),p(d['emisor']['nombre']+' / '+d['sucursal']),p('Período '+d['desde']+' a '+d['hasta']),p('SIN TIMBRAR. No es un CFDI; PAC pendiente.'),Spacer(1,14)]
  f=d['fiscal'];story += [p('Receptor: PUBLICO EN GENERAL / XAXX010101000 / 616 / S01'),p('CP: '+f['LugarExpedicion']+' / PUE / Forma '+f['FormaPago']+' / Periodicidad '+f['InformacionGlobal']['Periodicidad']),Spacer(1,12)]
  rows=[[p('Nota'),p('Fecha'),p('Forma SAT'),p('Total')]]+[[p(n['folio']),p(n['fecha'][:10]),p(n['formaPago']),p(n['total'])] for n in d['detalleNotas']]
  table=Table(rows,colWidths=[190,105,85,100],repeatRows=1);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceaf5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.lightgrey),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story += [table,Spacer(1,12),p('Base '+d['base']+' / Impuestos '+d['impuesto']+' / Total '+d['total'])]
  story += [p(a) for a in d['advertencias']];SimpleDocTemplate(out,title=d['folio']).build(story);return out.getvalue()
