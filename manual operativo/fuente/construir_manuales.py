"""Genera los dos manuales gráficos y anexa los flujos; requiere reportlab/pypdf/pymupdf."""
from pathlib import Path
import html,json,math,sys
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor,white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader,PdfWriter
import pymupdf
from contenido import MODULES,QUALITY_AREAS
from reportes import REPORTS
from soporte import INSTALL,COMMANDS,MAINTENANCE,COMMON_ERRORS,IMPACTS,SOURCES
ROOT=Path(__file__).resolve().parents[2];FOLDER=ROOT/'manual operativo';ASSETS=FOLDER/'recursos';TMP=ROOT/'tmp/pdfs';TMP.mkdir(parents=True,exist_ok=True)
W,H=A4;M=34;CW=W-2*M;NAVY='#123454';BLUE='#006da3';GREEN='#167a63';ORANGE='#a95612';INK='#20364b';GREY='#586c80'
STYLE={k:ParagraphStyle(k,fontName='Helvetica',fontSize=size,leading=lead,textColor=HexColor(INK),spaceAfter=0) for k,size,lead in [('body',10.1,13.2),('small',8.7,11),('table',9.2,12),('caption',8.3,10.5)]}
STYLE['head']=ParagraphStyle('head',fontName='Helvetica-Bold',fontSize=20,leading=24,textColor=HexColor(NAVY))
CHECKS=[]

def esc(s):return html.escape(str(s)).replace('\n','<br/>')
def P(text,style='body'):return Paragraph(esc(text),STYLE[style])
def para(c,text,x,y,w=CW,style='body'):
 p=P(text,style);_,h=p.wrap(w,1000);p.drawOn(c,x,y-h);return y-h
def heading(c,text,y,color=BLUE):
 c.setFont('Helvetica-Bold',11);c.setFillColor(HexColor(color));c.drawString(M,y,text);return y-10
def card(c,title,text,y,color=BLUE):
 p=P(text);_,h=p.wrap(CW-24,1000);height=h+39;c.setFillColor(HexColor('#f0f6fa'));c.setStrokeColor(HexColor('#cedde7'));c.roundRect(M,y-height,CW,height,6,fill=1,stroke=1);c.setFillColor(HexColor(color));c.setFont('Helvetica-Bold',10.4);c.drawString(M+12,y-17,title);p.drawOn(c,M+12,y-29-h);return y-height-11
def table(c,rows,y,widths=None,style='table'):
 widths=widths or [CW/len(rows[0])]*len(rows[0]);cells=[[P(v,style) for v in row] for row in rows];t=Table(cells,colWidths=widths,hAlign='LEFT');t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),HexColor('#dfeaf2')),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,HexColor('#f4f7fa')]),('GRID',(0,0),(-1,-1),.35,HexColor('#c8d5df')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]));_,h=t.wrap(CW,1000);t.drawOn(c,M,y-h);return y-h
def flow(c,items,y):
 count=len(items);gap=12;w=(CW-gap*(count-1))/count;h=38
 for i,text in enumerate(items):
  x=M+i*(w+gap);c.setFillColor(HexColor('#eaf3f9'));c.setStrokeColor(HexColor(BLUE));c.roundRect(x,y-h,w,h,5,fill=1,stroke=1);p=P(text,'small');_,ph=p.wrap(w-12,h-6);p.drawOn(c,x+6,y-(h-ph)/2-ph)
  if i<count-1:
   ax=x+w+2;ay=y-h/2;c.setStrokeColor(HexColor(BLUE));c.line(ax,ay,ax+8,ay);c.line(ax+8,ay,ax+5,ay+3);c.line(ax+8,ay,ax+5,ay-3)
 return y-h-12
def steps(c,lines,y):
 for i,line in enumerate(lines,1):
  c.setFillColor(HexColor(BLUE));c.circle(M+8,y-7,8,fill=1,stroke=0);c.setFillColor(white);c.setFont('Helvetica-Bold',9);c.drawCentredString(M+8,y-10,str(i));y=para(c,line,M+24,y,CW-24)-7
 return y
def header(c,title,section,route,owner,key):
 c.bookmarkPage(key);c.addOutlineEntry(title,key,level=0);c.setFillColor(HexColor(NAVY));c.rect(0,H-40,W,40,fill=1,stroke=0);c.setFillColor(white);c.setFont('Helvetica-Bold',10);c.drawString(M,H-24,'ERP JM | '+('TÉCNICO Y DUEÑO' if owner else 'USUARIO'));c.setFont('Helvetica',8);c.drawRightString(W-M,H-24,section)
 y=para(c,title,M,H-58,style='head')-8;y=para(c,route,M,y,style='small')-12;return y
