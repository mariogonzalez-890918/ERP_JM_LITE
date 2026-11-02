"""Pruebas de instalacion comercial con datos ficticios y procesos aislados."""
import contextlib,importlib.util,json,os,pathlib,queue,re,secrets,shutil,socket,subprocess,sys,tempfile,threading,time,unittest,urllib.request
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'sku-servidor'))
import server
spec=importlib.util.spec_from_file_location('initializer',ROOT/'tools/inicializar.py');initializer=importlib.util.module_from_spec(spec);spec.loader.exec_module(initializer)

class CommercialInstall(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name);self.password=secrets.token_urlsafe(20)
  initializer.create_initials(self.root,self.password);shutil.copy2(ROOT/'sku-servidor/catalogos.json',self.root/'catalogos.json')
 def test_owner_cannot_be_disabled_demoted_or_modified_by_auxiliary(self):
  with patch.object(server,'ROOT',self.root):
   store=server.Store(self.root/'data');actor={'role':'superadmin','email':server.ADMIN_EMAIL}
   self.assertEqual(server.ADMIN_EMAIL,'mario.gonzalez@jad-ayt.com')
   for role,active in [('superadmin',False),('visualizador',True)]:
    with self.assertRaises(ValueError):store.manage_user({'email':server.ADMIN_EMAIL,'name':server.ADMIN_NAME,'role':role,'active':active},actor)
   with self.assertRaises(PermissionError):store.manage_user({'email':server.ADMIN_EMAIL,'name':'Otro','role':'superadmin','active':True,'password':'Replacement-123'}, {'role':'auxti','email':'aux@example.test'})
   reopened=server.Store(self.root/'data',initial_admin={'salt':'00'*16,'password_hash':'00'*32})
   self.assertTrue(reopened.login(server.ADMIN_EMAIL,self.password,'127.0.0.1'))
 def test_port_assignment_bom_config_and_access_survive_process_restart(self):
  for path in (ROOT/'sku-servidor').glob('*.py'):shutil.copy2(path,self.root/path.name)
  shutil.copytree(ROOT/'sku-servidor/public',self.root/'public')
  config=self.root/'config.json';config.write_text(json.dumps({'host':'127.0.0.1','port':0,'data_dir':'relative-data'}),encoding='utf-8-sig')
  for attempt in range(2):
   process=subprocess.Popen([sys.executable,str(self.root/'server.py'),'--config',str(config)],cwd=self.root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',env={**os.environ,'PYTHONIOENCODING':'utf8'})
   lines=queue.Queue()
   def collect(stream):
    for line in stream:lines.put(line)
   reader=threading.Thread(target=collect,args=(process.stdout,),daemon=True);reader.start();captured=[];url=None;deadline=time.monotonic()+45
   try:
    while time.monotonic()<deadline:
     try:line=lines.get(timeout=1)
     except queue.Empty:
      if process.poll() is not None:break
      continue
     captured.append(line);match=re.search(r'Local: (http://127\.0\.0\.1:\d+)',line)
     if match:url=match[1];break
    self.assertIsNotNone(url,''.join(captured));self.assertNotEqual(url,'http://127.0.0.1:0')
    with urllib.request.urlopen(url+'/logo.svg') as response:self.assertIn(b'<svg',response.read())
    request=urllib.request.Request(url+'/api/login',data=json.dumps({'email':server.ADMIN_EMAIL,'password':self.password}).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request) as response:cookie=response.headers['Set-Cookie'].split(';')[0]
    with urllib.request.urlopen(urllib.request.Request(url+'/api/me',headers={'Cookie':cookie})) as response:me=json.load(response)
    self.assertEqual(me['user']['role'],'superadmin');self.assertEqual(me['user']['name'],'Mario González')
    self.assertTrue((self.root/'relative-data/sku.sqlite3').is_file())
   finally:
    if process.poll() is None:process.terminate()
    process.wait(timeout=15);reader.join(timeout=5);process.stdout.close()
 def test_unattended_seed_is_not_accepted_for_normal_start(self):
  result=subprocess.run([sys.executable,str(ROOT/'sku-servidor/server.py'),'--admin-seed',str(self.root/'initial-admin.json')],capture_output=True,timeout=15)
  self.assertNotEqual(result.returncode,0);self.assertIn(b'--initialize',result.stderr)
 def test_default_network_binding_and_busy_port_fail_without_fallback(self):
  config=self.root/'network-config.json'
  command=[sys.executable,str(ROOT/'sku-servidor/server.py'),'--config',str(config),'--data-dir',str(self.root/'network-data')]
  result=subprocess.run(command+['--initialize','--admin-seed',str(self.root/'initial-admin.json')],capture_output=True,timeout=30)
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertEqual(json.loads(config.read_text()),{'host':'0.0.0.0','port':8098})
  with socket.socket() as occupied:
   occupied.bind(('127.0.0.1',0));occupied.listen()
   result=subprocess.run(command+['--host','127.0.0.1','--port',str(occupied.getsockname()[1])],capture_output=True,timeout=30)
  self.assertNotEqual(result.returncode,0);self.assertIn(b'No se utilizara otro puerto',result.stderr)

if __name__=='__main__':unittest.main()
