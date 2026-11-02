import base64,copy,unittest
import test_purchase_v3 as cases

class SKUFichaTests(unittest.TestCase):
 def setUp(self):
  self.c=cases.PurchaseV3Tests();self.c.setUp();self.addCleanup(self.c.tearDown)
 def test_capture_is_atomic_and_product_is_ready_for_sale(self):
  from ventas import assign
  c=self.c;data=c.value('/api/ventas');state=copy.deepcopy(data['state']);catalogs=data['catalogos'];row={'id':state['maxId']+1,'tipo':next(iter(catalogs['TIP'])),'categoria':next(iter(catalogs['CAT'])),'subcategoria':next(iter(catalogs['SUB'])),'nombre':'Producto aquí','modulo':'000','estado':'ACTIVO','eliminado':False,'validado':False,'anterior':'','fila':None,'editado':True};assign(state,row);state['registros'].append(row);state['maxId']=row['id']
  tax=c.value('/api/empresa/impuestos',{'empresa':c.company,'nombre':'Impuesto capturado','tasa':'16'})['id'];ficha={'id':row['id'],'empresa':c.company,'impuestoId':tax,'unidad':'PIEZA','canales':['ventasins'],'precios':{'PUBLICO':'116'},'claveAlterna':'COD-PRUEBA','claveSat':'01010101','naturaleza':'PRODUCTO'};request={'revision':data['revision'],'state':state,'fichas':[ficha]}
  self.assertEqual(c.call('/api/ventas',{**request,'fichas':[{**ficha,'impuestoId':'inexistente'}]},method='PUT')[0],400);self.assertEqual(c.value('/api/ventas')['state'],data['state'])
  c.value('/api/ventas',request,method='PUT');product=next(p for p in c.value('/api/comercial/productos?empresa='+str(c.company))['productos'] if p['sku']==row['sku']);self.assertEqual(product['iva'],'16');self.assertEqual(product['claveAlterna'],'COD-PRUEBA');self.assertEqual(product['precios']['PUBLICO'],'116')
 def test_mass_tax_review_rollback_atomicity_stale_and_cross_company(self):
  from catalog_loads import workbook
  from impuestos_import import HEADERS
  c=self.c;path='/api/empresa/impuestos/importar';raw=workbook('IMPUESTOS',HEADERS,[{'A':'compras','B':c.material['sku'],'C':'Traslado lote','D':'5.5','E':'SI'}]);data={'empresa':c.company,'contenido':base64.b64encode(raw).decode()};review=c.value(path,{**data,'revisar':True});self.assertEqual(c.value('/api/empresa/impuestos?empresa='+str(c.company))['impuestos'],[])
  c.value('/api/empresa/impuestos',{'empresa':c.company,'nombre':'Cambio posterior','tasa':'0'});self.assertEqual(c.call(path,{**data,'huellaActual':review['huellaActual'],'huellaArchivo':review['huellaArchivo']})[0],409)
  review=c.value(path,{**data,'revisar':True});c.value(path,{**data,'huellaActual':review['huellaActual'],'huellaArchivo':review['huellaArchivo']});self.assertEqual(c.po('materiales')['materiales'][0]['impuesto'],'5.5')
  bad=workbook('IMPUESTOS',HEADERS,[{'C':'No debe quedar','D':'7','E':'SI'},{'A':'compras','B':'NOEXISTE','C':'No debe quedar','D':'7','E':'SI'}]);self.assertEqual(c.call(path,{'empresa':c.company,'contenido':base64.b64encode(bad).decode(),'revisar':True})[0],400);self.assertNotIn('No debe quedar',[t['nombre'] for t in c.value('/api/empresa/impuestos?empresa='+str(c.company))['impuestos']]);self.assertEqual(c.call(path,{**data,'revisar':True},c.buyer)[0],403)

if __name__=='__main__':unittest.main()
