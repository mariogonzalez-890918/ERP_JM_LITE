from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor,white
from reportlab.lib.utils import simpleSplit
import pymupdf
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'manual operativo/recursos';OUT.mkdir(parents=True,exist_ok=True)
NAVY='#123454';BLUE='#006da3';GREEN='#167a63';ORANGE='#b25c10';INK='#20364b';GREY='#607286'

def box(c,x,y,w,h,title,body='',color=BLUE,fill='#f0f7fb',font=12):
 c.setFillColor(HexColor(fill));c.setStrokeColor(HexColor(color));c.setLineWidth(1);c.roundRect(x,y,w,h,8,fill=1,stroke=1)
 c.setFillColor(HexColor(color));c.setFont('Helvetica-Bold',font)
 lines=simpleSplit(title,'Helvetica-Bold',font,w-18);top=y+h-20
 for line in lines:c.drawCentredString(x+w/2,top,line);top-=font+2
 c.setFillColor(HexColor(INK));c.setFont('Helvetica',10.5)
 for line in simpleSplit(body,'Helvetica',10.5,w-20):top-=13;c.drawCentredString(x+w/2,top,line)

def arrow(c,x1,y1,x2,y2,color=GREY):
 import math
 c.setStrokeColor(HexColor(color));c.setFillColor(HexColor(color));c.setLineWidth(1.5);c.line(x1,y1,x2,y2)
 angle=math.atan2(y2-y1,x2-x1);p=c.beginPath();p.moveTo(x2,y2);p.lineTo(x2-7*math.cos(angle-.45),y2-7*math.sin(angle-.45));p.lineTo(x2-7*math.cos(angle+.45),y2-7*math.sin(angle+.45));p.close();c.drawPath(p,fill=1,stroke=0)

def label(c,x,y,text,size=11,color=INK):c.setFont('Helvetica',size);c.setFillColor(HexColor(color));c.drawString(x,y,text)

def start(path,title,sub):
 c=canvas.Canvas(str(path),pagesize=(1100,780));c.setTitle(title);c.setFillColor(HexColor('#ffffff'));c.rect(0,0,1100,780,fill=1,stroke=0);c.setFillColor(HexColor(NAVY));c.rect(0,700,1100,80,fill=1,stroke=0);c.setFillColor(white);c.setFont('Helvetica-Bold',24);c.drawString(30,742,title);c.setFont('Helvetica',12);c.drawString(30,718,sub);return c

def finish(c,path):
 label(c,30,18,'ERP JM | Piloto ca0ce1e | 03 nov 2026 | Flujo real de esta versión',9,GREY);c.save();doc=pymupdf.open(path);doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(path.with_suffix('.png'));doc.close()

def technical():
 path=OUT/'diagrama_tecnico.pdf';c=start(path,'Cómo funciona ERP JM: dueño y técnico','Configuración, operación y recuperación. Producción se habilita sólo si la empresa la utiliza.')
 box(c,30,620,300,58,'Servidor Windows','Tarea ERP-JM-Lite + puerto web 8098',NAVY);box(c,400,620,300,58,'Navegador LAN / VPN','Usa la IP o nombre del servidor',NAVY);box(c,770,620,300,58,'Sistemas / Gerencia','Permisos y alcance por empresa',NAVY);arrow(c,330,649,400,649);arrow(c,700,649,770,649)
 config=['Módulos\ncontratados','Usuarios y\nperfiles','Razones sociales\ny sucursales','SKU, impuestos\ny unidades','Almacenes e\niniciales','Respaldo de\narranque']
 for i,text in enumerate(config):
  x=30+i*175;box(c,x,536,165,57,text.replace('\n',' '),font=11)
  if i<5:arrow(c,x+165,564,x+175,564)
 arrow(c,550,620,550,593)
 lanes=[(30,BLUE,'COMPRAS',['Cotización y pedido','Recepción física: +material','Registrar compra y cargo CXP','Registrar pago al proveedor']),
        (390,GREEN,'VENTAS',['Presupuesto y pedido','Reserva lógica: sin Kárdex','Remisión: salida de stock','Factura CXC y cobro']),
        (750,ORANGE,'PRODUCCIÓN OPCIONAL',['Receta y orden autorizada','Surtir y consumir materiales','Fabricar y revisar Calidad','Recibir: +PT o Cuarentena'])]
 for x,color,title,steps in lanes:
  box(c,x,464,320,45,title,color=color,fill='#f4f7fa',font=14)
  for i,text in enumerate(steps):
   y=400-i*62;box(c,x+10,y,300,45,text,color=color,font=12)
   if i<3:arrow(c,x+160,y,x+160,y-17,color)
  arrow(c,x+160,536,x+160,509)
  arrow(c,x+160,214,x+160,178)
 box(c,30,120,1040,58,'SQLite + Kárdex + historial','Un solo origen de datos. Las reservas no cambian el físico; los movimientos confirmados quedan auditados.',NAVY,font=15)
 box(c,30,45,500,55,'Control diario','Reportes, conciliación, carteras privadas y respaldos',GREEN)
 box(c,570,45,500,55,'Si ocurre un incidente','Diagnóstico -> copia previa -> restauración autorizada',ORANGE)
 arrow(c,280,120,280,100);arrow(c,820,120,820,100)
 finish(c,path)

