"""Layouts sin datos empresariales y cargas iniciales enlazadas, atómicas y revisables."""
import base64,hashlib,io,json,zipfile
from xml.sax.saxutils import escape
from permissions import require_module
from requisiciones import Conflict,now,read_rows,norm
PURCHASE={'A':'CLAVE PROVEEDOR','B':'SKU','C':'STATUS DE COMPRA','D':'SKU NUEVO','E':'PRODUCTO','F':'CATEGORIA','G':'SUBCATEGORIA','H':'DESCRIPCION','I':'PRECIO DE COMPRA','J':'IMPUESTO DE COMPRA','K':'COSTO','L':'U_M','M':'UM_COMPRA','N':'UM_ENTREGA','O':'PROVEEDOR PRINCIPAL'}
SALES={'A':'SKU','B':'PRODUCTOS Y SERVICIOS','C':'CATEGORIA','D':'SUBCATEGORIA','E':'LINEA','F':'MODULO ID PDV','G':'EXPENDIO','H':'DESCRIPCION','I':'PRECIO PUBLICO','J':'PRECIO RUTA','K':'PRECIO DESPACHO','N':'IMPUESTO','O':'UOM','S':'ESTADO','W':'CANAL'}
LAYOUTS={
 'compras':('SKU Compras e insumos','PRODUCTOS',PURCHASE,'compras','Genera o conserva SKU y enlaza los materiales de requisiciones, compras e inventarios.'),
 'ventas':('SKU Ventas','SUGERIDO',SALES,'ventas','Conserva SKU históricos y enlaza productos, listas de precios y canales de venta.'),
 'pdv':('Punto de venta','SUGERIDO',SALES,'expendios','CANAL: EXPENDIOS o AMBOS. Precios incluyen impuestos; IMPUESTO: 0, 8 o 16. Requiere empresa.'),
 'requisiciones':('Materiales de requisición','PRODUCTOS',PURCHASE,'requisiciones','Carga el maestro de materiales de requisición. Para enlazar SKU usa la carga de Compras.'),
 'proveedores':('Proveedores','PROVEEDORES',None,'pedidoscompra','Usa el importador de proveedores en Compras.'),
 'clientes':('Clientes','CLIENTES',None,'ventasins','Usa el importador de clientes en Ventas o PDV.'),
 'precios':('Listas de precios','PRECIOS',None,'ventasins','Usa Carga de precios en Ventas o PDV.'),
 'inventarios':('Inventario inicial','INVENTARIO',None,'inventarios','Usa Cargar conteo inicial en Inventarios; selecciona almacén y revisa antes de autorizar.'),
 'empresa':('Datos de empresa','EMPRESA',{'A':'NOMBRE','B':'RFC','C':'DOMICILIO','D':'RUBRO','E':'RESPONSABLE','F':'CORREO','G':'TELEFONO'},'empresa','Captura estos campos en Empresa. El token nunca forma parte de un layout.'),
 'sucursales':('Sucursales','SUCURSALES',{'A':'NOMBRE','B':'SERIE'},'empresa','Configura las sucursales en Empresa; usa series únicas y conserva los nombres históricos.'),
 'usuarios':('Usuarios y perfiles','USUARIOS',{'A':'CORREO','B':'NOMBRE','C':'PERFIL','D':'SUCURSALES','E':'ALMACENES'},'empresa','Captura usuarios desde Administración. Las contraseñas se establecen individualmente, fuera del layout.')}
QUALITY={'documentos':'documents','formatos':'forms','registros':'records','auditorias':'audits','no-conformidades':'findings','acciones-correctivas':'actions'}
for name,module in QUALITY.items():
 from quality_lite import FIELDS,MODULES
 headers={'A':'CODIGO','B':'TITULO','C':'DATOS_JSON'}
 LAYOUTS[name]=(MODULES[module],name.upper(),headers,'calidad','DATOS_JSON usa los campos del módulo; los formatos incluyen schema y los registros formato/valores. La carga crea borradores para revisar y aprobar.')

