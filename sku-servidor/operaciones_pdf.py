"""Representaciones comerciales y recibos internos; sin simulación de CFDI."""
import base64,html,io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,LongTable,TableStyle,Image

def document_pdf(doc,title=None,extra_rows=None):
 out=io.BytesIO();styles=getSampleStyleSheet();body=ParagraphStyle('small',parent=styles['Normal'],fontSize=8,leading=11);story=[]
 def para(v,style=body):return Paragraph(html.escape(str(v if v is not None else '')).replace('\n','<br/>'),style)
 def table(rows):
  t=LongTable([[para(v) for v in row] for row in rows],repeatRows=1,colWidths=[(A4[0]-64)/len(rows[0])]*len(rows[0]));t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5eef6')),('GRID',(0,0),(-1,-1),.3,colors.lightgrey),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.extend([t,Spacer(1,12)])
 issuer=doc.get('emisor') or {};logo=issuer.get('logo','')
 if logo.startswith('data:image/png;base64,'):
  im=Image(io.BytesIO(base64.b64decode(logo.split(',',1)[1])));scale=min(90/im.imageWidth,50/im.imageHeight);im.drawWidth=im.imageWidth*scale;im.drawHeight=im.imageHeight*scale;story.append(im)
 story.extend([para(issuer.get('nombre',''),styles['Heading1']),para(issuer.get('rfc','')+' · '+issuer.get('domicilio','')),para(title or (doc['tipo']+' '+doc['folio']),styles['Heading2']),para(doc.get('fecha','')+' · '+doc.get('estado','')),Spacer(1,8)])
 if doc['tipo'] in ('FACTURA','NOTA_CREDITO'):story.append(para('DOCUMENTO COMERCIAL · PENDIENTE DE TIMBRADO. No es un CFDI certificado; XML, UUID y validación definitiva pendientes del PAC.'))
 client=doc.get('cliente') or {};story.extend([para('Cliente: '+str(client.get('nombreFiscal') or client.get('nombre') or doc.get('clienteOpcional') or 'Público general')),para('RFC: '+client.get('rfc','')+' · CP fiscal: '+client.get('codigoPostalFiscal','')),Spacer(1,8)])
 if extra_rows is not None:table(extra_rows)
 else:
  table([['SKU / Descripción','Cantidad / Unidad','Precio','Descuento %','Impuesto','Importe'],*[[l['sku']+' '+l['nombre'],l['cantidad']+' '+l['unidad'],l['precio'],l.get('descuento','0'),l['impuesto'],l['total']] for l in doc['partidas']]])
  table([['Subtotal','Impuestos','Total','Moneda'],[doc.get('base',''),doc.get('impuesto',''),doc.get('total',''),doc.get('moneda') or 'MXN']])
 if doc.get('presupuestoOrigen'):story.append(para('Presupuesto origen: '+doc['presupuestoOrigen']))
 if doc.get('pedidoFolio'):story.append(para('Pedido relacionado: '+doc['pedidoFolio']))
 if doc.get('origenFolios'):story.append(para('Documentos de origen: '+', '.join(doc['origenFolios'])))
 if doc.get('vigencia'):story.append(para('Vigencia del presupuesto: '+doc['vigencia']))
 fiscal=doc.get('fiscal') or {}
 if fiscal:story.append(para('Régimen: '+fiscal['regimenFiscal']+' · Uso CFDI: '+fiscal['usoCFDI']+' · Método: '+fiscal['metodoPago']+' · Forma: '+fiscal['formaPago']+' · Tipo de cambio: '+fiscal['tipoCambio']))
 for k in ('preparo','autorizo','observaciones','condiciones'):
  if doc.get(k):story.append(para(k.capitalize()+': '+str(doc[k])))
 story.extend([Spacer(1,24),para('Entregó: __________________    Recibió: __________________    Fecha: __________________')]);SimpleDocTemplate(out,pagesize=A4,leftMargin=32,rightMargin=32,topMargin=25,bottomMargin=25).build(story);return out.getvalue()
