import base64,contextlib,hashlib,json,secrets,sqlite3,unittest
import test_backup_import as fixtures

class EnterpriseTests(unittest.TestCase):
 setUp=fixtures.ModuleBackupTests.setUp;tearDown=fixtures.ModuleBackupTests.tearDown;call=fixtures.ModuleBackupTests.call;value=fixtures.ModuleBackupTests.value;login=fixtures.ModuleBackupTests.login
 def test_edition_owner_only_and_area_layout_review_is_atomic(self):
  self.value('/api/users',{'email':'aux@example.test','name':'Auxiliar','role':'auxti','password':self.password,'active':True});aux=self.login('aux@example.test')
  self.assertEqual(self.call('/api/empresa/edicion',{'edicion':'avanzada'},aux)[0],403);self.value('/api/empresa/edicion',{'edicion':'avanzada'});self.assertEqual(self.value('/api/me')['app']['edicion']['nombre'],'Avanzada')
  from catalog_loads import workbook
  content=base64.b64encode(workbook('AREAS',{'A':'NOMBRE'},[{'A':'Área prueba layout'}])).decode();data={'modulo':'areas','contenido':content};review=self.value('/api/empresa/cargas',{**data,'revisar':True});self.assertNotIn('Área prueba layout',self.value('/api/requisiciones/meta')['areas']);self.value('/api/empresa/cargas',{**data,'huellaActual':review['huellaActual'],'huellaArchivo':review['huellaArchivo']});self.assertIn('Área prueba layout',self.value('/api/requisiciones/meta')['areas'])
 def test_contract_is_owner_only_and_applies_to_existing_sessions(self):
  self.value('/api/users',{'email':'seller@example.test','name':'Vendedor','role':'ventas','password':self.password,'active':True});seller=self.login('seller@example.test');self.assertIn('ventas',self.value('/api/me',actor=seller)['user']['modulos'])
  self.assertEqual(self.call('/api/empresa/modulos',actor=seller)[0],403);self.assertEqual(self.call('/api/empresa/modulos',{'revision':0,'modules':['ventas']},seller)[0],403)
  self.value('/api/empresa/modulos',{'revision':0,'modules':['calidad']});self.assertEqual(self.value('/api/me',actor=seller)['user']['modulos'],[]);self.assertIn('ventas',self.value('/api/me')['user']['modulos']);self.assertEqual(self.call('/api/empresa/modulos',{'revision':0,'modules':['ventas']})[0],409)
 def token(self):
  token=secrets.token_urlsafe(28);salt=secrets.token_hex(16);(self.store.directory/'activation-verifier.json').write_text(json.dumps({'salt':salt,'token_hash':hashlib.pbkdf2_hmac('sha256',token.encode(),bytes.fromhex(salt),310000).hex()}),encoding='utf8');return token
 def test_company_revision_branches_and_private_activation(self):
  config=self.value('/api/empresa/config');self.assertNotIn('EJIDOS',[b['nombre'] for b in config['sucursales']]);self.value('/api/empresa/config',{'revision':1,'nombre':'Empresa ficticia','rubro':'Servicios','responsable':'Responsable de prueba'})
  self.assertEqual(self.call('/api/empresa/config',{'revision':1,'nombre':'Otra','rubro':'Otro','responsable':'Otro'})[0],409)
  self.value('/api/empresa/sucursales',{'nombre':'BODEGA PRUEBA','serie':'REQ-BOD'});self.assertIn('BODEGA PRUEBA',[b['nombre'] for b in self.value('/api/empresa/config')['sucursales']]);self.assertEqual(self.call('/api/empresa/sucursales',{'nombre':'OTRA','serie':'REQ-BOD'})[0],400)
  token=self.token();self.assertEqual(self.call('/api/empresa/activar',{'token':'incorrecto-1234567890'})[0],403);self.value('/api/empresa/activar',{'token':token});body=json.dumps(self.value('/api/empresa/config'));self.assertNotIn(token,body);self.assertNotIn('token_hash',body);self.assertTrue(json.loads(body)['activacion']['activa'])
 def test_activation_is_owner_only_and_gates_other_users(self):
  self.value('/api/users',{'email':'aux@example.test','name':'Auxiliar','role':'auxti','password':self.password,'active':True});aux=self.login('aux@example.test');token=self.token()
  self.assertEqual(self.call('/api/empresa/activar',{'token':token},aux)[0],403);self.store.require_activation=True;self.assertEqual(self.call('/api/me',actor=aux)[0],403);self.value('/api/empresa/activar',{'token':token});self.assertEqual(self.call('/api/me',actor=aux)[0],200)
 def test_reset_requires_review_password_and_preserves_owner_and_activation(self):
  self.value('/api/empresa/activar',{'token':self.token()});self.value('/api/calidad/guardar',{'modulo':'documents','codigo':'D1','titulo':'Documento','datos':{}});self.value('/api/users',{'email':'otro@example.test','name':'Otro','role':'visualizador','password':self.password,'active':True})
  review=self.value('/api/empresa/restablecer',{});data={'aplicar':True,'confirmar':True,'texto':'RESTABLECER TODO','huellaActual':review['huellaActual'],'password':'incorrecta'}
  self.assertEqual(self.call('/api/empresa/restablecer',data)[0],403);self.assertEqual(len(self.value('/api/calidad/registros')['registros']),1)
  result=self.value('/api/empresa/restablecer',{**data,'password':self.password});backup=self.store.directory/'respaldos'/result['respaldoPrevio'];self.assertTrue(backup.exists())
  with contextlib.closing(sqlite3.connect(backup)) as db:self.assertEqual(db.execute('SELECT count(*) FROM q_items').fetchone()[0],1)
  self.assertEqual(self.value('/api/calidad/registros')['registros'],[]);self.assertTrue(self.value('/api/empresa/config')['activacion']['activa']);self.assertEqual(len(self.value('/api/users')['users']),0);self.assertEqual(self.value('/api/catalogo')['state']['registros'],[]);self.assertEqual(self.value('/api/comercial/meta')['empresas'],[])
 def test_reset_rejects_stale_preview_and_layouts_are_available(self):
  review=self.value('/api/empresa/restablecer',{});self.value('/api/calidad/guardar',{'modulo':'documents','codigo':'D1','titulo':'Documento','datos':{}})
  self.assertEqual(self.call('/api/empresa/restablecer',{'aplicar':True,'confirmar':True,'texto':'RESTABLECER TODO','huellaActual':review['huellaActual'],'password':self.password})[0],409)
  layouts=self.value('/api/empresa/layouts')['layouts'];self.assertGreaterEqual(len(layouts),17)
  for item in layouts:self.assertEqual(self.call(item['url'])[0],200,item['id'])

if __name__=='__main__':unittest.main()
