import base64,contextlib,hashlib,io,json,pathlib,sqlite3,tempfile,unittest,zipfile
import test_purchase_v3 as cases

class GeneralBackupTests(unittest.TestCase):
 def setUp(self):
  self.c=cases.PurchaseV3Tests();self.c.setUp();self.addCleanup(self.c.tearDown)
 def test_complete_snapshot_integrity_configuration_and_session_exclusion(self):
  c=self.c
  item=c.value('/api/calidad/guardar',{'modulo':'documents','codigo':'Q-1','titulo':'Calidad','datos':{}})['id']
  c.value('/api/calidad/archivo',{'id':item,'revision':1,'nombre':'evidencia.txt','contenido':base64.b64encode(b'evidencia respaldo').decode()})
  with c.store.connect() as db:
   db.execute("INSERT INTO app_meta VALUES('company_logo:test',?)",(json.dumps({'imagen':'logo-de-prueba'}),))
  with contextlib.closing(sqlite3.connect(c.store.path)) as writer:
   writer.execute('PRAGMA journal_mode=WAL');writer.execute("INSERT INTO app_meta VALUES('general_backup_wal','persistido')");writer.commit()
   status,raw,headers=c.call('/api/respaldos/general')
  self.assertEqual(status,200);self.assertIn('application/zip',headers['Content-Type']);self.assertIn('attachment;',headers['Content-Disposition'])
  with zipfile.ZipFile(io.BytesIO(raw)) as archive:
   self.assertIsNone(archive.testzip());manifest=json.loads(archive.read('manifest.json'));self.assertEqual(manifest['formato'],'JM-RESPALDO-GENERAL')
   for name,digest in manifest['archivos'].items():self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),digest)
   config=json.loads(archive.read('config.json'));self.assertEqual(config['port'],8098);self.assertEqual(config['data_dir'],'data')
   with tempfile.TemporaryDirectory() as folder:
    target=pathlib.Path(folder)/'copy.sqlite3';target.write_bytes(archive.read('data/sku.sqlite3'))
    with contextlib.closing(sqlite3.connect(target)) as db:
     self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertGreater(db.execute('SELECT count(*) FROM cm_companies').fetchone()[0],0);self.assertGreater(db.execute('SELECT count(*) FROM req_materials').fetchone()[0],0);self.assertEqual(db.execute('SELECT count(*) FROM q_items').fetchone()[0],1);self.assertIn('logo-de-prueba',db.execute("SELECT value FROM app_meta WHERE key='company_logo:test'").fetchone()[0]);self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],0);self.assertGreater(db.execute('SELECT count(*) FROM users').fetchone()[0],0)
     self.assertEqual(db.execute("SELECT value FROM app_meta WHERE key='general_backup_wal'").fetchone()[0],'persistido');self.assertEqual(db.execute('SELECT content FROM q_files').fetchone()[0],b'evidencia respaldo')
  self.assertEqual(c.value('/api/me')['user']['role'],'superadmin')
 def test_only_internal_owner_can_export_all_companies_and_security(self):
  c=self.c;self.assertEqual(c.call('/api/respaldos/general',actor=c.buyer)[0],403)
  c.value('/api/users',{'email':'aux@example.test','name':'Auxiliar','role':'auxti','password':c.password,'active':True});self.assertEqual(c.call('/api/respaldos/general',actor=c.login('aux@example.test'))[0],403)

if __name__=='__main__':unittest.main()
