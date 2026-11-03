"""Rutas del ciclo comercial. No conecta a bancos ni a PAC."""
from comercial_print import report_csv,report_xlsx,report_pdf
from operaciones_base import series
from operaciones_pdf import document_pdf
from requisiciones import now
from decimal import Decimal

def get(flow,action,q,actor):
 if action=='meta':return flow.metadata(int(q.get('empresa',0)),actor)
 if action=='documentos':return flow.list(q,actor)
 if action=='pedido':return flow.order_detail(q.get('id'),actor,q.get('almacen'))
 if action=='documento':
  return flow.document_detail(q.get('id'),actor)
 if action=='series':
  flow.manager(actor);company=int(q.get('empresa',0));flow.company(actor,company)
  with flow.store.atomic() as db:return {'series':[{'tipo':kind,**series(flow.cm,db,company,kind)} for kind in ('PRESUPUESTO','PEDIDO','REMISION','FACTURA','NOTA_CREDITO','DEVOLUCION','RECIBO_CXC')]}
 if action in ('pdf','correo','xml'):
  doc=flow.cm.get_document(q.get('id'),actor,'ventasins')
  if action=='xml':raise ValueError('No hay XML certificado: el PAC sigue pendiente de integración. No se generan timbrados simulados.')
  pdf=document_pdf(doc)
  if action=='pdf':return pdf,'application/pdf'
  from email.message import EmailMessage
  from email.policy import SMTP
  email=(doc.get('cliente') or {}).get('correo','')
  if not email:raise ValueError('Configura el correo del cliente antes de preparar el envío.')
  msg=EmailMessage(policy=SMTP);msg['To']=email;msg['Subject']=doc['tipo']+' '+doc['folio'];msg.set_content('Se adjunta '+doc['tipo']+' '+doc['folio']+'. '+doc.get('condiciones',''));msg.add_attachment(pdf,maintype='application',subtype='pdf',filename=doc['folio']+'.pdf');return msg.as_bytes(),'message/rfc822'
 if action=='recibo/pdf':
  doc=flow.cm.get_document(q.get('id'),actor,'ventasins');snapshot=flow.balance(doc,actor);payment=next((p for p in snapshot['pagos'] if p['id']==q.get('pago')),None)
  if not payment:raise ValueError('El pago no pertenece a esta factura.')
  rows=[['Factura','Recibo','Estado'],[doc['folio'],payment['folio'],'CANCELADO' if payment['cancelado'] else 'REGISTRADO'],['Fecha','Tipo / Método','Importe'],[payment['fecha'],payment['tipo']+' / '+payment['metodo'],payment['importe']],['Referencia','Saldo actual','Moneda'],[payment['referencia'],snapshot['saldo'],doc.get('moneda','MXN')],['Documento interno','Complemento de pagos',''],['No es un CFDI','Pendiente de PAC si corresponde','']]
  return document_pdf(doc,'Recibo interno '+payment['folio'],rows),'application/pdf'
 if action.startswith('reportes/'):
  if q.get('vista')=='PAGOS':
   from operaciones_reportes import payment_report
   rows=payment_report(flow,q,actor)
   if action.endswith('xlsx'):return report_xlsx(rows,'COBROS'),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
   if action.endswith('csv'):return report_csv(rows),'text/csv; charset=utf-8'
   if action.endswith('pdf'):return report_pdf(rows,'Cobros y reembolsos por factura, cliente y periodo','Registro interno; no realiza operaciones bancarias.'),'application/pdf'
  data=flow.list(q,actor);columns={'folio':'Folio','tipo':'Documento','fecha':'Fecha','cliente':'Cliente','sucursal':'Sucursal','sku':'SKU','cantidad':'Cantidad','estado':'Estado','base':'Subtotal','impuesto':'Impuestos','total':'Total','saldo':'Saldo factura','surtidoEstado':'Estado de surtido'};selected=q.get('columnas','folio,tipo,fecha,cliente,sku,cantidad,estado,base,impuesto,total,saldo').split(',')
  if not selected or any(k not in columns for k in selected):raise ValueError('Selecciona columnas válidas.')
  rows=[[columns[k] for k in selected]]
  for doc in data['documentos']:
   for line in doc['partidas']:
    value={**doc,**line,'cliente':(doc.get('cliente') or {}).get('nombre',doc.get('clienteOpcional','')),'saldo':doc.get('saldo','')};rows.append([value.get(k,'') for k in selected])
  if action.endswith('xlsx'):return report_xlsx(rows,'CICLO_COMERCIAL'),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  if action.endswith('csv'):return report_csv(rows),'text/csv; charset=utf-8'
  if action.endswith('pdf'):return report_pdf(rows,'Ciclo comercial por documento, cliente y periodo'),'application/pdf'
 raise ValueError('Opción del ciclo comercial no encontrada.')
def mutate(flow,action,data,actor):
 if action=='configuracion':return flow.save_config(data,actor)
 if action=='pago':return flow.pay(data,actor)
 if action=='cancelar-pago':return flow.cancel_payment(data,actor)
 if action=='series':
  flow.manager(actor);flow.company(actor,data.get('empresa'))
  if data.get('tipo') not in ('PRESUPUESTO','PEDIDO','REMISION','FACTURA','NOTA_CREDITO','DEVOLUCION','RECIBO_CXC'):raise ValueError('Tipo de serie inválido.')
  with flow.store.atomic() as db:return series(flow.cm,db,data['empresa'],data['tipo'],data)
 return flow.mutate(action,data,actor)
