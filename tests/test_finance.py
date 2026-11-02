import unittest,uuid
import test_purchase_v3 as purchase_cases

class FinanceTests(unittest.TestCase):
 def setUp(self):
  self.c=purchase_cases.PurchaseV3Tests();self.c.setUp();self.addCleanup(self.c.tearDown);self.company=self.c.company
 def concept(self,book='CXP'):
  return self.c.value('/api/finanzas/conceptos',{'empresa':self.company,'libro':book,'nombre':'Concepto de prueba'})['id']
 def account(self,book='CXP',**extra):
  return {'empresa':self.company,'libro':book,'tercero':self.c.vendor,'concepto':self.concept(book),'referencia':uuid.uuid4().hex,'fecha':'2026-10-01','vencimiento':'2026-11-30','moneda':'MXN','importe':'100',**extra}
 def row(self,id,book='CXP'):
  return next(r for r in self.c.value('/api/finanzas/cuentas?empresa='+str(self.company)+'&libro='+book)['cuentas'] if r['id']==id)
 def test_partial_payments_retries_refunds_and_cancellation_keep_exact_balance(self):
  id=self.c.value('/api/finanzas/cuentas',self.account())['id'];data={'cuenta':id,'tipo':'ABONO','importe':'40','fecha':'2026-10-20','referencia':'PAGO-1','metodo':'TRANSFERENCIA','revision':1,'clave':uuid.uuid4().hex}
  payment=self.c.value('/api/finanzas/pagos',data);self.assertTrue(self.c.value('/api/finanzas/pagos',data)['repetido']);self.assertEqual(self.row(id)['saldo'],'60.00')
  self.assertEqual(self.c.call('/api/finanzas/pagos',{**data,'importe':'41'})[0],409)
  self.assertEqual(self.c.call('/api/finanzas/pagos',{**data,'clave':uuid.uuid4().hex,'importe':'61','revision':2})[0],400)
  self.assertEqual(self.c.call('/api/finanzas/pagos',{**data,'clave':uuid.uuid4().hex,'importe':'1','revision':1})[0],409)
  refund=self.c.value('/api/finanzas/pagos',{**data,'tipo':'REEMBOLSO','importe':'10','revision':2,'clave':uuid.uuid4().hex})['id'];self.assertEqual(self.row(id)['saldo'],'70.00')
  self.assertEqual(self.c.call('/api/finanzas/cancelar',{'cuenta':id,'pago':payment['id'],'revision':3,'motivo':'Prueba'})[0],400)
  self.c.value('/api/finanzas/cancelar',{'cuenta':id,'pago':refund,'revision':3,'motivo':'Corrección de prueba'});self.assertEqual(self.row(id)['saldo'],'60.00')
 def test_purchase_link_uses_real_amount_and_cannot_be_registered_twice(self):
  doc=self.c.confirm(self.c.order());doc=self.c.move(doc,'2')['documento'];purchase=self.c.move(doc,'2','compra',referencia='FACTURA-PRUEBA')['movimiento'];data=self.account(importe=purchase['total'],compra=purchase['id'])
  self.assertEqual(self.c.call('/api/finanzas/cuentas',{**data,'importe':'1'})[0],400)
  self.c.value('/api/finanzas/cuentas',data);self.assertEqual(self.c.call('/api/finanzas/cuentas',{**data,'referencia':'OTRA'})[0],400)
  other=self.c.value('/api/comercial/empresas',{'nombre':'Otra prueba','sucursales':['CENTRAL']})['id'];self.assertEqual(self.c.call('/api/finanzas/meta?empresa='+str(other)+'&libro=CXP',actor=self.c.buyer)[0],403)
 def test_customer_balances_permissions_company_and_currency_are_separate(self):
  customer=self.c.value('/api/comercial/clientes',{'empresa':self.company,'nombre':'Cliente prueba','canales':['ventasins']})['id'];data=self.account('CXC',tercero=customer,moneda='USD');id=self.c.value('/api/finanzas/cuentas',data)['id']
  result=self.c.value('/api/finanzas/cuentas?empresa='+str(self.company)+'&libro=CXC');self.assertEqual(result['saldosPorMoneda'],{'USD':'100.00'})
  self.assertEqual(self.c.call('/api/finanzas/cuentas',data,self.c.buyer)[0],403)
  self.assertEqual(self.c.call('/api/finanzas/cuentas',{**data,'referencia':'Otra','importe':'0.001'})[0],400)
  self.c.value('/api/finanzas/cancelar',{'cuenta':id,'revision':1,'motivo':'Corrección'});self.assertEqual(self.row(id,'CXC')['estado'],'CANCELADA')

if __name__=='__main__':unittest.main()
