import json,secrets,time,unittest
import test_backup_import as fixtures
import server
from auth_security import totp,protect

class SecurityTests(unittest.TestCase):
 setUp=fixtures.ModuleBackupTests.setUp;tearDown=fixtures.ModuleBackupTests.tearDown;call=fixtures.ModuleBackupTests.call;value=fixtures.ModuleBackupTests.value;login=fixtures.ModuleBackupTests.login
 def test_internal_accounts_hidden_immutable_and_second_private_login(self):
  salt,digest=server.new_password(self.password);server.Store(self.store.directory,initial_admin={'salt':salt,'password_hash':digest,'internal_emails':['internal@example.test']})
  self.assertEqual(self.value('/api/users')['users'],[])
  for email in (server.ADMIN_EMAIL,'internal@example.test'):
   self.assertEqual(self.call('/api/users',{'email':email,'name':'No permitido','role':'visualizador','password':'abcd','active':False})[0],400)
  actor=self.login('internal@example.test');self.assertTrue(self.value('/api/me',actor=actor)['user']['internalAdmin']);self.assertTrue(self.value('/api/empresa/config',actor=actor)['puedeActivar'])
  for path in ('/api/comercial/accesos','/api/pedidoscompra/accesos'):self.assertEqual(self.value(path)['usuarios'],[])
 def test_totp_activation_replay_recovery_and_disable(self):
  self.assertEqual(self.value('/api/seguridad/estado')['habilitado'],False)
  pending=self.value('/api/seguridad/preparar',{'password':self.password});secret=pending['secreto'];counter=int(time.time()//30)
  result=self.value('/api/seguridad/confirmar',{'codigo':totp(secret,counter)});self.assertEqual(len(result['codigosRecuperacion']),8)
  with self.store.connect() as db:row=db.execute('SELECT secret,recovery FROM user_2fa').fetchone()
  self.assertNotIn(secret,row[0]);self.assertEqual(protect(row[0],True),secret);self.assertNotIn(result['codigosRecuperacion'][0],row[1])
  self.assertIsNone(self.store.login(server.ADMIN_EMAIL,self.password,'test-no-code'))
  self.assertIsNone(self.store.login(server.ADMIN_EMAIL,self.password,'test-replay',totp(secret,counter)))
  self.assertTrue(self.store.login(server.ADMIN_EMAIL,self.password,'test-code',totp(secret,counter+1)))
  recovery=result['codigosRecuperacion'][0];self.assertTrue(self.store.login(server.ADMIN_EMAIL,self.password,'test-recovery',recovery));self.assertIsNone(self.store.login(server.ADMIN_EMAIL,self.password,'test-recovery',recovery))
  self.value('/api/seguridad/desactivar',{'password':self.password,'codigo':result['codigosRecuperacion'][1]});self.assertFalse(self.value('/api/seguridad/estado')['habilitado'])
 def test_minimum_four_password_and_no_passwords_in_users(self):
  self.assertEqual(self.call('/api/users',{'email':'short@example.test','name':'Prueba','role':'visualizador','password':'abc','active':True})[0],400)
  self.value('/api/users',{'email':'four@example.test','name':'Prueba','role':'visualizador','password':'abcd','active':True});self.assertTrue(self.store.login('four@example.test','abcd','test'))
  for user in self.value('/api/users')['users']:self.assertNotIn('password',user);self.assertNotIn('password_hash',user)
 def test_current_password_change_closes_sessions(self):
  self.assertEqual(self.call('/api/seguridad/password',{'password':'incorrecta','nueva':'abcd','confirmacion':'abcd'})[0],403)
  self.value('/api/seguridad/password',{'password':self.password,'nueva':'abcd','confirmacion':'abcd'});self.assertEqual(self.call('/api/me')[0],401);self.assertTrue(self.store.login(server.ADMIN_EMAIL,'abcd','test-new'))

if __name__=='__main__':unittest.main()
