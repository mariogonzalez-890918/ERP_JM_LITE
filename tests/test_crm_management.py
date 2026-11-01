import json,unittest
import test_crm_privacy as crm_cases

class CRMManagementTests(unittest.TestCase):
 def setUp(self):
  self.c=crm_cases.CRMPrivacyTests();self.c.setUp();self.addCleanup(self.c.tearDown)
 def path(self,name):return '/api/crm/'+name+'?empresa='+str(self.c.company)
 def test_commission_is_manager_only_and_never_sent_to_seller(self):
  data={'empresa':self.c.company,'cliente':self.c.customer,'vendedor':'uno@example.test','porcentaje':'7.25','revision':0}
  for role in ('uno','dos','aux'):self.assertEqual(self.c.call('/api/crm/comisiones',data,self.c.actors[role])[0],403)
  self.c.value('/api/crm/comisiones',data,self.c.actors['gerente']);seller=self.c.value(self.path('meta'),actor=self.c.actors['uno']);self.assertNotIn('comision',seller['clientes'][0]);manager=self.c.value(self.path('meta'),actor=self.c.actors['gerente']);self.assertEqual(manager['clientes'][0]['comision'],'7.25')
  self.assertEqual(self.c.call('/api/crm/comisiones',{**data,'revision':1,'porcentaje':'100.01'})[0],400)
 def test_monthly_permission_is_revocable_and_does_not_widen_portfolio(self):
  query=self.path('planes')+'&mes=2026-11';self.assertEqual(self.c.call(query,actor=self.c.actors['uno'])[0],403)
  grant={'empresa':self.c.company,'email':'uno@example.test','habilitado':True,'revision':0};self.c.value('/api/crm/acceso-tablero',grant)
  self.assertEqual(self.c.call('/api/crm/acceso-tablero',grant,self.c.actors['gerente'])[0],403)
  row={'empresa':self.c.company,'mes':'2026-11','tipo':'CLIENTE','cliente':self.c.customer,'titulo':'Cliente de prueba','presupuesto':'1000','real':'250','pago':'Crédito','pedidos':'Mensual','revision':0};self.c.value('/api/crm/planes',row,self.c.actors['uno'])
  result=self.c.value(query,actor=self.c.actors['uno']);self.assertEqual(result['totales']['cumplimiento'],'25.00');self.assertNotIn('porcentajeComision',result['registros'][0]);self.assertNotIn('comisionEstimada',result['registros'][0])
  self.c.assign('dos',1);self.assertEqual(self.c.value(query,actor=self.c.actors['uno'])['registros'],[])
  self.c.value('/api/crm/acceso-tablero',{**grant,'habilitado':False,'revision':1});self.assertEqual(self.c.call(query,actor=self.c.actors['uno'])[0],403)
 def test_new_seller_is_created_with_company_scope_only_by_systems(self):
  data={'empresa':self.c.company,'email':'nuevo@example.test','nombre':'Vendedor nuevo','password':self.c.password};self.assertEqual(self.c.call('/api/crm/vendedores',data,self.c.actors['gerente'])[0],403);self.c.value('/api/crm/vendedores',data);actor=self.c.login(data['email']);self.assertEqual(self.c.value('/api/me',actor=actor)['user']['role'],'ventas');self.assertIn(data['email'],[v['email'] for v in self.c.value(self.path('meta'))['vendedores']]);self.assertEqual(self.c.value(self.path('meta'),actor=actor)['clientes'],[])

if __name__=='__main__':unittest.main()
