import unittest,uuid,json
from decimal import Decimal
import test_production as production_cases
class CommercialCycleTests(unittest.TestCase):
 def setUp(self):
  self.p=production_cases.ProductionTests();self.p.setUp();self.addCleanup(self.p.doCleanups);self.c=self.p.c
  self.customer=self.c.value('/api/comercial/clientes',{'empresa':self.c.company,'canal':'ventasins','nombre':'Cliente fiscal de prueba','nombreFiscal':'Cliente fiscal de prueba','rfc':'AAA010101AAA','codigoPostalFiscal':'06000','regimenFiscal':'601','usoCFDI':'G03','correo':'cliente@example.test'})['id']
  self.concept=self.c.value('/api/finanzas/conceptos',{'empresa':self.c.company,'libro':'CXC','nombre':'Venta de prueba'})['id'];self.f('configuracion',{'revision':0,'conceptoCXC':self.concept})
 def f(self,path,data=None,actor=None):return self.c.value('/api/ciclo/'+path+('?empresa='+str(self.c.company) if data is None and '?' not in path else ''),None if data is None else {'empresa':self.c.company,**data},actor)
 def order(self,quantity='5'):
  quote=self.c.value('/api/comercial/pedidos',{'empresa':self.c.company,'canal':'ventasins','sucursal':'CENTRAL','cliente':self.customer,'clave':uuid.uuid4().hex,'partidas':[{'sku':self.p.pt,'cantidad':quantity}]})['documento']
  return self.c.value('/api/comercial/presupuestos/convertir',{'canal':'ventasins','id':quote['id'],'revision':quote['revision']})['documento']
 def seed_stock(self,qty='10'):
  inv=self.c.http.RequestHandlerClass.inventory.inv
  with self.c.store.atomic() as db:inv.post(db,self.p.locations['terminado'],inv.materials()[self.p.pt],Decimal(qty),Decimal('20'),'opening-'+uuid.uuid4().hex,'INICIAL',{'email':'test@example.test','role':'superadmin'})
 def ship(self,order,quantity):return self.f('remision',{'pedido':order['id'],'revision':order['revision'],'almacen':self.p.locations['terminado'],'preparo':'Almacén de prueba','partidas':[{'linea':0,'cantidad':quantity}],'clave':uuid.uuid4().hex})['documento']
 def invoice(self,shipments):return self.f('factura',{'origenes':[d['id'] for d in shipments],'clave':uuid.uuid4().hex})['documento']
 def amount(self):return self.p.quantity(self.p.locations['terminado'],self.p.pt)
 def test_sale_without_production_quote_to_partial_ship_invoice_and_payment(self):
  self.p.p('configuracion',{**self.p.config,'activa':False});self.seed_stock();order=self.order();self.f('reservar',{'pedido':order['id'],'almacen':self.p.locations['terminado'],'clave':uuid.uuid4().hex});self.assertEqual(self.amount(),'10')
  a=self.ship(order,'2');b=self.ship(order,'3');self.assertEqual(self.amount(),'5');invoice=self.invoice([a,b]);self.assertEqual(invoice['total'],'580.00');self.assertEqual(self.amount(),'5')
  account=self.f('documento?id='+invoice['id']);self.assertEqual(account['saldo'],'580.00')
  for amount in ('200','380'):self.f('pago',{'factura':invoice['id'],'importe':amount,'fecha':invoice['fecha'][:10],'metodo':'TRANSFERENCIA','referencia':'Pago de prueba '+amount,'clave':uuid.uuid4().hex})
  state=self.f('documento?id='+invoice['id']);self.assertEqual(state['saldo'],'0.00');self.assertEqual(state['estadoCobro'],'PAGADA');status,pdf,_=self.c.call('/api/ciclo/recibo/pdf?id='+invoice['id']+'&pago='+state['pagos'][0]['id']);self.assertEqual(status,200,pdf[:100]);self.assertTrue(pdf.startswith(b'%PDF'))
 def test_sale_with_production_of_missing_quantity_then_ship_and_invoice(self):
  self.p.config=self.p.p('configuracion',{**self.p.config,'bajoPedido':True,'desdePedidos':True});order=self.order();detail=self.f('pedido?id='+order['id']+'&almacen='+self.p.locations['terminado']);self.assertEqual(detail['partidas'][0]['faltante'],'5')
  o=self.p.p('crear',{'receta':self.p.recipe['id'],'cantidad':'5','pedido':order['id'],'clave':uuid.uuid4().hex})['orden'];o=self.p.event(o,'autorizar');o=self.p.event(o,'surtir',partidas=[{'sku':self.p.raw,'cantidad':'10'}]);o=self.p.event(o,'consumir',partidas=[{'sku':self.p.raw,'cantidad':'10'}]);o=self.p.event(o,'fabricar',cantidad='5');o=self.p.event(o,'recibir',cantidad='5');shipment=self.ship(order,'5');invoice=self.invoice([shipment]);self.assertEqual(self.amount(),'0');self.assertEqual(invoice['total'],'580.00')
 def test_credit_note_has_no_stock_and_physical_return_has_one_entry(self):
  self.seed_stock('5');order=self.order();shipment=self.ship(order,'5');invoice=self.invoice([shipment]);credit=self.f('nota-credito',{'factura':invoice['id'],'motivo':'Devolución parcial','partidas':[{'linea':0,'cantidad':'2'}],'clave':uuid.uuid4().hex})['documento'];self.assertEqual(self.amount(),'0');self.assertEqual(self.f('documento?id='+invoice['id'])['saldo'],'348.00')
  data={'remision':shipment['id'],'almacen':self.p.locations['terminado'],'condicion':'APROBADO','motivo':'Recibido físicamente','partidas':[{'linea':0,'cantidad':'2'}],'clave':uuid.uuid4().hex};result=self.f('devolucion',data);self.assertEqual(result,self.f('devolucion',data));self.assertEqual(self.amount(),'2')
  self.f('cancelar',{'id':credit['id'],'revision':credit['revision'],'motivo':'Se revierte el ajuste comercial','clave':uuid.uuid4().hex});self.assertEqual(self.f('documento?id='+invoice['id'])['saldo'],'580.00');self.assertEqual(self.amount(),'2')
 def test_cannot_double_ship_or_invoice_or_cancel_with_active_dependents(self):
  self.seed_stock('5');order=self.order();shipment=self.ship(order,'5');invoice=self.invoice([shipment]);self.assertEqual(self.c.call('/api/ciclo/factura',{'empresa':self.c.company,'origenes':[shipment['id']],'clave':uuid.uuid4().hex})[0],400)
  self.assertEqual(self.c.call('/api/ciclo/remision',{'empresa':self.c.company,'pedido':order['id'],'revision':order['revision'],'almacen':self.p.locations['terminado'],'preparo':'Prueba','partidas':[{'linea':0,'cantidad':'1'}],'clave':uuid.uuid4().hex})[0],400)
  self.assertEqual(self.c.call('/api/ciclo/cancelar',{'empresa':self.c.company,'id':shipment['id'],'revision':shipment['revision'],'motivo':'Prueba','clave':uuid.uuid4().hex})[0],400);self.assertEqual(self.amount(),'0')
  self.f('cancelar',{'id':invoice['id'],'revision':invoice['revision'],'motivo':'Anulación comercial','clave':uuid.uuid4().hex});self.f('cancelar',{'id':shipment['id'],'revision':shipment['revision'],'motivo':'Regreso físico','clave':uuid.uuid4().hex});self.assertEqual(self.amount(),'5')
 def test_credit_after_payment_creates_balance_in_favor_and_actual_refund(self):
  self.seed_stock('5');invoice=self.invoice([self.ship(self.order(),'5')]);self.f('pago',{'factura':invoice['id'],'importe':'580','fecha':invoice['fecha'][:10],'metodo':'EFECTIVO','referencia':'Cobro de prueba','clave':uuid.uuid4().hex});self.f('nota-credito',{'factura':invoice['id'],'motivo':'Ajuste posterior al cobro','partidas':[{'linea':0,'cantidad':'1'}],'clave':uuid.uuid4().hex});self.assertEqual(self.f('documento?id='+invoice['id'])['saldo'],'-116.00')
  self.f('pago',{'factura':invoice['id'],'importe':'116','tipo':'REEMBOLSO','fecha':invoice['fecha'][:10],'metodo':'EFECTIVO','referencia':'Reembolso registrado','clave':uuid.uuid4().hex});self.assertEqual(self.f('documento?id='+invoice['id'])['saldo'],'0.00')
 def test_pending_quantities_payment_cancel_and_export_formats(self):
  self.seed_stock('5');order=self.order();shipment=self.ship(order,'5');invoice=self.f('factura',{'origenes':[shipment['id']],'partidas':[{'origen':shipment['id'],'linea':0,'cantidad':'2'}],'clave':uuid.uuid4().hex})['documento']
  self.assertEqual(self.f('documento?id='+shipment['id'])['pendientesFacturar'][0]['pendienteFacturar'],'3')
  self.f('pago',{'factura':invoice['id'],'importe':'100','fecha':invoice['fecha'][:10],'metodo':'EFECTIVO','referencia':'Cobro a cancelar','clave':uuid.uuid4().hex});snapshot=self.f('documento?id='+invoice['id'])
  self.f('cancelar-pago',{'factura':invoice['id'],'pago':snapshot['pagos'][0]['id'],'revisionCuenta':snapshot['revisionCuenta'],'motivo':'Captura errónea','clave':uuid.uuid4().hex});snapshot=self.f('documento?id='+invoice['id']);self.assertTrue(snapshot['pagos'][0]['cancelado']);self.assertEqual(snapshot['saldo'],'232.00')
  self.f('nota-credito',{'factura':invoice['id'],'motivo':'Ajuste parcial','partidas':[{'linea':0,'cantidad':'1'}],'clave':uuid.uuid4().hex});self.assertEqual(self.f('documento?id='+invoice['id'])['pendientesAcreditar'][0]['pendienteAcreditar'],'1')
  for ext in ('csv','xlsx','pdf'):self.assertEqual(self.c.call('/api/ciclo/reportes/'+ext+'?empresa='+str(self.c.company))[0],200)
 def test_missing_quantity_is_recomputed_and_duplicate_production_blocked(self):
  self.seed_stock('2');self.p.config=self.p.p('configuracion',{**self.p.config,'bajoPedido':True,'desdePedidos':True});order=self.order()
  data={'empresa':self.c.company,'receta':self.p.recipe['id'],'cantidad':'999','pedido':order['id'],'seleccion':'FALTANTE','clave':uuid.uuid4().hex}
  o=self.p.p('crear',data)['orden'];self.assertEqual(o['cantidadPlaneada'],'3');self.assertEqual(self.c.call('/api/produccion/crear',{**data,'clave':uuid.uuid4().hex})[0],400)
  self.assertEqual(self.p.quantity(self.p.locations['materiasPrimas'],self.p.raw),'100');
  with self.c.store.connect() as db:self.assertTrue(self.c.http.RequestHandlerClass.commercial_flow.cm.linked_stock(db,order['id']))
if __name__=='__main__':unittest.main()