def finish(c,key,y,owner):
 if y<28:raise ValueError(f'Contenido fuera de página: {key}, límite {y:.1f}')
 CHECKS.append({'manual':'tecnico' if owner else 'usuario','pagina':c.getPageNumber(),'seccion':key,'contenido_hasta':round(y,1)})
 c.setStrokeColor(HexColor('#d5e0e8'));c.line(M,25,W-M,25);c.setFillColor(HexColor(GREY));c.setFont('Helvetica',8);c.drawString(M,13,'Piloto ca0ce1e | 03 nov 2026 | Capturas de demostración');c.showPage()
def image(c,name,y):
 path=ASSETS/name
 if not path.exists():return card(c,'Referencia de pantalla','Accede por la ruta indicada. El menú y los botones dependen del perfil autorizado.',y)
 reader=ImageReader(str(path));iw,ih=reader.getSize();scale=min(CW/iw,220/ih);w=iw*scale;h=ih*scale;x=(W-w)/2;c.drawImage(reader,x,y-h,w,h,mask='auto');c.setStrokeColor(HexColor('#bdcbd6'));c.rect(x,y-h,w,h,stroke=1,fill=0);y-=h+5;return para(c,'Pantalla de demostración. Datos, clasificaciones y ubicaciones ilustrativos; no vienen precargados.',M,y,style='caption')-9

def module_page(c,m,owner):
 y=header(c,m['title'],'OPERACIÓN POR MÓDULO',m['route'],owner,m['id']);y=para(c,m['goal'],M,y)-10;y=flow(c,m['flow'],y);y=image(c,m['image'],y);y=steps(c,m['tech'] if owner else m['user'],y)
 y=card(c,'EFECTO EN LOS DATOS',m['effect'],y,GREEN)
 y=heading(c,'Matriz de solución y errores comunes',y)-4;y=table(c,[['Síntoma o aviso','Causa probable','Solución / responsable'],*m['errors']],y,[135,153,CW-288],style='small')-8
 y=para(c,'Control: '+m['check'],M,y,style='caption');finish(c,m['id'],y,owner)

def report_page(c,r,owner,i):
 y=header(c,r['title'],'REPORTES POR MÓDULO',r['route'],owner,'reporte-'+str(i));y=flow(c,['Definir filtros','Consultar','Abrir detalle','Exportar / conciliar'],y)
 y=card(c,'FORMATOS DISPONIBLES',r['formats'],y);y=card(c,'FILTROS Y ALCANCE',r['filters'],y);y=steps(c,r['steps'],y)
 y=card(c,'CÓMO INTERPRETARLO',r['read'],y,GREEN);y=card(c,'EJEMPLO / COMPROBACIÓN',r['example'],y,ORANGE)
 y=heading(c,'Matriz de solución del reporte',y)-4;y=table(c,[['Síntoma','Revisar','Solución'],*r['errors']],y,[135,153,CW-288],style='small')-9;y=para(c,'Permisos: '+r['access'],M,y,style='small');finish(c,'reporte-'+str(i),y,owner)

def text_page(c,title,section,rows,owner,key,extra=None):
 y=header(c,title,section,'Guía del piloto publicado; aplicar según autorización y contexto.',owner,key)
 for title,text in rows:y=card(c,title,text,y)
 if extra:
  for title,command in extra:
   y=heading(c,title,y)-3;y=para(c,command,M,y,style='small')-12
 finish(c,key,y,owner)

def quality_pages(c,owner):
 for start in range(0,15,5):
  y=header(c,f'QualityLite: áreas {start+1} a {start+5}','GUÍA DE LAS 15 ÁREAS','Calidad / Seleccionar módulo / Nuevo, consultar o exportar',owner,'calidad-areas-'+str(start));y=flow(c,['Área y formato','Captura','Evidencia / revisión','Estado e historial'],y)
  y=para(c,'La edición corresponde a Calidad/Superadministrador. Repositorio compartido por instalación; no confundir registros de calidad con movimientos físicos o financieros.',M,y)-15
  y=table(c,[['Área','Qué registrar','Funcionamiento','Error y solución'],*QUALITY_AREAS[start:start+5]],y,[110,138,142,CW-390])-14
  y=card(c,'CONTROL COMÚN','Verifica código, versión, estado, responsables y fecha de compromiso. Para Registros se requiere una versión aprobada del formato. En inspecciones/quejas, los movimientos de almacén o CXC se documentan en su módulo.',y,GREEN);finish(c,'calidad-areas-'+str(start),y,owner)