def workbook(sheet,headers,rows=()):
 ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main';out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
  z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
  z.writestr('xl/workbook.xml','<workbook xmlns="'+ns+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="'+escape(sheet)+'" sheetId="1" r:id="rId1"/></sheets></workbook>')
  z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
  body=''.join('<row r="'+str(index)+'">'+''.join('<c r="'+col+str(index)+'" t="inlineStr"><is><t xml:space="preserve">'+escape(str(value))+'</t></is></c>' for col,value in row.items())+'</row>' for index,row in enumerate([headers,*rows],1))
  z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="'+ns+'"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="23" width="24" customWidth="1"/></cols><sheetData>'+body+'</sheetData></worksheet>')
 return out.getvalue()

class CatalogLoads:
 def __init__(self,store,purchases,sales,requisitions,reports,commercial,quality):self.store=store;self.purchases=purchases;self.sales=sales;self.req=requisitions;self.reports=reports;self.cm=commercial;self.quality=quality
 def listed(self,actor):
  from permissions import enabled_modules
  enabled=enabled_modules(actor)
  return {'layouts':[{'id':id,'nombre':v[0],'instrucciones':v[4],'url':'/api/empresa/layout/'+id,'cargaCentral':id in ('compras','ventas','pdv') or id in QUALITY} for id,v in LAYOUTS.items() if v[3] in enabled or actor['role']=='superadmin' or v[3]=='ventasins' and 'expendios' in enabled]}
 def layout(self,id,actor):
  if id not in {r['id'] for r in self.listed(actor)['layouts']}:raise PermissionError('Layout no disponible para tu perfil.')
  title,sheet,headers,module,note=LAYOUTS[id]
  if id=='proveedores':
   from pedidos_compra_vendors import HEADERS
   headers={self.col(i):v for i,v in enumerate(HEADERS)}
  elif id=='clientes':
   from clientes_comerciales import HEADERS
   headers={self.col(i):v for i,v in enumerate(HEADERS)}
  elif id=='precios':
   # El archivo corresponde al importador existente, con pestañas y columnas propias.
   from ventas import ROOT
   return (ROOT/'public/layout-precios.xlsx').read_bytes(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  elif id=='inventarios':
   from inventarios import HEADERS
   headers={self.col(i):v for i,v in enumerate(HEADERS)}
  return workbook(sheet,headers),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
 @staticmethod
 def col(i):
  result='';i+=1
  while i:i,r=divmod(i-1,26);result=chr(65+r)+result
  return result
 def fingerprint(self,db):
  values=[]
  for table in ('catalog','sales_catalog','req_materials','cm_products','cm_prices','cm_companies','q_items'):
   for row in db.execute('SELECT * FROM '+table+' ORDER BY rowid'):values.append([table,list(row)])
  return hashlib.sha256(json.dumps(values,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 def run(self,data,actor):
  id=data.get('modulo');review=data.get('revisar') is True;require_module(actor,'cargar_maestro')
  if id not in ('compras','ventas','pdv') and id not in QUALITY:raise ValueError('Usa el importador indicado en el layout de este módulo.')
  require_module(actor,LAYOUTS[id][3])
  if id not in QUALITY and actor['role'] not in ('superadmin','auxti'):raise PermissionError('Solo administración ejecuta cargas iniciales enlazadas.')
  try:raw=base64.b64decode(data.get('contenido',''),validate=True)
  except Exception:raise ValueError('Archivo inválido.')
  if not raw or len(raw)>15*1024*1024:raise ValueError('Usa un XLSX de hasta 15 MB.')
  digest=hashlib.sha256(raw).hexdigest()
  with self.store.atomic(rollback=review) as db:
   fingerprint=self.fingerprint(db)
   if not review and (data.get('huellaActual')!=fingerprint or data.get('huellaArchivo')!=digest):raise Conflict('La base o el archivo cambió. Revisa nuevamente la carga.')
   if id=='compras':
    require_module(actor,'requisiciones');require_module(actor,'pedidoscompra')
    rev=db.execute('SELECT revision FROM catalog WHERE id=1').fetchone()[0]
    result=self.purchases.run({**data,'archivo':'INICIAL.xlsx','revision':rev,'revisar':False},actor)
    if result['resumen']['conflictos']:raise ValueError('La carga tiene conflictos; corrige las filas antes de aplicar.')
    from compras import export_products
    content=base64.b64encode(export_products(self.store.get(),self.store.catalogs)).decode()
    linked=self.req.import_master({'archivo':'INICIAL.xlsx','contenido':content},actor);self.reports.sync_import(actor)
    result={'sku':result['resumen'],'materiales':linked}
   elif id in ('ventas','pdv'):
    require_module(actor,'ventas')
    companies=data.get('empresas',[])
    if not isinstance(companies,list) or not companies:raise ValueError('Selecciona al menos una empresa destino.')
    for company in companies:self.cm.company(company,actor,True)
    rev=db.execute('SELECT revision FROM sales_catalog WHERE id=1').fetchone()[0]
    loaded=self.sales.import_master({'master':data['contenido'],'revision':rev},actor)
    if loaded is None:raise Conflict('El catálogo de ventas cambió.')
    rows=[]
    for record in loaded['state']['registros']:
     if record['eliminado']:continue
     row={**record.get('camposExcel',{}),'A':record['sku'],'H':record['nombre'],'S':record['estado']}
     if not row['A']:raise ValueError('Completa la clasificación para generar todos los SKU de ventas.')
     if id=='pdv' and norm(row.get('W','')) not in ('EXPENDIOS','AMBOS'):raise ValueError('La carga PDV requiere CANAL EXPENDIOS o AMBOS en todas las filas.')
     rows.append(row)
    linked_content=base64.b64encode(workbook('SUGERIDO',SALES,rows)).decode()
    from maestro_comercial import import_master
    result=import_master(self.cm,{'empresas':companies,'contenido':linked_content,'archivo':'INICIAL.xlsx'},actor)
    if result['totalPendientes']:raise ValueError('Completa impuestos, unidades y precios de todos los productos antes de aplicar la carga.')
    result['skuEnlazados']=len(rows)
   else:
    rows,_=read_rows(raw,'INICIAL.xlsx',sheet_name=LAYOUTS[id][1]);result={'registros':0}
    for number,row in rows[1:]:
     if not any(str(v).strip() for v in row.values()):continue
     try:values=json.loads(row.get('C','{}'))
     except ValueError:raise ValueError('DATOS_JSON inválido en fila '+str(number))
     self.quality.save({'modulo':QUALITY[id],'codigo':row.get('A'),'titulo':row.get('B'),'datos':values},actor);result['registros']+=1
    if not result['registros']:raise ValueError('El layout no contiene registros.')
   return {'ok':True,'revisar':review,'huellaActual':fingerprint,'huellaArchivo':digest,'resultado':result}
