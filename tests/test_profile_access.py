import unittest
import test_backup_import as fixtures
import server
from permissions import MODULES,enabled_modules

class ProfileAccessTests(unittest.TestCase):
 setUp=fixtures.ModuleBackupTests.setUp
 tearDown=fixtures.ModuleBackupTests.tearDown
 call=fixtures.ModuleBackupTests.call
 value=fixtures.ModuleBackupTests.value
 login=fixtures.ModuleBackupTests.login
 def test_all_profiles_match_session_contract_and_revocations(self):
  self.store.enforce_contract=True
  for role in server.ROLES:
   if role=='superadmin':continue
   with self.subTest(role=role):
    email=role+'@example.test'
    self.value('/api/users',{'email':email,'name':role,'role':role,'password':self.password,'active':True,'sucursales':list(server.BRANCHES) if role=='gerente' else ['CENTRAL'] if role=='requisicion' else [],'almacenes':['CENTRAL'] if role=='almacenista' else []})
    user=self.login(email)
    pending=self.value('/api/me',actor=user)['user']
    self.assertEqual(pending['modulos'],[])
    self.assertEqual(pending['acceso']['motivo'],'contrato_pendiente')
  self.value('/api/empresa/modulos',{'revision':0,'modules':['ventasins','requisiciones']})
  profiles=self.value('/api/perfiles')
  self.assertTrue(profiles['contrato']['configurado'])
  for profile in profiles['perfiles']:
   if profile['perfil']=='superadmin':continue
   user=self.login(profile['perfil']+'@example.test')
   session=self.value('/api/me',actor=user)['user']
   self.assertEqual(session['modulos'],profile['efectivos'])
   self.assertTrue(set(session['modulos'])<=set(['ventasins','requisiciones']))
  self.assertEqual(set(self.value('/api/me')['user']['modulos']),set(MODULES))
  sales=next(p for p in profiles['perfiles'] if p['perfil']=='ventas')
  self.value('/api/perfiles',{'perfil':'ventas','revision':sales['revision'],'modulos':[]},method='PUT')
  actor=self.login('ventas@example.test')
  self.assertEqual(self.value('/api/me',actor=actor)['user']['acceso']['motivo'],'sin_modulos_perfil')
  self.assertEqual(self.call('/api/crm/meta?empresa=1',actor=actor)[0],403)
 def test_restricted_profiles_reject_unusable_modules(self):
  profiles=self.value('/api/perfiles')['perfiles']
  for role in ('requisicion','ventaspasteleria'):
   p=next(p for p in profiles if p['perfil']==role)
   self.assertEqual(self.call('/api/perfiles',{'perfil':role,'revision':p['revision'],'modulos':['compras']},method='PUT')[0],400)
 def test_missing_contract_is_not_silently_granted(self):
  self.store.enforce_contract=True
  self.value('/api/users',{'email':'sales@example.test','name':'Vendedor','role':'ventas','password':self.password,'active':True})
  seller=self.login('sales@example.test')
  self.assertEqual(self.call('/api/comercial/meta?canal=ventasins',actor=seller)[0],403)
  self.value('/api/empresa/modulos',{'revision':0,'modules':['calidad']})
  self.assertEqual(self.value('/api/me',actor=seller)['user']['acceso']['motivo'],'sin_modulos_contratados')

if __name__=='__main__':unittest.main()

