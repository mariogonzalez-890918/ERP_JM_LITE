"""Guarda alta SKU y ficha comercial en una sola transacción."""
from productos_comerciales import save_product

def save_capture(store,sales,cm,data,actor):
 fichas=data.get('fichas')
 if fichas is None:return sales.put(data,actor)
 cm.admin(actor)
 if not isinstance(fichas,list) or not 1<=len(fichas)<=2000:raise ValueError('Indica de 1 a 2000 fichas de producto.')
 with store.atomic() as db:
  result=sales.put(data,actor)
  if result is None:return None
  records={r['id']:r for r in result['state']['registros']};seen=set()
  for ficha in fichas:
   if not isinstance(ficha,dict) or type(ficha.get('id')) is not int:raise ValueError('Ficha de producto inválida.')
   row=records.get(ficha.get('id'))
   if not row or row.get('eliminado') or row['id'] in seen:raise ValueError('SKU inexistente, repetido o dado de baja.')
   seen.add(row['id']);old=db.execute('SELECT revision FROM cm_products WHERE sku=?',(row['sku'],)).fetchone()
   if not ficha.get('impuestoId'):raise ValueError('Selecciona el impuesto de la empresa para cada producto.')
   save_product(cm,{**ficha,'sku':row['sku'],'skuOriginal':row['sku'] if old else None,'nombre':row['nombre'],'tipo':row['tipo'],'categoria':row['categoria'],'subcategoria':row['subcategoria'],'modulo':row['modulo'],'activo':row['estado']=='ACTIVO'},actor)
 return result
