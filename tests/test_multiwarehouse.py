import json,sqlite3,unittest,uuid
import test_inventory as inventory_cases
from inventarios import InventoryStore

class MultiWarehouseTests(unittest.TestCase):
 def setUp(self):self.case=inventory_cases.InventoryTests();self.case.setUp()
 def tearDown(self):self.case.tearDown()
 def __getattr__(self,name):
  case=self.__dict__.get('case')
  if case is None:raise AttributeError(name)
  return getattr(case,name)
 def new_warehouse(self,name='Producción configurada',function='PRODUCCION',branch='CENTRAL'):
  return self.inv('almacenes',{'empresa':self.company,'sucursal':branch,'nombre':name,'funcion':function})['almacen']
 def test_names_and_independent_stock_same_branch(self):
  self.activate('20');old=self.state();w=self.new_warehouse();self.assertNotEqual(w['id'],self.w);self.assertFalse(w['activo']);self.assertEqual(w['sucursal'],'CENTRAL')
  self.activate('0',w['id']);self.assertEqual(self.amount(),'20');self.assertEqual(self.amount(w['id']),'0')
  transfer=self.inv('traspaso',{'accion':'solicitar','origen':self.w,'destino':w['id'],'partidas':[{'sku':self.sku,'cantidad':'4'}],'motivo':'Surtido de prueba','clave':uuid.uuid4().hex})['traspaso']
  self.assertFalse(transfer['intercompania'])
  transfer=self.inv('traspaso',{'accion':'enviar','id':transfer['id'],'revision':transfer['revision'],'persona':'Entrega prueba','clave':uuid.uuid4().hex})['traspaso']
  self.inv('traspaso',{'accion':'recibir','id':transfer['id'],'revision':transfer['revision'],'persona':'Recibe prueba','partidas':[{'sku':self.sku,'cantidad':'4'}],'clave':uuid.uuid4().hex})
  self.assertEqual(self.amount(),'16');self.assertEqual(self.amount(w['id']),'4');self.assertEqual(self.state()['almacen']['ciclo'],old['almacen']['ciclo'])
  self.assertEqual(self.inv('kardex?almacen='+w['id'])['movimientos'][-1]['nombreAlmacen'],'Producción configurada')
 def test_migration_preserves_ids_costs_and_immutable_history(self):
  self.activate('20')
  with self.store.connect() as db:
   balances=db.execute('SELECT * FROM inv_balances').fetchall();ledger=db.execute('SELECT * FROM inv_ledger').fetchall();warehouses=db.execute('SELECT * FROM inv_warehouses').fetchall()
   db.execute('DROP TABLE inv_warehouses');db.execute('CREATE TABLE inv_warehouses(id TEXT PRIMARY KEY,company INTEGER NOT NULL,branch TEXT NOT NULL,cycle INTEGER NOT NULL DEFAULT 1,active INTEGER NOT NULL DEFAULT 0,revision INTEGER NOT NULL DEFAULT 1,UNIQUE(company,branch))');db.executemany('INSERT INTO inv_warehouses VALUES(?,?,?,?,?,?)',warehouses)
  InventoryStore(self.store,self.http.RequestHandlerClass.inventory.inv.po)
  self.new_warehouse()
  with self.store.connect() as db:
   self.assertEqual(db.execute('SELECT * FROM inv_balances').fetchall(),balances);self.assertEqual(db.execute('SELECT * FROM inv_ledger').fetchall(),ledger)
   with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM inv_ledger')
  self.assertEqual(self.amount(),'20')
 def test_permissions_revision_names_and_company_boundaries(self):
  w=self.new_warehouse();data={'id':w['id'],'revision':w['revision'],'nombre':'PT configurado','funcion':'PT'}
  worker=self.stockuser('almacenista');self.assertEqual(self.call('/api/inventarios/almacenes',data,worker)[0],403)
  self.inv('almacenes',data);self.assertEqual(self.call('/api/inventarios/almacenes',data)[0],409)
  self.assertEqual(self.call('/api/inventarios/almacenes',{'empresa':self.company,'sucursal':'CENTRAL','nombre':'pt CONFIGURADO','funcion':'PT'})[0],400)
  self.assertEqual(self.call('/api/inventarios/almacenes',{'empresa':self.company,'sucursal':'NO CONFIGURADA','nombre':'Otro','funcion':'PT'})[0],400)
  self.activate('2',w['id']);latest=self.state(w['id'])['almacen'];self.assertEqual(self.call('/api/inventarios/almacenes',{'id':w['id'],'revision':latest['revision'],'nombre':latest['nombre'],'funcion':'MERMA'})[0],400)
  manager=self.stockuser('gerente');other=self.value('/api/comercial/empresas',{'nombre':'Otra empresa de pruebas','sucursales':['CENTRAL']})['id']
  self.assertEqual(self.call('/api/inventarios/almacenes',{'empresa':other,'sucursal':'CENTRAL','nombre':'Otro','funcion':'PT'},manager)[0],403)


 def test_quarantine_blocks_ordinary_outputs_and_releases_atomically(self):
  from unittest.mock import patch
  q=self.new_warehouse('Cuarentena de prueba','CUARENTENA');self.activate('5',q['id']);self.activate('0')
  inv=self.http.RequestHandlerClass.inventory.inv
  data={'origen':q['id'],'destino':self.w,'sku':self.sku,'cantidad':'2','responsable':'Inspección de prueba','motivo':'Criterios verificados','clave':uuid.uuid4().hex}
  self.assertEqual(self.call('/api/inventarios/movimiento',{'almacen':q['id'],'sku':self.sku,'tipo':'SALIDA','cantidad':'1','motivo':'Intento ordinario','clave':uuid.uuid4().hex})[0],400)
  post=inv.post
  def fail_second(db,w,*args,**kwargs):
   if w==self.w:raise ValueError('Fallo simulado de recepción')
   return post(db,w,*args,**kwargs)
  with patch.object(inv,'post',side_effect=fail_second):self.assertEqual(self.call('/api/inventarios/cuarentena/liberar',data)[0],400)
  self.assertEqual(self.amount(q['id']),'5');self.assertEqual(self.amount(),'0')
  result=self.inv('cuarentena/liberar',data);self.assertEqual(result,self.inv('cuarentena/liberar',data));self.assertEqual(self.amount(q['id']),'3');self.assertEqual(self.amount(),'2')
  self.assertEqual(result['movimientos'][0]['costoUnitario'],result['movimientos'][1]['costoUnitario'])
  self.assertEqual(self.call('/api/inventarios/cuarentena/liberar',{**data,'cantidad':'20','clave':uuid.uuid4().hex})[0],400)
  self.assertEqual(self.amount(q['id']),'3');self.assertEqual(self.amount(),'2')
  worker=self.stockuser('almacenista');self.assertEqual(self.call('/api/inventarios/cuarentena/liberar',{**data,'clave':uuid.uuid4().hex},worker)[0],403)


 def test_purchase_receipt_keeps_legacy_destination(self):
  new=self.new_warehouse('Otro almacén de la sucursal','GENERAL');self.activate('20');self.activate('0',new['id'])
  order=self.confirm(self.order());self.assertTrue(self.inv('pedidos-recibir?almacen='+self.w)['pedidos']);self.assertFalse(self.inv('pedidos-recibir?almacen='+new['id'])['pedidos'])
  self.move(order,'1');self.assertEqual(self.amount(),'30');self.assertEqual(self.amount(new['id']),'0')
  self.assertEqual(len(self.inv('recepciones?almacen='+self.w)['recepciones']),1);self.assertEqual(self.inv('recepciones?almacen='+new['id'])['recepciones'],[])

if __name__=='__main__':unittest.main()
