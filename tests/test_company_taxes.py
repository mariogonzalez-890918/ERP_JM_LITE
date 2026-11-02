import unittest
import test_purchase_v3 as purchase_cases

class CompanyTaxesTests(unittest.TestCase):
 def setUp(self):
  self.c=purchase_cases.PurchaseV3Tests();self.c.setUp();self.addCleanup(self.c.tearDown)
 def test_purchase_tax_scope_override_and_historical_amounts(self):
  c=self.c;company=c.company;config='/api/empresa/impuestos';data={'empresa':company,'nombre':'Impuesto prueba','tasa':'5.5'}
  self.assertEqual(c.call(config,data,c.buyer)[0],403);tax=c.value(config,data)['id']
  other=c.value('/api/comercial/empresas',{'nombre':'Empresa alternativa','sucursales':['CENTRAL']})['id'];self.assertEqual(c.value(config+'?empresa='+str(other))['impuestos'],[])
  link={'empresa':company,'vincular':True,'ambito':'compras','sku':c.material['sku'],'impuesto':tax};c.value(config,link)
  self.assertEqual(c.po('materiales',actor=c.buyer)['materiales'][0]['impuesto'],'5.5');doc=c.order();self.assertEqual(doc['total'],'211.00');self.assertEqual(doc['partidas'][0]['tipoImpuesto'],'Impuesto prueba')
  c.value(config,{**data,'id':tax,'revision':1,'tasa':'10'});self.assertEqual(c.po('documento',extra='&id='+doc['id'])['total'],'211.00');self.assertEqual(c.order()['total'],'220.00')
  self.assertEqual(c.call(config,{**link,'empresa':other})[0],400);self.assertEqual(c.call(config,{**data,'tasa':'NaN'})[0],400)
 def test_sales_product_uses_company_tax(self):
  c=self.c;tax=c.value('/api/empresa/impuestos',{'empresa':c.company,'nombre':'Traslado especial','tasa':'5.5'})['id'];sku='010101TEST0001'
  c.value('/api/comercial/productos',{'empresa':c.company,'sku':sku,'nombre':'Producto configurable','unidad':'PIEZA','canales':['ventasins'],'impuestoId':tax,'precios':{'PUBLICO':'105.50'}})
  product=next(p for p in c.value('/api/comercial/productos?empresa='+str(c.company))['productos'] if p['sku']==sku);self.assertEqual(product['iva'],'5.5');self.assertEqual(product['impuestoId'],tax)
  from comercial import tax_line
  line=tax_line('1','105.50',product['iva']);self.assertEqual(line['base'],'100.00');self.assertEqual(line['impuesto'],'5.50')
  import uuid
  doc=c.value('/api/comercial/pedidos',{'empresa':c.company,'sucursal':'CENTRAL','clave':uuid.uuid4().hex,'partidas':[{'sku':sku,'cantidad':'1'}]})['documento'];self.assertEqual(doc['base'],'100.00');self.assertEqual(doc['partidas'][0]['tipoImpuesto'],'Traslado especial')
  c.value('/api/empresa/impuestos',{'empresa':c.company,'id':tax,'revision':1,'nombre':'Nueva tasa','tasa':'10'})
  self.assertEqual(c.value('/api/comercial/documento?id='+doc['id'])['impuesto'],'5.50')

if __name__=='__main__':unittest.main()
