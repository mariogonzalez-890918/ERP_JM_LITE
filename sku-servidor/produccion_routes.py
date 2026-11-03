"""API, layouts y hoja PDF de Producción, sin dependencias fiscales externas."""
import base64,hashlib,io,json
from collections import OrderedDict
from comercial import fingerprint,dumps
from comercial_print import report_xlsx,report_csv,report_pdf
from clientes_comerciales import read_table
from requisiciones import Conflict
HEADERS=['SKU_PRODUCTO','CODIGO','RENDIMIENTO','SKU_COMPONENTE','CANTIDAD','UNIDAD','FACTOR','MERMA','SUBRECETA','ALTERNATIVOS','INSTRUCCIONES']
def get(p,action,q,actor):
 if action=='meta':return p.metadata(actor)
 if action=='recetas':return p.recipes(int(q.get('empresa',0)),actor)
 if action=='ordenes':return p.list(q,actor)
 if action=='orden':return p.detail(q.get('id'),actor)
 if action=='series':return p.series({'empresa':int(q.get('empresa',0)),'sucursal':q.get('sucursal')},actor)
 if action=='layout':
  with p.store.connect() as db:p.scope(db,actor,int(q.get('empresa',0)),'crear',False)
  return report_xlsx([HEADERS],'RECETAS'),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
 if action=='hoja/pdf':return sheet_pdf(p,q.get('id'),actor),'application/pdf'
 if action.startswith('reportes/'):
  with p.store.connect() as db:p.scope(db,actor,int(q.get('empresa',0)),'reportes',False)
  from operaciones_reportes import production_report
  rows=production_report(p,q,actor)
  if action.endswith('xlsx'):return report_xlsx(rows,'PRODUCCION'),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  if action.endswith('csv'):return report_csv(rows),'text/csv; charset=utf-8'
  if action.endswith('pdf'):return report_pdf(rows,'Producción por orden, almacén y periodo'),'application/pdf'
 raise ValueError('Opción de Producción no encontrada.')
def mutate(p,action,data,actor):
 if action=='configuracion':return p.save_config(data,actor)
 if action=='recetas':return p.save_recipe(data,actor)
 if action=='explosionado':return p.plan(data,actor)
 if action=='series':return p.series(data,actor,True)
 if action=='recetas/importar':return import_recipes(p,data,actor)
 return p.mutate(action,data,actor)
def import_recipes(p,data,actor):
 rows=read_table(data,'RECETAS')
 if not rows or rows[0]!=HEADERS:raise ValueError('Conserva los encabezados y la hoja RECETAS del layout.')
 groups=OrderedDict()
 for index,row in enumerate(rows[1:],2):
  if not any(str(v).strip() for v in row):continue
  if len(row)>len(HEADERS) and any(row[len(HEADERS):]):raise ValueError('Fila '+str(index)+': sobran columnas.')
  row=list(row)+['']*max(0,len(HEADERS)-len(row));code=str(row[1]).strip().upper()
  if not code:raise ValueError('Fila '+str(index)+': falta código de receta.')
  group=groups.setdefault(code,{'empresa':data.get('empresa'),'codigo':code,'producto':row[0],'cantidadBase':row[2],'instrucciones':row[10],'componentes':[]})
  if str(group['producto'])!=str(row[0]) or str(group['cantidadBase'])!=str(row[2]):raise ValueError('La receta tiene productos/rendimientos distintos: '+code)
  group['componentes'].append({'sku':row[3],'cantidad':row[4],'unidad':row[5],'factor':row[6] or '1','merma':row[7] or '0','subcodigo':str(row[8]).strip().upper(),'alternativos':[v.strip() for v in str(row[9]).split('|') if v.strip()]})
 if not groups:raise ValueError('El layout no contiene recetas.')
 with p.store.atomic(rollback=data.get('revisar') is True) as db:
  p.scope(db,actor,data.get('empresa'),'crear');stamp=fingerprint([[list(r) for r in db.execute('SELECT * FROM pr_recipes WHERE company=? ORDER BY id',(data['empresa'],))],p.inv.materials(),p.config(db,data['empresa'])]);file_hash=hashlib.sha256(str(data.get('contenido','')).encode()).hexdigest()
  if not data.get('revisar') and (data.get('huellaActual')!=stamp or data.get('huellaArchivo')!=file_hash):raise Conflict('Revisa el layout nuevamente; cambió el catálogo o el archivo.')
  created={};path=[]
  def create(code):
   if code in created:return created[code]
   if code in path:raise ValueError('El layout contiene recetas cíclicas.')
   path.append(code);group=groups[code]
   for line in group['componentes']:
    sub=line.pop('subcodigo','')
    if sub:
     if sub in groups:line['subreceta']=create(sub)['id']
     else:
      row=db.execute('SELECT id FROM pr_recipes WHERE company=? AND code=? ORDER BY version DESC LIMIT 1',(data['empresa'],sub)).fetchone()
      if not row:raise ValueError('Subreceta no encontrada: '+sub)
      line['subreceta']=row[0]
   created[code]=p._save_recipe(group,actor);path.pop();return created[code]
  for code in groups:create(code)
  return {'ok':True,'recetas':len(created),'versiones':[{'codigo':v['codigo'],'version':v['version']} for v in created.values()],'huellaActual':stamp,'huellaArchivo':file_hash,'revisado':data.get('revisar') is True}
