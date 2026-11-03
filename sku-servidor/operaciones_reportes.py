"""Reportes derivados del historial existente, con filtros y columnas controladas."""
import json
from decimal import Decimal
from fechas import iso_date
from comercial_print import report_csv,report_xlsx,report_pdf

def export(rows,columns,q,title):
 selected=q.get('columnas','').split(',') if q.get('columnas') else list(columns)
 if len(set(selected))!=len(selected) or any(k not in columns for k in selected):raise ValueError('Selecciona columnas válidas para este reporte.')
 cells=[[columns[k] for k in selected],*[[r.get(k,'') for k in selected] for r in rows]]
 return cells

def production_report(p,q,actor):
 view=q.get('vista','ORDENES');start=iso_date(q.get('desde'));end=iso_date(q.get('hasta'))
 if start and end and start>end:raise ValueError('Revisa el rango de fechas.')
 with p.store.connect() as db:
  cfg,_=p.scope(db,actor,int(q.get('empresa',0)),'reportes',False);costs=actor['role']=='superadmin' or actor['role']=='gerente' and 'costos' in cfg['permisos'].get(actor['email'],__import__('produccion').DEFAULT_CAPS['gerente'])
 orders=p.list(q if view=='ORDENES' else {**q,'desde':'','hasta':''},actor)['ordenes'];rows=[]
 columns={'folio':'Folio','estado':'Estado','sucursal':'Sucursal','producto':'Producto','unidad':'Unidad','cantidadPlaneada':'Planeado','cantidadFabricada':'Fabricado','cantidadRechazada':'Rechazado','cantidadRecibida':'Recibido','cantidadPendiente':'Pendiente','inicio':'Inicio','fin':'Fin','responsable':'Responsable','pedido':'Pedido'}
 if view=='ORDENES':
  if costs:columns.update({'costoEstimado':'Estimado','costoReal':'Real','variacion':'Variación','costoUnitario':'Costo unitario','costoRedondeo':'Redondeo'})
  rows=[{**o,'variacion':str(Decimal(o.get('costoReal','0'))-Decimal(o['costoEstimado'])) if o.get('costoEstimado') is not None and costs else ''} for o in orders]
 elif view in ('MOVIMIENTOS','CONSUMOS','MERMAS','LOTES','CALIDAD'):
  columns={'folio':'Orden','fecha':'Fecha','evento':'Evento','sucursal':'Sucursal','producto':'Producto','almacen':'Almacén','sku':'SKU','cantidad':'Cantidad','unidad':'Unidad','lote':'Lote','caducidad':'Caducidad','estado':'Estado / Dictamen','observaciones':'Observaciones','actor':'Responsable'}
  if costs:columns.update({'costoUnitario':'Costo unitario','importe':'Importe'})
  with p.store.connect() as db:
   for order in orders:
    for kind,date,who,payload in db.execute('SELECT kind,created,actor,payload FROM pr_events WHERE document=? ORDER BY rowid',(order['id'],)):
     if start and date[:10]<start or end and date[:10]>end:continue
     event=json.loads(payload);data=event['datos'];base={'folio':order['folio'],'fecha':date,'evento':kind,'sucursal':order['sucursal'],'producto':order['producto'],'actor':who,'estado':order['estado'],'observaciones':data.get('observaciones') or data.get('motivo',''),'lote':data.get('lote',''),'caducidad':data.get('caducidad','')}
     if view=='LOTES':
      if kind=='fabricar' and (order['metodo']!='ETAPAS' or data.get('etapa')==order['parametros']['etapas'][-1]):rows.append({**base,'cantidad':data['cantidad'],'unidad':order['unidad'],'sku':order['producto'],'estado':'Rechazado: '+str(data.get('rechazado','0'))})
     elif view=='CALIDAD':
      if kind=='calidad':rows.append({**base,'evento':data['punto'],'estado':data['estado']})
     else:
      for movement in event.get('movimientos',[]):
       if view=='CONSUMOS' and movement['tipo']!='PRODUCCION_CONSUMO':continue
       if view=='MERMAS' and movement['tipo']!='PRODUCCION_MERMA':continue
       if q.get('almacen') and movement['almacen']!=q['almacen']:continue
       rows.append({**base,**movement,'evento':movement['tipo']})
      if view=='MERMAS' and kind=='perdida':rows.append({**base,'evento':'PERDIDA_EXTRAORDINARIA',**({'importe':data['importe']} if costs else {})})
 else:raise ValueError('Tipo de reporte de Producción inválido.')
 return export(rows,columns,q,'Producción')

def payment_report(flow,q,actor):
 start=iso_date(q.get('desde'));end=iso_date(q.get('hasta'))
 if start and end and start>end:raise ValueError('Revisa el rango de fechas.')
 rows=[]
 for doc in flow.list({**q,'tipo':'FACTURA','desde':'','hasta':''},actor)['documentos']:
  for payment in doc.get('pagos',[]):
   if start and payment['fecha']<start or end and payment['fecha']>end:continue
   if payment['tipo']=='CREDITO':continue
   rows.append({**payment,'factura':doc['folio'],'cliente':(doc.get('cliente') or {}).get('nombre',''),'moneda':doc.get('moneda','MXN'),'estado':'CANCELADO' if payment['cancelado'] else 'REGISTRADO'})
 columns={'folio':'Recibo','factura':'Factura','cliente':'Cliente','fecha':'Fecha','tipo':'Movimiento','importe':'Importe','moneda':'Moneda','metodo':'Método','referencia':'Referencia','estado':'Estado'}
 return export(rows,columns,q,'Cobros')
