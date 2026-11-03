import contextlib,hashlib,io,json,pathlib,sqlite3,tempfile,threading,unittest,urllib.request,urllib.error,zipfile
from unittest.mock import patch
import test_purchase_v3 as cases

class GeneralRestoreTests(unittest.TestCase):
 def setUp(self):
  self.c=cases.PurchaseV3Tests();self.c.setUp();self.addCleanup(self.c.tearDown)
 def upload(self,raw,actor=None):
  c=self.c;actor=actor or c.admin
  request=urllib.request.Request(c.url+'/api/respaldos/general/restaurar/revisar',data=raw,headers={'Content-Type':'application/zip','Cookie':actor['cookie'],'X-CSRF-Token':actor['csrf']})
  try:
   with urllib.request.urlopen(request,timeout=60) as response:return response.status,json.load(response)
  except urllib.error.HTTPError as error:return error.code,json.load(error)
 def snapshot(self):
  status,raw,_=self.c.call('/api/respaldos/general');self.assertEqual(status,200);return raw
 def marker(self,value):
  with self.c.store.connect() as db:db.execute("INSERT OR REPLACE INTO app_meta VALUES('restore_test',?)",(value,))
 def get_marker(self):
  with self.c.store.connect() as db:return db.execute("SELECT value FROM app_meta WHERE key='restore_test'").fetchone()[0]
 def confirm(self,review,**extra):
  return self.c.call('/api/respaldos/general/restaurar/confirmar',{'id':review['id'],'texto':'RESTAURAR TODO','confirmar':True,'password':self.c.password,**extra})
 def db_from_zip(self,raw):
  with zipfile.ZipFile(io.BytesIO(raw)) as archive,tempfile.TemporaryDirectory() as folder:
   path=pathlib.Path(folder)/'db.sqlite3';path.write_bytes(archive.read('data/sku.sqlite3'))
   with contextlib.closing(sqlite3.connect(path)) as db:return db.execute("SELECT value FROM app_meta WHERE key='restore_test'").fetchone()[0]
 def test_complete_restore_previous_zip_and_sessions_invalidated(self):
  import base64
  c=self.c;item=c.value('/api/calidad/guardar',{'modulo':'documents','codigo':'RESTAURAR-Q','titulo':'Archivo original','datos':{}})['id'];c.value('/api/calidad/archivo',{'id':item,'revision':1,'nombre':'evidencia.txt','contenido':base64.b64encode(b'archivo original').decode()})
  self.marker('RESPALDO');raw=self.snapshot();self.marker('ACTUAL');c.value('/api/empresa/sucursales',{'nombre':'TEMPORAL','serie':'TEMP-TEST'})
  status,review=self.upload(raw);self.assertEqual(status,200,review);self.assertEqual(self.get_marker(),'ACTUAL')
  status,body,_=self.confirm(review);self.assertEqual(status,200,body);result=json.loads(body);self.assertEqual(self.get_marker(),'RESPALDO');self.assertEqual(c.call('/api/me')[0],401)
  c.admin=c.login('mario.gonzalez@jad-ayt.com');status,previous,_=c.call('/api/respaldos/general/previo/'+result['respaldoPrevio']);self.assertEqual(status,200);self.assertEqual(self.db_from_zip(previous),'ACTUAL');self.assertEqual(self.confirm(review)[0],409)
  self.assertEqual(len(c.po('materiales')['materiales']),1)
  import requisiciones
  self.assertNotIn('TEMPORAL',requisiciones.BRANCHES)
  with c.store.connect() as db:self.assertFalse(json.loads(db.execute('SELECT payload FROM cm_source').fetchone()[0])['habilitada']);self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertEqual(db.execute('SELECT content FROM q_files').fetchone()[0],b'archivo original')
 def test_stale_review_wrong_password_and_confirmation_do_not_restore(self):
  self.marker('RESPALDO');raw=self.snapshot();self.marker('ACTUAL');status,review=self.upload(raw);self.assertEqual(status,200)
  self.assertEqual(self.confirm(review,password='incorrecta')[0],403);self.assertEqual(self.confirm(review,texto='RESTAURAR')[0],400);self.assertEqual(self.get_marker(),'ACTUAL')
  self.marker('CAMBIO POSTERIOR');self.assertEqual(self.confirm(review)[0],409);self.assertEqual(self.get_marker(),'CAMBIO POSTERIOR')
 def test_only_systems_can_review_confirm_and_download_previous(self):
  c=self.c;raw=self.snapshot();self.assertEqual(self.upload(raw,c.buyer)[0],403)
  c.value('/api/users',{'email':'aux@example.test','name':'Auxiliar','role':'auxti','password':c.password,'active':True});aux=c.login('aux@example.test');self.assertEqual(self.upload(raw,aux)[0],403)
  self.assertEqual(c.call('/api/respaldos/general/restaurar/confirmar',{'texto':'RESTAURAR TODO'},aux)[0],403)
  self.assertEqual(c.call('/api/respaldos/general/previo/'+'a'*32,actor=aux)[0],403)
 def test_corrupt_hash_traversal_and_schema_changes_rejected(self):
  raw=self.snapshot()
  for mode in ('hash','traversal','schema'):
   out=io.BytesIO()
   with zipfile.ZipFile(io.BytesIO(raw)) as source:
    files={n:source.read(n) for n in source.namelist()};manifest=json.loads(files['manifest.json'])
   if mode=='hash':files['config.json']+=b' '
   elif mode=='traversal':files['../outside.txt']=b'bad'
   else:
    with tempfile.TemporaryDirectory() as folder:
     path=pathlib.Path(folder)/'db.sqlite3';path.write_bytes(files['data/sku.sqlite3'])
     with contextlib.closing(sqlite3.connect(path)) as db:db.execute('CREATE TABLE unwanted(id)');db.commit()
     files['data/sku.sqlite3']=path.read_bytes()
    manifest['archivos']['data/sku.sqlite3']=hashlib.sha256(files['data/sku.sqlite3']).hexdigest();files['manifest.json']=json.dumps(manifest).encode()
   with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as target:
    for name,value in files.items():target.writestr(name,value)
   status,error=self.upload(out.getvalue());self.assertEqual(status,400,(mode,error))
 def test_failure_after_apply_rolls_back_database_and_live_session(self):
  self.marker('RESPALDO');raw=self.snapshot();self.marker('ACTUAL');status,review=self.upload(raw);self.assertEqual(status,200)
  restore=self.c.http.RequestHandlerClass.restore_general
  with patch.object(restore,'refresh',side_effect=[RuntimeError('fallo simulado'),None]):self.assertEqual(self.confirm(review)[0],500)
  self.assertEqual(self.get_marker(),'ACTUAL');self.assertEqual(self.c.value('/api/me')['user']['role'],'superadmin')
  with self.c.store.connect() as db:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
 def test_restore_waits_for_active_operations_and_blocks_new_writes(self):
  gate=self.c.store.maintenance;entered=threading.Event();release=threading.Event();written=threading.Event()
  def active():
   with gate.shared():entered.set();release.wait(5)
  thread=threading.Thread(target=active);thread.start();self.assertTrue(entered.wait(2))
  from requisiciones import Conflict
  with self.assertRaises(Conflict):
   with gate.exclusive(timeout=.05):pass
  release.set();thread.join(2)
  def writer():
   self.marker('POSTERIOR');written.set()
  with gate.exclusive():
   pending=threading.Thread(target=writer);pending.start();self.assertFalse(written.wait(.1))
   with self.c.store.connect() as db:self.assertEqual(db.execute('SELECT 1').fetchone()[0],1)
  pending.join(2);self.assertTrue(written.is_set());self.assertEqual(self.get_marker(),'POSTERIOR')
 def test_credentials_and_activation_verifier_recovered_from_zip(self):
  import secrets,server
  c=self.c;self.marker('RESPALDO');verifier=c.store.directory/'activation-verifier.json';original={'salt':secrets.token_hex(16),'token_hash':secrets.token_hex(32)};verifier.write_text(json.dumps(original));raw=self.snapshot();old_password=c.password;c.password=secrets.token_urlsafe(20)
  with c.store.connect() as db:
   salt,digest=server.new_password(c.password);db.execute('UPDATE users SET salt=?,password_hash=? WHERE email=?',(salt,digest,server.ADMIN_EMAIL))
  verifier.write_text(json.dumps({'salt':secrets.token_hex(16),'token_hash':secrets.token_hex(32)}))
  status,review=self.upload(raw);self.assertEqual(status,200,review);self.assertEqual(self.confirm(review)[0],200);self.assertEqual(json.loads(verifier.read_text()),original)
  c.password=old_password;c.admin=c.login(server.ADMIN_EMAIL)


 def test_legacy_single_warehouse_backup_is_upgraded_only_in_staging(self):
  from almacenes_config import LEGACY_SCHEMA
  raw=self.snapshot()
  with zipfile.ZipFile(io.BytesIO(raw)) as source:files={name:source.read(name) for name in source.namelist()}
  with tempfile.TemporaryDirectory() as folder:
   path=pathlib.Path(folder)/'legacy.sqlite3';path.write_bytes(files['data/sku.sqlite3'])
   with contextlib.closing(sqlite3.connect(path)) as db:
    
    from operaciones_base import SCHEMA
    for name,sql in SCHEMA.items():db.execute('DROP '+('TRIGGER' if 'TRIGGER' in sql[:40] else 'TABLE')+' IF EXISTS '+name)
    rows=db.execute('SELECT * FROM inv_warehouses').fetchall();db.execute('DROP TABLE inv_warehouses');db.execute(LEGACY_SCHEMA);db.executemany('INSERT INTO inv_warehouses VALUES(?,?,?,?,?,?)',rows);db.commit()
   files['data/sku.sqlite3']=path.read_bytes()
  manifest=json.loads(files['manifest.json']);manifest['archivos']['data/sku.sqlite3']=hashlib.sha256(files['data/sku.sqlite3']).hexdigest();files['manifest.json']=json.dumps(manifest).encode()
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as target:
   for name,value in files.items():target.writestr(name,value)
  c=self.c;new=c.value('/api/inventarios/almacenes',{'empresa':c.company,'sucursal':'CENTRAL','nombre':'Almacén posterior al respaldo','funcion':'PT'})['almacen'];status,review=self.upload(out.getvalue());self.assertEqual(status,200,review)
  self.assertIn(new['id'],[w['id'] for w in c.value('/api/inventarios/meta')['almacenes']])
  self.assertEqual(self.confirm(review)[0],200);c.admin=c.login('mario.gonzalez@jad-ayt.com')
  restored=c.value('/api/inventarios/almacenes',{'empresa':c.company,'sucursal':'CENTRAL','nombre':'Almacén tras restauración','funcion':'PT'})['almacen'];self.assertNotEqual(restored['id'],str(c.company)+':CENTRAL')

if __name__=='__main__':unittest.main()
