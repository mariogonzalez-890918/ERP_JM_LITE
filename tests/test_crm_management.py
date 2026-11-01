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
 def test_commission_basis_snapshots_collections_refunds_and_private_reports(self):
  company=self.c.company;rate={'empresa':company,'cliente':self.c.customer,'vendedor':'uno@example.test','porcentaje':'10','base':'FACTURADO','revision':0};self.c.value('/api/crm/comisiones',rate)
  concept=self.c.value('/api/finanzas/conceptos',{'empresa':company,'libro':'CXC','nombre':'Facturas de prueba'})['id'];account={'empresa':company,'libro':'CXC','tercero':self.c.customer,'concepto':concept,'fecha':'2026-11-01','vencimiento':'2026-11-30','moneda':'MXN','importe':'1160','baseComision':'1000'}
  first=self.c.value('/api/finanzas/cuentas',{**account,'referencia':'FACTURADO-1'})['id'];self.c.value('/api/crm/comisiones',{**rate,'porcentaje':'20','base':'COBRADO','revision':1});second=self.c.value('/api/finanzas/cuentas',{**account,'referencia':'COBRADO-1'})['id']
  import uuid
  for id in (first,second):self.c.value('/api/finanzas/pagos',{'cuenta':id,'tipo':'ABONO','importe':'580','fecha':'2026-11-10','referencia':'Transferencia','metodo':'TRANSFERENCIA','revision':1,'clave':uuid.uuid4().hex})
  self.c.value('/api/finanzas/pagos',{'cuenta':second,'tipo':'REEMBOLSO','importe':'116','fecha':'2026-11-20','referencia':'Devolución','metodo':'TRANSFERENCIA','revision':2,'clave':uuid.uuid4().hex})
  query='?empresa='+str(company)+'&desde=2026-11-01&hasta=2026-11-30';result=self.c.value('/api/crm/reporte-comisiones'+query);self.assertEqual(result['totalesPorMoneda'],{'MXN':'180.00'});self.assertEqual({r['regla'] for r in result['registros']},{'FACTURADO','COBRADO'});self.assertEqual(next(r for r in result['registros'] if r['cuenta']==first)['porcentaje'],'10.00')
  for suffix,signature in [('excel',b'PK'),('pdf',b'%PDF-'),('csv',b'\xef\xbb\xbf')]:
   path='/api/crm/comisiones-'+suffix+query;self.assertEqual(self.c.call(path,actor=self.c.actors['uno'])[0],403);self.assertTrue(self.c.call(path)[1].startswith(signature))

if __name__=='__main__':unittest.main()
