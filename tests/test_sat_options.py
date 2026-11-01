import unittest
import test_purchase_v3 as cases

class SATOptionsTests(unittest.TestCase):
 def setUp(self):
  self.c=cases.PurchaseV3Tests();self.c.setUp();self.addCleanup(self.c.tearDown)
 def test_full_official_catalog_search_and_validation(self):
  c=self.c;result=c.value('/api/empresa/sat?tipo=productos&q=01010101');self.assertEqual(result['totalCatalogo'],52513);self.assertEqual(result['resultados'][0]['clave'],'01010101');self.assertIn('sat.gob.mx',result['fuente']);self.assertEqual(result['version'],'2026-10-29')
  units=c.value('/api/empresa/sat?tipo=unidades&q=KGM');self.assertEqual(units['totalCatalogo'],2418);self.assertEqual(units['resultados'][0]['clave'],'KGM')
  from sat_catalogs import validate
  self.assertEqual(validate('unidades','H87'),'H87')
  with self.assertRaises(ValueError):validate('productos','12345678')
 def test_controlled_units_optional_lines_and_distinct_prices(self):
  c=self.c;path='/api/empresa/catalogos-producto';self.assertEqual(c.call(path,{'tipo':'linea','nombre':'Manipulada'},c.buyer)[0],403)
  unit=c.value(path,{'tipo':'unidad','nombre':'Caja configurable','claveSat':'XBX'})['id'];line=c.value(path,{'tipo':'linea','nombre':'Línea configurable'})['id']
  data={'empresa':c.company,'sku':'010101TEST0001','nombre':'Producto','unidadId':unit,'lineaId':line,'iva':'16','canales':['ventasins','expendios'],'precios':{'PUBLICO':'116','MINIMO':'90','REMATE':'70'},'claveSat':'01010101'}
  c.value('/api/comercial/productos',data);product=next(p for p in c.value('/api/comercial/productos/catalogo?empresa='+str(c.company))['productos'] if p['sku']==data['sku']);self.assertEqual(product['unidad'],'Caja configurable');self.assertEqual(product['unidadSat'],'XBX');self.assertEqual(product['precios'],{'PUBLICO':'116','MINIMO':'90','REMATE':'70'});self.assertNotIn('RUTA',product['precios'])
  update={**data,'skuOriginal':data['sku'],'revision':product['revision'],'lineaId':'','unidad':'Manipulada','linea':''};c.value('/api/comercial/productos',update);product=next(p for p in c.value('/api/comercial/productos/catalogo?empresa='+str(c.company))['productos'] if p['sku']==data['sku']);self.assertEqual(product['unidad'],'Caja configurable');self.assertEqual(product['linea'],'')
  self.assertEqual(c.call('/api/comercial/productos',{**data,'sku':'010101TEST0002','unidadId':'NO-EXISTE'})[0],400)
  self.assertEqual(c.call('/api/comercial/productos',{**data,'sku':'010101TEST0002','unidadSat':'KGM'})[0],400)
  self.assertEqual(c.call(path,{'tipo':'unidad','nombre':'Unidad no SAT','claveSat':'INVALIDA'})[0],400)
  import uuid
  box=c.value('/api/comercial/cajas',{'canal':'expendios','empresa':c.company,'sucursal':'CENTRAL','codigo':'REMATE','nombre':'Caja de prueba','lista':'REMATE'})['id'];session=c.value('/api/comercial/sesiones/abrir',{'canal':'expendios','empresa':c.company,'caja':box,'modo':'TICKETS'})
  doc=c.value('/api/comercial/cobrar',{'canal':'expendios','empresa':c.company,'sesion':session['id'],'clave':uuid.uuid4().hex,'partidas':[{'sku':data['sku'],'cantidad':'1'}]})['documento'];self.assertEqual(doc['total'],'70.00')

if __name__=='__main__':unittest.main()