def sheet_pdf(p,id,actor):
 from reportlab.lib import colors
 from reportlab.lib.pagesizes import A4
 from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
 from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image
 import html
 detail=p.detail(id,actor);o=detail['orden'];out=io.BytesIO();styles=getSampleStyleSheet();story=[]
 small=ParagraphStyle('production-small',parent=styles['Normal'],fontSize=8,leading=10)
 def paragraph(v):return Paragraph(html.escape(str(v if v is not None else 'Pendiente')),small)
 def table(rows):
  t=Table([[paragraph(v) for v in row] for row in rows],repeatRows=1,hAlign='LEFT',colWidths=[(A4[0]-64)/len(rows[0])]*len(rows[0]));t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e6eef5')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.lightgrey),('FONTSIZE',(0,0),(-1,-1),8)]));story.extend([t,Spacer(1,12)])
 logo=o.get('emisor',{}).get('logo','')
 if logo.startswith('data:image/png;base64,'):
  image=Image(io.BytesIO(base64.b64decode(logo.split(',',1)[1])));ratio=min(100/image.imageWidth,50/image.imageHeight);image.drawWidth=image.imageWidth*ratio;image.drawHeight=image.imageHeight*ratio;story.append(image)
 story.extend([Paragraph('Hoja de producción · '+html.escape(o['folio'] or 'Pendiente de autorización'),styles['Title']),paragraph(o['emisor'].get('nombre','')),paragraph('Revisión '+str(o['revision'])+' · '+o['modificado']+' · '+o['estado']),Spacer(1,12)])
 table([['Producto','Receta / versión','Método'],[o['producto']+' '+o['nombre'],o['receta']['codigo']+' / '+str(o['receta']['version']),o['metodo']]])
 table([['Planeado','Fabricado','Rechazado','Recibido','Pendiente'],[o[k] for k in ('cantidadPlaneada','cantidadFabricada','cantidadRechazada','cantidadRecibida','cantidadPendiente')]])
 story.extend([paragraph('Unidad: '+o['unidad']+' · Responsable: '+o['responsable']),paragraph('Inicio: '+o['inicio']+' · Terminación: '+o['fin']),paragraph('Pedido relacionado: '+o['pedido']),paragraph(o['receta']['instrucciones']),paragraph(o['observaciones']),Spacer(1,12)])
 table([['SKU','Requerido','Unidad','Consumo real'],*[[l['sku'],l['requerido'],l['unidadInventario'],o['consumos'].get(l['sku'],'0')] for l in p.required(o['receta'],Decimal(o['cantidadPlaneada']),p.config_for_sheet(o))]])
 if 'costoReal' in o:table([['Estimado','Real','Asignado a PT','Unitario','Redondeo'],[o.get(k) for k in ('costoEstimado','costoReal','costoAsignado','costoUnitario','costoRedondeo')]])
 rows=[['Fecha / Usuario','Evento','Almacén / SKU','Cantidad']]
 warehouses={w['id']:w['sucursal']+' / '+w.get('nombre',w['sucursal']) for w in p.inv.warehouses(actor)['almacenes']}
 for e in detail['eventos']:
  if not e['movimientos']:rows.append([e['fecha']+' '+e['actor'],e['tipo'],'',''])
  for m in e['movimientos']:rows.append([m['fecha'][:19].replace('T',' ')+' '+m['actor'],m['tipo'].replace('_',' '),warehouses.get(m['almacen'],'Almacén histórico')+' / '+m['sku'],m['cantidad']+' '+m['unidad']])
 table(rows);story.append(paragraph('Producción: __________________  Calidad: __________________  Almacén: __________________'))
 SimpleDocTemplate(out,pagesize=A4,leftMargin=32,rightMargin=32,topMargin=25,bottomMargin=25).build(story);return out.getvalue()
from decimal import Decimal
