import json,pathlib,unittest
import test_backup_import as fixtures

class TaxonomyTests(unittest.TestCase):
 tearDown=fixtures.ModuleBackupTests.tearDown;call=fixtures.ModuleBackupTests.call;value=fixtures.ModuleBackupTests.value;login=fixtures.ModuleBackupTests.login
 def setUp(self):
  fixtures.ModuleBackupTests.setUp(self)
  with self.store.connect() as db:db.execute('DELETE FROM sku_taxonomy')
  self.store.taxonomy.reload()
 def tax(self,scope,kind,code,label,revision=0,**extra):return self.value('/api/empresa/taxonomia',{'ambito':scope,'grupo':kind,'codigo':code,'nombre':label,'revision':revision,**extra})
 def test_empty_classifications_for_new_product_and_runtime_catalogs(self):
  self.assertEqual(self.value('/api/empresa/taxonomia')['clasificaciones'],[])
  catalog=self.value('/api/me')['catalogos'];self.assertEqual(catalog['compras'],{'TIP':{},'CAT':{},'SUB':{}});self.assertTrue(all(not v for v in catalog['ventas'].values()))
  self.tax('compras','TIP','AA','Tipo propio');self.tax('compras','CAT','BB','Categoría propia');self.tax('compras','SUB','CC','Subcategoría propia');self.tax('ventas','PDV','Z01','Grupo propio de caja')
  self.assertEqual(self.value('/api/me')['catalogos']['compras']['CAT'],{'BB':'Categoría propia'});self.assertEqual(self.value('/api/me')['catalogos']['ventas']['PDV'],{'Z01':'Grupo propio de caja'})
 def test_rename_preserves_used_sku_and_used_code_cannot_be_removed(self):
  for kind,code in [('TIP','AA'),('CAT','BB'),('SUB','CC')]:self.tax('compras',kind,code,code)
  content=fixtures.workbook([fixtures.product(E='AA',F='BB',G='CC')]);review=self.value('/api/empresa/cargas',{'modulo':'compras','contenido':content,'revisar':True});self.value('/api/empresa/cargas',{'modulo':'compras','contenido':content,'huellaActual':review['huellaActual'],'huellaArchivo':review['huellaArchivo']});sku=self.value('/api/catalogo')['state']['registros'][0]['sku']
  self.tax('compras','CAT','BB','Nombre corregido',1);self.assertEqual(self.value('/api/catalogo')['state']['registros'][0]['sku'],sku)
  self.assertEqual(self.call('/api/empresa/taxonomia',{'ambito':'compras','grupo':'CAT','codigo':'BB','nombre':'Nombre corregido','revision':2,'eliminar':True})[0],400)
  self.assertEqual(self.call('/api/empresa/taxonomia',{'ambito':'compras','grupo':'CAT','codigo':'BB','nombre':'Viejo','revision':1})[0],409)
 def test_only_superadmin_configures_and_empty_categories_block_import(self):
  self.assertEqual(self.call('/api/compras/importar',{'archivo':'PRUEBA.xlsx','contenido':fixtures.workbook([fixtures.product()]),'revision':1})[0],400)
  self.value('/api/users',{'email':'aux@example.test','name':'Aux','role':'auxti','password':self.password,'active':True});aux=self.login('aux@example.test');self.assertEqual(self.call('/api/empresa/taxonomia',{'ambito':'compras','grupo':'TIP','codigo':'AA','nombre':'No permitido'},aux)[0],403)

if __name__=='__main__':unittest.main()