def user():
 path=OUT/'diagrama_usuario.pdf';c=start(path,'Cómo trabajar en ERP JM: usuario','Escoge tu tarea y sigue su flujo. Los botones visibles dependen de tus permisos.')
 for x,title,body in [(30,'1. Entrar','URL del servidor + usuario + 2FA si aplica'),(390,'2. Elegir contexto','Empresa, sucursal y almacén correctos'),(750,'3. Abrir tu módulo','Si no aparece: solicitar acceso a Sistemas')]:box(c,x,612,320,66,title,body,NAVY,font=15)
 arrow(c,350,645,390,645);arrow(c,710,645,750,645)
 cards=[(30,470,BLUE,'Ventas y CRM','Prospectar -> presupuesto -> pedido\nEntrega autorizada -> remisión\nFactura comercial -> cobro'),(390,470,BLUE,'Compras y CXP','Solicitud -> pedido al proveedor\nRecibir lo que llegó -> registrar compra\nCargo CXP -> pago registrado'),(750,470,GREEN,'Almacenes','Elegir almacén -> consultar físico\nSurtir / recibir / traspasar con permiso\nComprobar el Kárdex'),(30,316,ORANGE,'Producción','Receta -> orden -> autorización\nSurtir -> consumo -> fabricación\nRecibir PT / Cuarentena -> cerrar'),(390,316,GREEN,'Calidad y requisiciones','Calidad: registro -> evidencia -> revisión\nRequisición: solicitar -> surtir\nLa inspección sola no libera stock'),(750,316,BLUE,'SKU, cargas y TPV','SKU: clasificar -> completar -> guardar\nCarga: layout -> revisar -> aplicar\nTPV actual: caja -> emitir ticket')]
 for x,y,color,title,body in cards:
  box(c,x,y,320,122,title,color=color,font=15)
  for i,line in enumerate(body.split('\n')):label(c,x+14,y+62-i*20,line,11)
 for x in (190,550,910):arrow(c,x,612,x,592)
 box(c,30,214,1040,65,'4. Confirmar una sola vez y verificar','Revisa el folio, el estado, el saldo y las cantidades. Después descarga tu reporte o PDF.',NAVY,font=16)
 for x in (190,550,910):arrow(c,x,316,x,279)
 box(c,30,112,500,72,'¿Aparece un error?','Lee el aviso -> consulta si se guardó -> corrige o pide apoyo. No dupliques movimientos.',ORANGE)
 box(c,570,112,500,72,'5. Terminar la jornada','Guarda pendientes, revisa documentos y cierra tu sesión. No cierres el servicio del servidor.',GREEN)
 arrow(c,280,214,280,184);arrow(c,820,214,820,184)
 label(c,30,67,'IMPORTANTE: ticket, factura pendiente de PAC y cobro son registros distintos.',12,ORANGE)
 label(c,30,45,'El TPV visible emite tickets; no registra por sí solo cobro ni salida automática de Kárdex.',11,INK)
 finish(c,path)

if __name__=='__main__':technical();print('Diagrama técnico generado.')
