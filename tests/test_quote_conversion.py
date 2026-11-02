import copy,json,unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import test_commercial as cases

class QuoteConversionTests(unittest.TestCase):
 def setUp(self):
  self.c=cases.CommercialTests();self.c.setUp();self.addCleanup(self.c.tearDown);self.c.load_master()
 def convert(self,quote,actor=None):return self.c.cm('presupuestos/convertir',{'id':quote['id'],'revision':quote['revision']},actor)
 def test_separate_document_keeps_quote_prices_and_no_stock_movement(self):
  c=self.c;quote=c.order(condiciones='Condición acordada',observaciones='Observación cotizada',partidas=[{'sku':cases.SKU,'cantidad':'2','precio':'116','descuento':'10'}]);c.load_master('232');result=self.convert(quote);order=result['documento'];accepted=result['presupuesto']
  self.assertNotEqual(order['id'],quote['id']);self.assertNotEqual(order['folio'],quote['folio']);self.assertEqual(order['presupuestoId'],quote['id']);self.assertEqual(order['presupuestoOrigen'],quote['folio']);self.assertEqual(order['partidas'],quote['partidas']);self.assertEqual(order['total'],quote['total']);self.assertEqual(order['condiciones'],quote['condiciones']);self.assertEqual(order['observaciones'],quote['observaciones'])
  self.assertEqual(accepted['folio'],quote['folio']);self.assertEqual(accepted['estado'],'ACEPTADO');self.assertEqual(accepted['pedidoDestino'],order['id']);self.assertEqual(len(c.cm('documentos')['documentos']),2)
  self.assertIn(quote['folio'].encode(),c.call('/api/comercial/imprimir?canal=ventasins&id='+order['id'])[1]);self.assertIn(order['folio'].encode(),c.call('/api/comercial/imprimir?canal=ventasins&id='+quote['id'])[1])
  with c.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM inv_ledger').fetchone()[0],0);self.assertEqual(json.loads(db.execute('SELECT payload FROM cm_versions WHERE document=? AND revision=1',(quote['id'],)).fetchone()[0])['estado'],'PRESUPUESTO')
  self.assertEqual(c.call('/api/comercial/pedidos/bloqueo',{'id':accepted['id'],'revision':accepted['revision'],'bloqueado':False})[0],400)
 def test_concurrent_and_retried_conversion_creates_one_order(self):
  quote=self.c.order()
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.convert(quote),range(2)))
  self.assertEqual(results[0]['documento']['id'],results[1]['documento']['id']);self.assertEqual(sum(r.get('repetido',False) for r in results),1);self.assertEqual(len([d for d in self.c.cm('documentos')['documentos'] if d['tipo']=='PEDIDO']),1)
 def test_failure_after_order_insert_rolls_back_documents_and_folios(self):
  c=self.c;quote=c.order();cm=c.http.RequestHandlerClass.commercial.cm;persist=cm.persist;sequence=next(s for s in c.cm('folios')['series'] if s['tipo']=='PEDIDO')
  def fail_accept(db,value,*args,**kwargs):
   if value['tipo']=='PRESUPUESTO' and value.get('pedidoDestino'):raise ValueError('Fallo simulado al aceptar')
   return persist(db,value,*args,**kwargs)
  with patch.object(cm,'persist',side_effect=fail_accept):self.assertEqual(c.call('/api/comercial/presupuestos/convertir',{'id':quote['id'],'revision':quote['revision']})[0],400)
  self.assertEqual(len(c.cm('documentos')['documentos']),1);self.assertEqual(next(s for s in c.cm('folios')['series'] if s['tipo']=='PEDIDO')['siguiente'],sequence['siguiente']);self.assertEqual(self.convert(quote)['documento']['tipo'],'PEDIDO')
 def test_sales_profile_operates_only_own_customers_and_documents(self):
  c=self.c;seller=c.new_user('ventas',[c.company]);other=c.new_user('ventasins',[c.company]);self.assertTrue(c.cm('meta',actor=seller)['puedeOperar'])
  customer=c.cm('clientes',{'empresa':c.company,'nombre':'Cliente asignado por gerencia'})['id']
  denied={'canal':'ventasins','empresa':c.company,'sucursal':'CENTRAL','clave':'test_unassigned_client_123','cliente':customer,'partidas':[{'sku':cases.SKU,'cantidad':'1'}]}
  self.assertEqual(c.call('/api/comercial/pedidos',denied,seller)[0],403)
  c.value('/api/crm/asignar',{'empresa':c.company,'cliente':customer,'vendedor':'ventas@example.test','revision':0})
  quote=c.order(seller,cliente=customer);order=self.convert(quote,seller)['documento'];self.assertEqual(order['creador'],'ventas@example.test')
  self.assertEqual(c.call('/api/comercial/presupuestos/convertir',{'id':quote['id'],'revision':quote['revision']},other)[0],403)
  self.assertEqual(c.call('/api/comercial/clientes',{'empresa':c.company,'nombre':'No autorizado'},seller)[0],403)
  c.cm('pedidos/bloqueo',{'id':order['id'],'revision':order['revision'],'bloqueado':False},seller)
 def test_pending_cancellation_stale_revision_and_inactive_product_block_conversion(self):
  c=self.c;quote=c.order();self.assertEqual(c.call('/api/comercial/presupuestos/convertir',{'id':quote['id'],'revision':0})[0],409)
  c.cm('pedidos/cancelacion/solicitar',{'id':quote['id'],'revision':quote['revision'],'motivo':'Pendiente de decisión'})
  self.assertEqual(c.call('/api/comercial/presupuestos/convertir',{'id':quote['id'],'revision':quote['revision']})[0],400)
  another=c.order()
  with c.store.connect() as db:
   row=db.execute('SELECT payload FROM cm_products WHERE sku=?',(cases.SKU,)).fetchone();product=json.loads(row[0]);product['activo']=False;db.execute('UPDATE cm_products SET payload=? WHERE sku=?',(json.dumps(product),cases.SKU))
  self.assertEqual(c.call('/api/comercial/presupuestos/convertir',{'id':another['id'],'revision':another['revision']})[0],400)

if __name__=='__main__':unittest.main()
