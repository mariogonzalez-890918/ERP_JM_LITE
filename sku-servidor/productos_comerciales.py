"""Captura de productos, pertenencia a canales y reserva central de SKU."""
import copy,json,re
from decimal import Decimal,ROUND_HALF_UP
from comercial import ADMINS,amount,dumps,now
from requisiciones import Conflict,text
from ventas import TIP,CAT,SUB,PDV,ALPHABET,resolve,key_from_name,validate as validate_sales

def channels(product):return [c for c,enabled in [('ventasins',product.get('institucional',True)),('expendios',product.get('expendio',False))] if enabled]
def optional_price(value):
 if value is None or str(value).strip().upper() in ('','NULL','N/A','NA'):return None
 try:q=Decimal(str(value))
 except Exception:raise ValueError('Precio inválido.')
 if not q.is_finite() or q<0 or q>Decimal('999999999'):raise ValueError('Precio fuera de rango.')
 return format(q.quantize(Decimal('.000001'),rounding=ROUND_HALF_UP).normalize(),'f')

def catalog(cm,company,actor):
 cm.admin(actor);cm.company(company,actor)
 with cm.store.connect() as db:
  rows=db.execute('SELECT sku,revision,payload FROM cm_products ORDER BY sku').fetchall();prices={(l,s):{'revision':r,**json.loads(p)} for l,s,r,p in db.execute("SELECT list,sku,revision,payload FROM cm_prices WHERE company=? AND customer=''",(company,))}
 from impuestos import listed,configured
 taxes={}
 with cm.store.connect() as db:
  tax_list=listed(db,company)
  for sku,_,_ in rows:
   tax=configured(db,company,'ventas',sku,strict=False)
   if tax:taxes[sku]=tax
 from product_options import listed as list_options
 with cm.store.connect() as db:options=list_options(db)
 return {'opciones':options,'impuestos':tax_list,'productos':[{'sku':s,'revision':r,**json.loads(p),**taxes.get(s,{}),'canales':channels(json.loads(p)),'precios':{l:prices[(l,s)]['precio'] for l in ('PUBLICO','MINIMO','REMATE','RUTA','DESPACHO') if (l,s) in prices}} for s,r,p in rows],'tipos':TIP,'categorias':CAT,'subcategorias':SUB,'modulos':PDV}