def matrix_pages(c,owner):
 for start in (0,5):
  y=header(c,'Diagnóstico y errores transversales','MATRIZ DE SOPORTE',f'Casos {start+1} a {min(start+5,len(COMMON_ERRORS))}. No reemplaza la revisión del folio original.',owner,'errores-'+str(start));y=flow(c,['Guardar evidencia','Verificar si se registró','Corregir causa','Reintento controlado'],y)
  y=table(c,[['Síntoma','Causa probable','Solución / responsable'],*COMMON_ERRORS[start:start+5]],y,[126,155,CW-281])-18
  y=card(c,'QUÉ ENVIAR A SOPORTE','Módulo, empresa/sucursal/almacén, folio, fecha y hora, acción intentada, aviso exacto y captura sin contraseñas/tokens. Indica si hubo entrega física o pago real. No repetir confirmaciones hasta consultar el estado.',y,ORANGE);finish(c,'errores-'+str(start),y,owner)
 for start in (0,9):
  y=header(c,'Qué acciones cambian stock y saldos','MATRIZ DE EFECTOS',f'Escenarios {start+1} a {min(start+9,len(IMPACTS))}. El anexo final desarrolla las rutas con números.',owner,'efectos-'+str(start));y=table(c,[['Acción','Stock','Saldo / valor','Lectura correcta'],*IMPACTS[start:start+9]],y,[143,91,100,CW-334],style='small')-14
  y=card(c,'SI CAMBIA EL ALMACÉN','El saldo es propio del almacén y empresa. Enviar un traspaso no confirma recepción. Facturar no vuelve a surtir. Acreditar no confirma que la mercancía regresó.',y,GREEN);finish(c,'efectos-'+str(start),y,owner)

def cover(c,owner):
 c.setFillColor(HexColor(NAVY));c.rect(0,0,W,H,fill=1,stroke=0);c.setFillColor(HexColor('#17c0bf'));c.rect(M,H-120,72,7,fill=1,stroke=0);c.setFillColor(white);c.setFont('Helvetica-Bold',42);c.drawString(M,H-96,'ERP JM')
 title='Manual técnico\ny del propietario' if owner else 'Manual gráfico\ndel usuario'
 for i,line in enumerate(title.split('\n')):c.setFont('Helvetica-Bold',30);c.drawString(M,H-190-i*40,line)
 c.setFont('Helvetica',14);c.drawString(M,H-304,'Funcionamiento por módulo');c.drawString(M,H-330,'Reportes, matrices de solución y errores comunes');c.drawString(M,H-356,'Anexo: recorrido completo con 12 diagramas')
 y=H-414
 for s in ['Configuración y permisos','Compra, almacén y producción','Venta, cobro y devolución de cliente','Multiempresa, multialmacén y recuperación']:
  c.setFillColor(HexColor('#17c0bf'));c.circle(M+4,y+4,3,fill=1,stroke=0);c.setFillColor(white);c.setFont('Helvetica',12);c.drawString(M+18,y,s);y-=29
 c.setFont('Helvetica',10);c.drawString(M,100,'Edición documental 1.0 | 3 de noviembre de 2026');c.drawString(M,80,'Basado en piloto ca0ce1e | Lite y Avanzada según módulos contratados');c.drawString(M,60,'Sin contraseñas ni datos reales de clientes');c.showPage()

def source_page(c,owner):
 y=header(c,'Alcance, uso y versión del manual','REFERENCIAS Y LÍMITES','Documento de operación del software; actualizar después de cada cambio relevante.',owner,'fuentes')
 for i,s in enumerate(SOURCES,1):y=card(c,f'{i:02d}  Referencia de uso',s,y)
 y=para(c,'Los diagramas se anexan al final. Incluyen escenario normal, parciales, faltantes, traslados, calidad, devoluciones, créditos, pagos y cancelaciones. No representan todas las combinaciones de configuración posibles; aplica los controles de tu empresa.',M,y)-12
 finish(c,'fuentes',y,owner)

