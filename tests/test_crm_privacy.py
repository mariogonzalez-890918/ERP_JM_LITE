import unittest,uuid
import test_backup_import as fixtures

class CRMPrivacyTests(unittest.TestCase):
 tearDown=fixtures.ModuleBackupTests.tearDown;call=fixtures.ModuleBackupTests.call;value=fixtures.ModuleBackupTests.value;login=fixtures.ModuleBackupTests.login
 def setUp(self):
  fixtures.ModuleBackupTests.setUp(self);self.company=self.value('/api/comercial/empresas',{'nombre':'Empresa CRM ficticia','sucursales':['CENTRAL']})['id'];self.actors={}
  for name,role in [('uno','ventasins'),('dos','ventasins'),('gerente','gerente'),('aux','auxti')]:
   email=name+'@example.test';self.value('/api/users',{'email':email,'name':name,'role':role,'password':self.password,'active':True,'sucursales':['CENTRAL','NORTE','ORIENTE','SUR'] if role=='gerente' else []});self.value('/api/comercial/accesos',{'email':email,'empresas':[self.company],'sucursales':['CENTRAL'],'cajas':[],'acciones':[],'revision':0});self.actors[name]=self.login(email)
  self.customer=self.value('/api/comercial/clientes',{'empresa':self.company,'nombre':'Cliente confidencial ficticio','canales':['ventasins']})['id'];self.assign('uno',0)
 def assign(self,name,revision):return self.value('/api/crm/asignar',{'empresa':self.company,'cliente':self.customer,'vendedor':name+'@example.test','revision':revision})
 def clients(self,actor):return self.value('/api/comercial/clientes?empresa='+str(self.company),actor=actor)['clientes']
 def opportunity(self,actor,**fields):return self.value('/api/crm/oportunidades',{'empresa':self.company,'cliente':self.customer,'titulo':'Seguimiento confidencial ficticio','etapa':'PROSPECTO','importe':'150',**fields},actor)['id']
 def test_customers_are_scoped_and_only_system_can_assign(self):
  self.assertEqual(len(self.clients(self.actors['uno'])),1);self.assertEqual(self.clients(self.actors['dos']),[]);self.assertEqual(self.clients(self.actors['aux']),[]);self.assertEqual(len(self.clients(self.actors['gerente'])),1)
  for name in ('uno','dos','gerente','aux'):self.assertEqual(self.call('/api/crm/asignar',{'empresa':self.company,'cliente':self.customer,'vendedor':'dos@example.test','revision':1},self.actors[name])[0],403)
  self.assertEqual(self.call('/api/comercial/clientes',{'empresa':self.company,'nombre':'No permitido'},self.actors['uno'])[0],403)
 def test_followups_dashboard_and_reassignment_revoke_old_access(self):
  id=self.opportunity(self.actors['uno']);path='/api/crm/oportunidades?empresa='+str(self.company)
  self.assertEqual(self.value(path,actor=self.actors['dos'])['oportunidades'],[])
  self.assertEqual(self.call('/api/crm/seguimiento',{'id':id,'revision':1,'tipo':'NOTA','nota':'Intruso'},self.actors['dos'])[0],403)
  self.value('/api/crm/seguimiento',{'id':id,'revision':1,'tipo':'LLAMADA','nota':'Seguimiento de prueba','proximoSeguimiento':'2026-10-01'},self.actors['uno'])
  own=self.value('/api/crm/dashboard?empresa='+str(self.company),actor=self.actors['uno']);other=self.value('/api/crm/dashboard?empresa='+str(self.company),actor=self.actors['dos']);self.assertEqual(own['prospectos'],1);self.assertEqual(other['prospectos'],0)
  self.assertEqual(self.call('/api/crm/dashboard?empresa='+str(self.company)+'&vendedor=uno@example.test',actor=self.actors['dos'])[0],403)
  self.assign('dos',1);self.assertEqual(self.clients(self.actors['uno']),[]);self.assertEqual(self.value(path,actor=self.actors['uno'])['oportunidades'],[]);self.assertEqual(len(self.value(path,actor=self.actors['dos'])['oportunidades'][0]['seguimientos']),1)
 def test_orders_export_and_templates_do_not_leak_foreign_client(self):
  self.value('/api/comercial/productos',{'empresa':self.company,'nombre':'Producto de prueba','tipo':'PT','categoria':'PD','subcategoria':'05','unidad':'PIEZA','iva':'16','canales':['ventasins'],'precios':{'PUBLICO':'116'}})
  sku=self.value('/api/comercial/productos?empresa='+str(self.company))['productos'][0]['sku'];data={'empresa':self.company,'sucursal':'CENTRAL','cliente':self.customer,'clave':uuid.uuid4().hex,'partidas':[{'sku':sku,'cantidad':'1'}]}
  self.assertEqual(self.call('/api/comercial/pedidos',data,self.actors['dos'])[0],403)
  doc=self.value('/api/comercial/pedidos',data,self.actors['uno'])['documento'];self.assertEqual(self.call('/api/comercial/documento?id='+doc['id'],actor=self.actors['dos'])[0],403);self.assertEqual(self.call('/api/comercial/documento/excel?id='+doc['id'],actor=self.actors['dos'])[0],403);self.assertEqual(self.value('/api/comercial/documentos?empresa='+str(self.company),actor=self.actors['dos'])['documentos'],[])

if __name__=='__main__':unittest.main()
