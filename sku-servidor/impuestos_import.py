"""Layout revisable para impuestos y asignaciones a SKU por empresa."""
import base64,hashlib,json
from impuestos import save,link
from requisiciones import read_rows,norm,Conflict

HEADERS={'A':'AMBITO','B':'SKU','C':'IMPUESTO','D':'TASA','E':'ACTIVO'}
def layout():
 from catalog_loads import workbook
 return workbook('IMPUESTOS',HEADERS),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

def run(enterprise,data,actor):
 if actor['role']!='superadmin':raise PermissionError('Solo Superadministrador carga impuestos masivamente.')
 company=data.get('empresa');enterprise.company_logo(company,actor)
 try:raw=base64.b64decode(data.get('contenido',''),validate=True)
 except (ValueError,TypeError):raise ValueError('Archivo XLSX inválido.')
 if not raw or len(raw)>5*1024*1024:raise ValueError('Usa un XLSX de hasta 5 MB.')
 rows,_=read_rows(raw,'IMPUESTOS.xlsx',sheet_name='IMPUESTOS')
 if not rows or {k:norm(v) for k,v in rows[0][1].items()}!=HEADERS:raise ValueError('Usa el layout IMPUESTOS sin cambiar sus encabezados.')
 if len(rows)>2001:raise ValueError('Máximo 2000 filas por carga.')
 review=data.get('revisar') is True
 with enterprise.store.atomic(rollback=review) as db:
  digest=hashlib.sha256(raw+str(company).encode()).hexdigest();stamp=enterprise.fingerprint(db)
  if not review and (data.get('huellaArchivo')!=digest or data.get('huellaActual')!=stamp):raise Conflict('Los datos o el archivo cambiaron. Revisa la carga nuevamente.')
  result=[];definitions={};links=set()
  for number,row in rows[1:]:
   if not any(str(v).strip() for v in row.values()):continue
   name=str(row.get('C','')).strip();rate=str(row.get('D','')).strip();enabled=norm(row.get('E','SI'))
   if enabled not in ('SI','NO'):raise ValueError('ACTIVO debe ser SI o NO; fila '+str(number)+'.')
   key=norm(name);definition=(rate,enabled)
   if key in definitions and definitions[key]!=definition:raise ValueError('Definición contradictoria del impuesto en la fila '+str(number)+'.')
   old=next((r for r in db.execute('SELECT id,name,revision,rate,active FROM app_taxes WHERE company=?',(company,)) if norm(r[1])==key),None)
   changed=old is None or old[3]!=rate or bool(old[4])!=(enabled=='SI')
   if key not in definitions:
    saved=save(db,{'empresa':company,'nombre':name,'tasa':rate,'activo':enabled=='SI','id':old[0] if old else None,'revision':old[2] if old else 0});tax=saved['id'];definitions[key]=definition
   else:tax=old[0]
   scope=str(row.get('A','')).strip().lower();sku=str(row.get('B','')).strip().upper()
   if scope or sku:
    if not sku or (scope,sku) in links:raise ValueError('SKU vacío o vínculo repetido en fila '+str(number)+'.')
    links.add((scope,sku));prior=db.execute('SELECT revision FROM app_product_taxes WHERE company=? AND scope=? AND sku=?',(company,scope,sku)).fetchone()
    link(db,{'empresa':company,'ambito':scope,'sku':sku,'impuesto':tax,'revision':prior[0] if prior else 0})
   result.append({'fila':number,'ambito':scope,'sku':sku,'impuesto':name,'tasa':rate,'accion':'Crear impuesto' if old is None else 'Actualizar impuesto' if changed else 'Conservar impuesto','vincular':bool(sku)})
  if not result:raise ValueError('El archivo no contiene datos.')
  enterprise.audit(db,actor,'carga_impuestos',{'empresa':company,'filas':len(result),'vinculos':len(links)})
 return {'ok':True,'revisado':review,'huellaArchivo':digest,'huellaActual':stamp,'filas':result,'impuestos':len(definitions),'vinculos':len(links)}