def build(owner):
 name='Manual_Tecnico_y_Dueno_ERP_JM.pdf' if owner else 'Manual_Usuario_ERP_JM.pdf';base=TMP/('base-'+name);c=canvas.Canvas(str(base),pagesize=A4,pageCompression=1);c.setTitle('ERP JM - '+('Manual técnico y del propietario' if owner else 'Manual gráfico del usuario'));c.setAuthor('ERP JM');cover(c,owner)
 # Reserva la página del índice para completarla tras conocer la paginación real.
 c.setFillColor(white);c.rect(0,0,W,H,fill=1,stroke=0);c.showPage()
 if owner:
  text_page(c,'Instalación, red y arranque automático','ADMINISTRACIÓN TÉCNICA',INSTALL,owner,'instalacion')
  text_page(c,'Control del servicio y actualización','ADMINISTRACIÓN TÉCNICA',MAINTENANCE[:4],owner,'mantenimiento',COMMANDS)
  text_page(c,'Verificación y recuperación técnica','ADMINISTRACIÓN TÉCNICA',MAINTENANCE[4:]+[('No cambiar el puerto','8098 es fijo. Si está ocupado, identificar su uso. No utilizar 88999 ni cambiar automáticamente a otro puerto.'),('Instalación portable','La copia portable puede usar otra carpeta de datos. Ejecutar el EXE sin su configuración correcta puede abrir una base vacía distinta.')],owner,'verificacion')
 for m in MODULES:module_page(c,m,owner)
 quality_pages(c,owner)
 for i,r in enumerate(REPORTS,1):report_page(c,r,owner,i)
 matrix_pages(c,owner);source_page(c,owner);c.save()
 # Índice navegable con todas las secciones y su número, generado sin suposiciones.
 selected=[r for r in CHECKS if r['manual']==('tecnico' if owner else 'usuario')];titles={m['id']:m['title'] for m in MODULES};titles.update({'reporte-'+str(i):'Reporte: '+r['title'] for i,r in enumerate(REPORTS,1)})
 toc=BytesIO();tc=canvas.Canvas(toc,pagesize=A4);y=header(tc,'Índice y forma de uso','GUÍA DE LECTURA','Usa los marcadores del PDF o busca el módulo por su nombre.',owner,'indice');y=para(tc,'Cada módulo contiene objetivo, ruta, pasos, efecto en datos y matriz de errores. Después se detallan sus reportes. Las operaciones sólo corresponden al perfil autorizado.',M,y)-14
 tc.setFont('Helvetica',8.2)
 for row in selected:
  key=row['seccion'];title=titles.get(key,{'instalacion':'Instalación, red y arranque','mantenimiento':'Servicio y actualización','verificacion':'Verificación técnica','fuentes':'Alcance y referencias'}.get(key,'QualityLite: áreas '+str(int(key.split('-')[-1])+1)+' a '+str(int(key.split('-')[-1])+5) if key.startswith('calidad-areas-') else 'Diagnóstico transversal' if key.startswith('errores-') else 'Matriz de efectos de operación'))
  if len(title)>85:title=title[:82]+'...'
  tc.setFillColor(HexColor(INK));tc.drawString(M,y,title);tc.drawRightString(W-M,y,str(row['pagina']));y-=12.4
 base_count=len(PdfReader(base).pages);annex_count=12+(1 if owner else 0);tc.setFont('Helvetica-Bold',9);tc.drawString(M,y-8,'Anexo gráfico completo de funcionamiento');tc.drawRightString(W-M,y-8,str(base_count+1));tc.showPage();tc.save();toc.seek(0)
 reader=PdfReader(base)
 # add_page conserva las referencias correctas; reemplazo seguro usando un nuevo ensamblado.
 assembled=PdfWriter()
 for i,page in enumerate(reader.pages):assembled.add_page(PdfReader(toc).pages[0] if i==1 else page)
 for row in selected:assembled.add_outline_item(titles.get(row['seccion'],{'instalacion':'Instalación y red','mantenimiento':'Servicio y actualización','verificacion':'Verificación técnica','fuentes':'Alcance y referencias'}.get(row['seccion'],'QualityLite: áreas '+str(int(row['seccion'].split('-')[-1])+1)+' a '+str(int(row['seccion'].split('-')[-1])+5) if row['seccion'].startswith('calidad-areas-') else 'Diagnóstico transversal' if row['seccion'].startswith('errores-') else 'Matriz de efectos de operación')),row['pagina']-1)
 if owner:assembled.append(str(ASSETS/'diagrama_tecnico.pdf'),outline_item='Anexo: visión de Sistemas')
 assembled.append(str(ASSETS/'Flujo_completo_del_ERP.pdf'),outline_item='Anexo: 12 hojas del flujo completo')
 output=FOLDER/name
 with output.open('wb') as stream:assembled.write(stream)
 doc=pymupdf.open(output)
 for i,page in enumerate(doc):page.insert_text((page.rect.width-78,page.rect.height-11),f'{i+1} / {len(doc)}',fontsize=8,color=(.35,.42,.5))
 temporary=TMP/('numerado-'+name);doc.save(temporary,garbage=4,deflate=True);doc.close();output.write_bytes(temporary.read_bytes())
 return output

if __name__=='__main__':
 for owner in (True,False):print(build(owner))
 (TMP/'manual-layout-checks.json').write_text(json.dumps(CHECKS,ensure_ascii=False,indent=2),encoding='utf8')