def save_product(cm,data,actor):
 cm.admin(actor);company=data.get('empresa');cm.company(company,actor,True);name=text(data.get('nombre',''),300);unit=text(data.get('unidad','SELECCIONADA' if data.get('unidadId') else ''),100);selected=data.get('canales',[]);sku=str(data.get('sku','')).strip().upper();original=data.get('skuOriginal');rate=amount(data.get('iva','0'))
 tax_id=data.get('impuestoId')
 if tax_id:
  from impuestos import selected as selected_tax
  with cm.store.connect() as db:_,tax_rate=selected_tax(db,company,tax_id)
  rate=Decimal(tax_rate)
 if not name or not unit or not isinstance(selected,list) or not selected or len(set(selected))!=len(selected) or set(selected)-{'ventasins','expendios'} or rate>100:raise ValueError('Indica descripción, unidad, 0% sin IVA, 8% IEPS o 16% IVA y al menos un canal.')
 prices={l:optional_price((data.get('precios') or {}).get(l)) for l in ('PUBLICO','MINIMO','REMATE','RUTA','DESPACHO')}
 if 'ventasins' in selected and prices['PUBLICO'] is None:raise ValueError('Institucionales requiere precio público con IVA.')
 if 'expendios' in selected and all(prices[k] is None for k in ('PUBLICO','MINIMO','REMATE','RUTA','DESPACHO')):raise ValueError('TPV requiere al menos un precio configurado.')
 with cm.store.connect() as db:
  db.execute('BEGIN IMMEDIATE');sale_row=db.execute('SELECT revision,payload FROM sales_catalog WHERE id=1').fetchone();sales=json.loads(sale_row[1]);state=sales['state'];old=None
  if original:
   if original!=sku:raise ValueError('No se cambia el SKU de un producto existente.')
   old=db.execute('SELECT revision,payload FROM cm_products WHERE sku=?',(original,)).fetchone()
   if not old:raise ValueError('Producto no disponible.')
  if not sku:
   codes=[resolve(data.get(k,''),t) for k,t in [('tipo',TIP),('categoria',CAT),('subcategoria',SUB)]]
   if '00' in codes:raise ValueError('Para generar SKU selecciona tipo, categoría y subcategoría válidos.')
   body=''.join(codes)+key_from_name(name);used=set(state['reservados'])|{r.get('sku') for r in state['registros']}|{r[0] for r in db.execute('SELECT sku FROM cm_products')}
   sku=next((body+suffix for suffix in ALPHABET if body+suffix not in used),None)
   if not sku:raise ValueError('Se agotaron las claves para este nombre; usa un SKU diferente.')
  if not re.fullmatch('[A-Z0-9]{14}',sku):raise ValueError('El SKU debe tener 14 caracteres sin espacios ni guiones.')
  existing=db.execute('SELECT revision FROM cm_products WHERE sku=?',(sku,)).fetchone()
  if existing and not old:raise Conflict('Ese SKU ya existe. Abre Editar producto para modificarlo.')
  if data.get('revision',0)!=(old[0] if old else 0):raise Conflict('El producto cambió. Actualiza el catálogo.')
  if sku in state['reservados']:raise ValueError('El SKU está reservado por una baja anterior.')
  value={'nombre':name,'unidad':unit,'iva':format(rate,'f'),'tipo':text(data.get('tipo',''),100),'categoria':text(data.get('categoria',''),100),'subcategoria':text(data.get('subcategoria',''),100),'linea':text(data.get('linea',''),100),'modulo':text(data.get('modulo',''),100),'institucional':'ventasins' in selected,'expendio':'expendios' in selected,'activo':data.get('activo',True) is True,'origen':'MANUAL'}
  if tax_id:value['iva']=json.loads(old[1]).get('iva') if old else None
  previous=json.loads(old[1]) if old else {}
  from product_options import resolve as resolve_option
  unit_id,unit_name,unit_sat=resolve_option(db,'unidad',data.get('unidadId'),unit,previous.get('unidad',''))
  line_id,line_name,_=resolve_option(db,'linea',data.get('lineaId'),text(data.get('linea',''),100),previous.get('linea',''))
  value.update({'unidad':unit_name,'unidadId':unit_id,'linea':line_name,'lineaId':line_id})
  for field,limit in [('claveAlterna',80),('claveSat',8),('unidadSat',10),('observaciones',2000)]:value[field]=text(data.get(field,previous.get(field,'')),limit)
  from sat_catalogs import validate as validate_sat
  value['claveSat']=validate_sat('productos',value['claveSat'])
  if unit_sat and value['unidadSat'] and value['unidadSat']!=unit_sat:raise ValueError('La clave SAT de unidad debe coincidir con la unidad de venta configurada.')
  value['unidadSat']=validate_sat('unidades',unit_sat or value['unidadSat'])
  kind=data.get('naturaleza',previous.get('naturaleza','PRODUCTO'))
  if kind not in ('PRODUCTO','SERVICIO'):raise ValueError('Selecciona producto o servicio.')
  value['naturaleza']=kind
  db.execute('INSERT INTO cm_products VALUES(?,?,?) ON CONFLICT(sku) DO UPDATE SET payload=excluded.payload,revision=excluded.revision',(sku,dumps(value),(old[0] if old else 0)+1))
  for listing,price in prices.items():
   enabled=listing in ('PUBLICO','MINIMO','REMATE') or listing in ('RUTA','DESPACHO') and 'expendios' in selected
   if price is None or not enabled:db.execute("DELETE FROM cm_prices WHERE company=? AND list=? AND sku=? AND customer=''",(company,listing,sku));continue
   previous=db.execute("SELECT revision FROM cm_prices WHERE company=? AND list=? AND sku=? AND customer=''",(company,listing,sku)).fetchone()
   db.execute("INSERT INTO cm_prices VALUES(?,?,?,'',?,?) ON CONFLICT(company,list,sku,customer) DO UPDATE SET revision=excluded.revision,payload=excluded.payload",(company,listing,sku,(previous[0] if previous else 0)+1,dumps({'precio':price,'origen':'MANUAL','fecha':now()})))
  # El generador SKU comparte las reservas para que una captura posterior no repita la clave.
  if not any(r.get('sku')==sku for r in state['registros']):
   before=copy.deepcopy(sales);id=state['maxId']+1;state['maxId']=id
   state['registros'].append({'id':id,'tipo':resolve(value['tipo'],TIP),'categoria':resolve(value['categoria'],CAT),'subcategoria':resolve(value['subcategoria'],SUB),'nombre':name,'sku':sku,'anterior':sku,'clave':sku[6:13],'digito':sku[-1],'modulo':value['modulo'] if value['modulo'] in PDV else '000','fila':None,'estado':'ACTIVO','eliminado':False,'validado':True,'editado':False})
   validate_sales(sales);db.execute('INSERT INTO sales_history VALUES(?,?,?)',(sale_row[0],now(),dumps(before)));db.execute('UPDATE sales_catalog SET revision=revision+1,payload=? WHERE id=1',(dumps(sales),))
  if tax_id:
   db.execute('INSERT INTO app_product_taxes VALUES(?,?,?,?,1) ON CONFLICT(company,scope,sku) DO UPDATE SET tax=excluded.tax,revision=app_product_taxes.revision+1',(company,'ventas',sku,tax_id))
  cm.audit(db,actor,company,'producto_manual_guardado',{'sku':sku,'canales':selected})
 return {'ok':True,'sku':sku}
