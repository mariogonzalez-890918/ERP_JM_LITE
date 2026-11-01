import base64,json,unittest
import test_backup_import as fixtures
from catalog_loads import workbook,SALES

class InitialLoadsTests(unittest.TestCase):
 setUp=fixtures.ModuleBackupTests.setUp;tearDown=fixtures.ModuleBackupTests.tearDown;call=fixtures.ModuleBackupTests.call;value=fixtures.ModuleBackupTests.value;login=fixtures.ModuleBackupTests.login
 def load(self,module,content,companies=None,review=None):
  data={'modulo':module,'contenido':content,'empresas':companies or []}
  return self.value('/api/empresa/cargas',{**data,**({'huellaActual':review['huellaActual'],'huellaArchivo':review['huellaArchivo']} if review else {'revisar':True})})
 def test_purchase_preview_and_apply_link_same_sku_to_materials(self):
  content=fixtures.workbook([fixtures.product()]);review=self.load('compras',content);self.assertEqual(self.value('/api/catalogo')['state']['registros'],[]);self.assertEqual(self.value('/api/requisiciones/materiales')['materiales'],[])
  self.load('compras',content,review=review);product=self.value('/api/catalogo')['state']['registros'][0];material=self.value('/api/requisiciones/materiales')['materiales'][0];self.assertEqual(product['sku'],material['sku'])
 def sales(self,price='116',channel='AMBOS'):
  rows=[{'A':'PTPD05PRUEBA00','B':'PT','C':'PD','D':'05','F':'A01','G':'SI','H':'PRODUCTO FICTICIO','I':price,'J':'116','K':'116','N':'16','O':'PIEZA','S':'ACTIVO','W':channel}];return base64.b64encode(workbook('SUGERIDO',SALES,rows)).decode()
 def test_tpv_channel_name_accepts_the_new_label_without_institutional_products(self):
  company=self.value('/api/comercial/empresas',{'nombre':'Empresa TPV de prueba','sucursales':['CENTRAL']})['id'];content=self.sales(channel='TPV');review=self.load('pdv',content,[company]);self.load('pdv',content,[company],review);self.assertEqual(len(self.value('/api/comercial/productos?canal=expendios&empresa='+str(company))['productos']),1);self.assertEqual(self.value('/api/comercial/productos?canal=ventasins&empresa='+str(company))['productos'],[])
 def test_sales_and_pdv_share_sku_and_prices_without_preview_writes(self):
  company=self.value('/api/comercial/empresas',{'nombre':'Empresa de prueba','sucursales':['CENTRAL']})['id'];content=self.sales();review=self.load('pdv',content,[company]);self.assertEqual(self.value('/api/ventas')['state']['registros'],[])
  self.load('pdv',content,[company],review);sku=self.value('/api/ventas')['state']['registros'][0]['sku'];products=self.value('/api/comercial/productos?canal=expendios&empresa='+str(company))['productos'];self.assertEqual(products[0]['sku'],sku);self.assertEqual(products[0]['precios']['REMATE'],'116');self.assertNotIn('DESPACHO',products[0]['precios'])
 def test_invalid_prices_rollback_catalog_and_quality_bulk_preview(self):
  company=self.value('/api/comercial/empresas',{'nombre':'Empresa de prueba','sucursales':['CENTRAL']})['id'];self.assertEqual(self.call('/api/empresa/cargas',{'modulo':'ventas','contenido':self.sales(''),'empresas':[company],'revisar':True})[0],400);self.assertEqual(self.value('/api/ventas')['state']['registros'],[])
  content=base64.b64encode(workbook('DOCUMENTOS',{'A':'CODIGO','B':'TITULO','C':'DATOS_JSON'},[{'A':'D-001','B':'Ejemplo','C':'{}'}])).decode();review=self.load('documentos',content);self.assertEqual(self.value('/api/calidad/registros')['registros'],[]);self.load('documentos',content,review=review);self.assertEqual(len(self.value('/api/calidad/registros')['registros']),1)
 def test_explicit_sku_destinations_are_reviewed_and_reach_crm_without_pdv(self):
  company=self.value('/api/comercial/empresas',{'nombre':'Empresa de prueba','sucursales':['CENTRAL']})['id'];data={'modulo':'ventas','contenido':self.sales(),'empresas':[company],'destinos':['ventasins']};review=self.value('/api/empresa/cargas',{**data,'revisar':True});apply={**data,'huellaActual':review['huellaActual'],'huellaArchivo':review['huellaArchivo']}
  self.assertEqual(self.call('/api/empresa/cargas',{**apply,'destinos':['expendios']})[0],409);self.value('/api/empresa/cargas',apply)
  self.assertEqual(self.value('/api/comercial/productos?canal=expendios&empresa='+str(company))['productos'],[]);products=self.value('/api/crm/meta?empresa='+str(company))['productos'];self.assertEqual(len(products),1)
  opportunity={'empresa':company,'titulo':'Prospecto con producto','sku':products[0]['sku']};id=self.value('/api/crm/oportunidades',opportunity)['id'];self.assertEqual(self.value('/api/crm/oportunidades?empresa='+str(company))['oportunidades'][0]['sku'],products[0]['sku']);self.assertEqual(self.call('/api/crm/oportunidades',{**opportunity,'sku':'NOEXISTE'})[0],400)

if __name__=='__main__':unittest.main()
