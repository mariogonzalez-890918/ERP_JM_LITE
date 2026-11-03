import json,unittest,uuid
import test_inventory as inventory_cases
import test_commercial as commercial_cases
class ProductionTests(unittest.TestCase):
 def setUp(self):
  self.c=inventory_cases.InventoryTests();self.c.setUp();self.addCleanup(self.c.tearDown);c=self.c;c.activate('100')
  c.value('/api/comercial/maestro',{'canal':'ventasins','empresas':[c.company],'archivo':'Productos.xlsx','contenido':commercial_cases.master()});self.pt= commercial_cases.SKU;self.raw=c.sku;self.locations={'materiasPrimas':c.w}
  for name,kind,key in [('Producción de prueba','PRODUCCION','consumo'),('PT de prueba','PT','terminado'),('Cuarentena de prueba','CUARENTENA','cuarentena'),('Merma de prueba','MERMA','merma')]:
   w=c.inv('almacenes',{'empresa':c.company,'sucursal':'CENTRAL','nombre':name,'funcion':kind})['almacen'];c.activate('0',w['id']);self.locations[key]=w['id']
  self.config=self.p('configuracion',{'revision':0,'activa':True,'manual':True,'paraStock':True,'parcial':True,'desperdicios':True,**self.locations})
  self.recipe=self.p('recetas',{'codigo':'REC-PT','producto':self.pt,'cantidadBase':'1','componentes':[{'sku':self.raw,'cantidad':'2','unidad':c.material['unidadEntrega']}]})
 def p(self,path,data=None,actor=None):
  c=self.c;return c.value('/api/produccion/'+path+('?empresa='+str(c.company) if data is None and '?' not in path else ''),None if data is None else {'empresa':c.company,**data},actor)
 def create(self,qty='5'):return self.p('crear',{'receta':self.recipe['id'],'cantidad':qty,'clave':uuid.uuid4().hex})['orden']
 def event(self,o,action,**data):return self.p(action,{'id':o['id'],'revision':o['revision'],'clave':uuid.uuid4().hex,**data})['orden']
 def quantity(self,w,sku):
  with self.c.store.connect() as db:row=db.execute('SELECT qty FROM inv_balances WHERE warehouse=? AND sku=?',(w,sku)).fetchone();return row[0] if row else '0'
 def test_full_manufacture_consumption_cost_stock_and_pdf(self):
  with self.c.store.connect() as db:before=db.execute('SELECT COUNT(*) FROM inv_ledger').fetchone()[0]
  plan=self.p('explosionado',{'receta':self.recipe['id'],'cantidad':'5'});self.assertEqual(plan['explosionado'][0]['requerido'],'10');o=self.create();self.assertEqual(o['estado'],'PENDIENTE_AUTORIZACION')
  with self.c.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM inv_ledger').fetchone()[0],before)
  o=self.event(o,'autorizar');o=self.event(o,'surtir',partidas=[{'sku':self.raw,'cantidad':'10'}]);o=self.event(o,'consumir',partidas=[{'sku':self.raw,'cantidad':'10'}]);o=self.event(o,'fabricar',cantidad='5',lote='LOTE-PRUEBA');o=self.event(o,'recibir',cantidad='5',lote='LOTE-PRUEBA');self.assertEqual(o['costoReal'],'100');self.assertEqual(o['costoUnitario'],'20');self.assertEqual(self.quantity(self.locations['terminado'],self.pt),'5');self.assertEqual(self.quantity(self.c.w,self.raw),'90');o=self.event(o,'cerrar');self.assertEqual(o['estado'],'CERRADA')
  status,pdf,_=self.c.call('/api/produccion/hoja/pdf?id='+o['id']);self.assertEqual(status,200,pdf[:100]);self.assertTrue(pdf.startswith(b'%PDF'))
 def test_partial_receipts_keep_actual_cost_and_pending_quantities(self):
  o=self.event(self.create('10'),'autorizar');o=self.event(o,'surtir',partidas=[{'sku':self.raw,'cantidad':'20'}])
  for _ in range(2):
   o=self.event(o,'consumir',partidas=[{'sku':self.raw,'cantidad':'10'}]);o=self.event(o,'fabricar',cantidad='5');o=self.event(o,'recibir',cantidad='5');self.assertEqual(o['costoUnitario'],'20')
  self.assertEqual(o['cantidadPendiente'],'0');self.assertEqual(o['costoReal'],'200');self.assertEqual(self.quantity(self.locations['terminado'],self.pt),'10')
 def test_reservations_and_double_submissions_do_not_change_physical_twice(self):
  o=self.event(self.create(),'autorizar');self.assertEqual(self.quantity(self.c.w,self.raw),'100')
  with self.c.store.connect() as db:self.assertEqual(db.execute('SELECT qty FROM op_reservations WHERE document=?',(o['id'],)).fetchone()[0],'10')
  data={'id':o['id'],'revision':o['revision'],'clave':uuid.uuid4().hex,'partidas':[{'sku':self.raw,'cantidad':'10'}]};result=self.p('surtir',data);self.assertEqual(result,self.p('surtir',data));self.assertEqual(self.quantity(self.c.w,self.raw),'90')
  with self.c.store.connect() as db:
   inv=self.c.http.RequestHandlerClass.inventory.inv;m=inv.materials()[self.raw]
   with self.assertRaises(ValueError):inv.post(db,self.locations['consumo'],m,-__import__('decimal').Decimal('1'),None,'test-other-reservation','SALIDA',{'email':'test','role':'superadmin'},allow_negative=False)
 def test_recipe_versions_are_snapshotted_and_cycles_are_rejected(self):
  o=self.create();version=self.p('recetas',{'codigo':'REC-PT','producto':self.pt,'cantidadBase':'1','componentes':[{'sku':self.raw,'cantidad':'3'}]});self.assertEqual(version['version'],2);saved=self.p('orden?id='+o['id']);self.assertEqual(saved['orden']['receta']['version'],1);self.assertEqual(saved['orden']['receta']['componentes'][0]['cantidad'],'2')
  self.assertEqual(self.c.call('/api/produccion/recetas',{'empresa':self.c.company,'codigo':'CICLO','producto':self.pt,'cantidadBase':'1','componentes':[{'sku':self.pt,'cantidad':'1'}]})[0],400)
 def test_failed_receipt_rolls_back_and_cancellation_posts_inverse_entries(self):
  from unittest.mock import patch
  o=self.event(self.create(),'autorizar');o=self.event(o,'surtir',partidas=[{'sku':self.raw,'cantidad':'10'}]);o=self.event(o,'consumir',partidas=[{'sku':self.raw,'cantidad':'10'}]);o=self.event(o,'fabricar',cantidad='5');prod=self.c.http.RequestHandlerClass.production
  with patch.object(prod.inv,'post',side_effect=ValueError('Fallo de prueba')):self.assertEqual(self.c.call('/api/produccion/recibir',{'id':o['id'],'revision':o['revision'],'cantidad':'5','clave':uuid.uuid4().hex})[0],400)
  self.assertEqual(self.quantity(self.locations['terminado'],self.pt),'0');o=self.event(o,'recibir',cantidad='5');o=self.event(o,'cancelar',motivo='Cancelación verificada');self.assertEqual(o['estado'],'CANCELADA');self.assertEqual(self.quantity(self.c.w,self.raw),'100');self.assertEqual(self.quantity(self.locations['terminado'],self.pt),'0')
 def test_quality_gates_lots_quarantine_and_stage_reports(self):
  self.config=self.p('configuracion',{**self.config,'calidadMP':True,'calidadProceso':True,'calidadPT':True,'lotes':True,'metodos':['ETAPAS'],'etapas':['Preparar','Terminar']});o=self.p('crear',{'receta':self.recipe['id'],'cantidad':'5','metodo':'ETAPAS','clave':uuid.uuid4().hex})['orden'];o=self.event(o,'autorizar');o=self.event(o,'surtir',partidas=[{'sku':self.raw,'cantidad':'10'}])
  invalid=lambda action,**data:self.c.call('/api/produccion/'+action,{'empresa':self.c.company,'id':o['id'],'revision':o['revision'],'clave':uuid.uuid4().hex,**data})[0]
  self.assertEqual(invalid('consumir',partidas=[{'sku':self.raw,'cantidad':'10'}]),400);o=self.event(o,'calidad',punto='MP',estado='APROBADO',observaciones='Materias primas conformes');o=self.event(o,'consumir',partidas=[{'sku':self.raw,'cantidad':'10'}]);self.assertEqual(invalid('fabricar',cantidad='5',etapa='Preparar',lote='L1'),400);o=self.event(o,'calidad',punto='PROCESO',estado='APROBADO',observaciones='Parámetros conformes')
  self.assertEqual(invalid('fabricar',cantidad='5',etapa='Terminar',lote='L1'),400);o=self.event(o,'fabricar',cantidad='5',etapa='Preparar',lote='L1');o=self.event(o,'fabricar',cantidad='5',etapa='Terminar',lote='L1');self.assertEqual(invalid('recibir',cantidad='5',destino=self.locations['terminado'],lote='L1'),400);self.assertEqual(invalid('recibir',cantidad='5',lote='NO-EXISTE'),400);o=self.event(o,'recibir',cantidad='5',lote='L1');self.assertEqual(self.quantity(self.locations['cuarentena'],self.pt),'5');self.assertEqual(self.quantity(self.locations['terminado'],self.pt),'0')
  for view in ('ORDENES','MOVIMIENTOS','CONSUMOS','MERMAS','LOTES','CALIDAD'):
   for ext in ('csv','xlsx','pdf'):self.assertEqual(self.c.call('/api/produccion/reportes/'+ext+'?empresa='+str(self.c.company)+'&vista='+view)[0],200)
 def test_production_operator_has_no_costs_or_authorization_and_revocation_applies(self):
  operator=self.c.stockuser('produccion');o=self.create();detail=self.p('orden?id='+o['id'],actor=operator);self.assertNotIn('costoReal',detail['orden']);self.assertNotIn('costoEstimado',detail['orden']);self.assertEqual(self.c.call('/api/produccion/autorizar',{'empresa':self.c.company,'id':o['id'],'revision':o['revision'],'clave':uuid.uuid4().hex},operator)[0],403)
  meta=self.p('meta',actor=operator);self.assertTrue(meta['empresas']);self.assertFalse(any('costo' in m for m in meta['materiales']));self.config=self.p('configuracion',{**self.config,'permisos':{'produccion@inventory.test':[]}});self.assertEqual(self.c.call('/api/produccion/orden?id='+o['id'],actor=operator)[0],403)
 def test_recipe_layout_review_is_atomic_and_apply_checks_fingerprint(self):
  from comercial_print import report_xlsx
  from produccion_routes import HEADERS
  import base64
  data={'archivo':'Recetas.xlsx','contenido':base64.b64encode(report_xlsx([HEADERS,[self.pt,'IMPORTADA','1',self.raw,'2',self.c.material['unidadEntrega'],'1','0','','','Instrucciones']],'RECETAS')).decode()};before=len(self.p('recetas')['recetas']);review=self.p('recetas/importar',{**data,'revisar':True});self.assertEqual(len(self.p('recetas')['recetas']),before);self.p('recetas/importar',{**data,**{k:review[k] for k in ('huellaActual','huellaArchivo')}});self.assertEqual(len(self.p('recetas')['recetas']),before+1);self.assertEqual(self.c.call('/api/produccion/recetas/importar',{'empresa':self.c.company,**data,**{k:review[k] for k in ('huellaActual','huellaArchivo')}})[0],409)
 def test_general_restore_recovers_orders_events_reservations_and_costs(self):
  from test_general_restore import GeneralRestoreTests
  o=self.event(self.create(),'autorizar');o=self.event(o,'surtir',partidas=[{'sku':self.raw,'cantidad':'10'}]);o=self.event(o,'consumir',partidas=[{'sku':self.raw,'cantidad':'10'}]);o=self.event(o,'fabricar',cantidad='5');restore=GeneralRestoreTests();restore.c=self.c;raw=restore.snapshot()
  with self.c.store.connect() as db:events=db.execute('SELECT COUNT(*) FROM pr_events').fetchone()[0];ledger=db.execute('SELECT COUNT(*) FROM inv_ledger').fetchone()[0]
  self.event(o,'recibir',cantidad='5');status,review=restore.upload(raw);self.assertEqual(status,200,review);status,result,_=restore.confirm(review);self.assertEqual(status,200,result);self.c.admin=self.c.login('mario.gonzalez@jad-ayt.com');restored=self.p('orden?id='+o['id'])['orden'];self.assertEqual(restored['cantidadRecibida'],'0');self.assertEqual(restored['costoConsumido'],'100');self.assertEqual(self.quantity(self.locations['terminado'],self.pt),'0')
  with self.c.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM pr_events').fetchone()[0],events);self.assertEqual(db.execute('SELECT COUNT(*) FROM inv_ledger').fetchone()[0],ledger)
  restored=self.event(restored,'recibir',cantidad='5');self.assertEqual(restored['costoUnitario'],'20')
 def test_multilevel_explosion_allocates_shared_material_once_without_stock_moves(self):
  import copy
  from decimal import Decimal
  p=self.c.http.RequestHandlerClass.production;root=copy.deepcopy(self.recipe);raw={**root['componentes'][0],'cantidad':'60'};root['componentes']=[raw,{**raw,'sku':self.pt,'cantidad':'1','receta':{**self.recipe,'componentes':[raw]}}]
  with self.c.store.connect() as db:
   before=db.execute('SELECT COUNT(*) FROM inv_ledger').fetchone()[0];rows,cost=p.explosion(db,root,Decimal('1'),self.locations['materiasPrimas'],self.config);self.assertEqual([r['faltante'] for r in rows if r['sku']==self.raw],['0','20']);self.assertEqual(db.execute('SELECT COUNT(*) FROM inv_ledger').fetchone()[0],before)
 def test_merma_rejects_labor_and_extraordinary_loss_keep_actual_cost(self):
  self.config=self.p('configuracion',{**self.config,'parcial':False});o=self.event(self.create(),'autorizar');o=self.event(o,'surtir',partidas=[{'sku':self.raw,'cantidad':'10'}]);o=self.event(o,'consumir',partidas=[{'sku':self.raw,'cantidad':'10','merma':'1'}]);o=self.event(o,'cargo',tipo='MANO_OBRA',importe='15',motivo='Costo de operación');o=self.event(o,'perdida',importe='10',motivo='Pérdida extraordinaria autorizada');o=self.event(o,'fabricar',cantidad='5',rechazado='1');o=self.event(o,'recibir',cantidad='4');self.assertEqual(o['costoUnitario'],'26.25');self.assertEqual(o['costoReal'],'105');self.assertEqual(self.quantity(self.locations['merma'],self.pt),'1');self.assertEqual(self.quantity(self.locations['merma'],self.raw),'1');o=self.event(o,'cerrar');self.assertEqual(o['estado'],'CERRADA')
if __name__=='__main__':unittest.main()
