"""HTTP y SQLite reales: salida/regreso TPV y cierre por empresa/sucursal."""
import datetime,json,unittest,uuid
from unittest.mock import patch
import test_production as production

from pos_fixture import seed_pos_stock

class POSInventoryGlobalTests(unittest.TestCase):
 def setUp(self):
  self.p=production.ProductionTests();self.p.setUp();self.addCleanup(self.p.doCleanups);self.c=self.p.c;self.w=self.p.locations['terminado']
  self.cm=self.c.http.RequestHandlerClass.commercial.cm
  with self.c.store.atomic() as db:
   co=self.cm.company(self.c.company,{'email':'test','role':'superadmin'},db=db);co.update({'rfc':'AAA010101AAA'});db.execute('UPDATE cm_companies SET payload=? WHERE id=?',(json.dumps(co),self.c.company))
  seed_pos_stock(self.c,self.c.company,self.p.pt,'10',self.w)
  self.box=self.api('cajas',{'empresa':self.c.company,'sucursal':'CENTRAL','codigo':'TPV1','nombre':'Caja TPV','lista':'PUBLICO'})['id']
  self.session=self.api('sesiones/abrir',{'empresa':self.c.company,'caja':self.box,'fondo':'0'})
  self.api('tpv/configuracion',{'empresa':self.c.company,'sucursal':'CENTRAL','revision':0,'almacen':self.w,'facturaGlobal':True,'codigoPostal':'06000','regimenFiscal':'601'})
  self.day=(datetime.date.fromisoformat(__import__('requisiciones').now()[:10])-datetime.timedelta(days=1)).isoformat()
 def api(self,path,data=None,actor=None,**query):
  from urllib.parse import urlencode
  url='/api/comercial/'+path+('?' +urlencode({'canal':'expendios','empresa':self.c.company,**query}) if data is None else '')
  return self.c.value(url,None if data is None else {'canal':'expendios',**data},actor)
 def request(self,path,data,actor=None):return self.c.call('/api/comercial/'+path,{'canal':'expendios',**data},actor)[0]
 def sale(self,qty='1',ticket=False,**fields):
  data={'empresa':self.c.company,'sesion':self.session['id'],'clave':uuid.uuid4().hex,'partidas':[{'sku':self.p.pt,'cantidad':qty}],'metodo':'EFECTIVO','recibido':'5000','formaPago':'01','soloTicket':ticket,**fields}
  with patch('comercial.now',return_value=self.day+'T12:00:00-06:00'):result=self.api('cobrar',data)
  return result['documento'],data
 def quantity(self,w=None):return self.p.quantity(w or self.w,self.p.pt)
 def period(self):return {'empresa':self.c.company,'sucursal':'CENTRAL','desde':self.day,'hasta':self.day,'periodicidad':'01'}
 def review(self):return self.api('tpv/global/revisar',self.period())
 def global_data(self):return {**self.period(),'clave':uuid.uuid4().hex,'huellaRevision':self.review()['huellaRevision'],'reconocerFueraPlazo':True}
 def cancel(self,d,approve=True):
  pending=self.api('cancelaciones',{'id':d['id'],'revision':d['revision'],'motivo':'Regreso físico de prueba'})['solicitud']
  data={'id':pending['id'],'revision':pending['revision'],'aprobar':approve};return self.api('cancelaciones/resolver',data),data
 def test_issue_and_cancel_post_once_at_original_cost_and_warehouse(self):
  d,data=self.sale('2');self.assertEqual(self.quantity(),'8');self.api('cobrar',data);self.assertEqual(self.quantity(),'8')
  self.assertEqual(d['inventario']['almacen'],self.w)
  self.api('tpv/configuracion',{'empresa':self.c.company,'sucursal':'CENTRAL','revision':1,'almacen':self.c.w,'facturaGlobal':False})
  _,decision=self.cancel(d);self.assertEqual(self.quantity(),'10');self.assertEqual(self.request('cancelaciones/resolver',decision),409);self.assertEqual(self.quantity(),'10')
  with self.c.store.connect() as db:
   moves=[json.loads(p) for p, in db.execute("SELECT payload FROM inv_ledger WHERE json_extract(payload,'$.tipo') IN ('TPV_EMISION','TPV_CANCELACION')")]
  self.assertEqual(len(moves),2);self.assertEqual(moves[1]['costoUnitario'],'20');self.assertEqual(moves[1]['referencia'],d['folio'])
 def test_insufficient_stock_rolls_back_document_folio_and_all_lines(self):
  with self.c.store.connect() as db:before=db.execute('SELECT count(*) FROM cm_documents').fetchone()[0]
  with self.assertRaises(AssertionError):self.sale('11')
  self.assertEqual(self.quantity(),'10')
  with self.c.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM cm_documents').fetchone()[0],before)
 def test_rejected_cancellation_does_not_restore_stock(self):
  d,_=self.sale();self.cancel(d,False);self.assertEqual(self.quantity(),'9')
 def test_ticket_and_payment_only_one_stock_exit(self):
  d,_=self.sale(ticket=True);self.assertEqual(d['estado'],'EMITIDA');self.assertEqual(self.quantity(),'9');self.assertEqual(self.review()['notas'],[])
  d=self.api('tpv/pago',{'id':d['id'],'revision':d['revision'],'formaPago':'28','recibido':'116'})['documento'];self.assertEqual(d['estado'],'PAGADA');self.assertEqual(self.quantity(),'9');self.assertEqual(self.review()['notas'][0]['formaPago'],'28')
  self.assertEqual(self.request('tpv/pago',{'id':d['id'],'revision':d['revision'],'formaPago':'28'}),400)
 def test_global_snapshots_tax_and_notes_without_second_stock_or_sale(self):
  a,_=self.sale('2');b,_=self.sale('1');before=self.quantity();review=self.review();self.assertEqual(len(review['notas']),2);self.assertEqual(review['total'],'348.00')
  data={**self.period(),'clave':uuid.uuid4().hex,'huellaRevision':review['huellaRevision'],'reconocerFueraPlazo':True};g=self.api('tpv/global/crear',data)['documento'];self.assertEqual(g['estado'],'PENDIENTE_PAC');self.assertEqual(self.quantity(),before)
  self.assertEqual(self.api('tpv/global/crear',data)['documento']['id'],g['id']);self.assertEqual(len(self.review()['notas']),0)
  self.assertEqual(self.api('documentos')['totales']['total'],'348.00');self.assertEqual(self.api('sesiones')['sesiones'][0]['cobrado'],'348.00')
  f=g['fiscal'];self.assertEqual(f['Receptor']['Rfc'],'XAXX010101000');self.assertEqual(f['Receptor']['RegimenFiscalReceptor'],'616');self.assertEqual(f['Receptor']['UsoCFDI'],'S01');self.assertEqual(f['TotalImpuestosTrasladados'],'48.00');self.assertEqual(len(f['Conceptos']),2)
  self.assertEqual(f['Conceptos'][0]['ClaveUnidad'],'ACT');self.assertEqual(f['Conceptos'][0]['Traslados'][0]['Impuesto'],'002')
  status,pdf,_=self.c.call('/api/comercial/tpv/global/pdf?canal=expendios&id='+g['id']);self.assertEqual(status,200);self.assertTrue(pdf.startswith(b'%PDF'))
  snapshot=self.c.value('/api/respaldos?modulo=comercial');self.assertTrue(snapshot)
 def test_global_blocks_note_cancel_until_global_preparation_is_cancelled(self):
  d,_=self.sale();g=self.api('tpv/global/crear',self.global_data())['documento'];pending=self.api('cancelaciones',{'id':d['id'],'revision':d['revision'],'motivo':'Regreso físico'})['solicitud'];decision={'id':pending['id'],'revision':1,'aprobar':True}
  self.assertEqual(self.request('cancelaciones/resolver',decision),400);self.assertEqual(self.quantity(),'9')
  self.api('tpv/global/cancelar',{'id':g['id'],'revision':g['revision'],'motivo':'Revisión de cierre'});self.assertEqual(self.quantity(),'9');self.api('cancelaciones/resolver',decision);self.assertEqual(self.quantity(),'10')
 def test_stale_review_and_branch_disabled_are_rejected(self):
  self.sale();data=self.global_data();self.sale();self.assertEqual(self.request('tpv/global/crear',data),409)
  self.assertEqual(self.request('tpv/global/revisar',{**self.period(),'sucursal':'NORTE'}),400)
  self.api('tpv/configuracion',{'empresa':self.c.company,'sucursal':'CENTRAL','revision':1,'facturaGlobal':False,'almacen':self.w})
  self.assertEqual(self.request('tpv/global/crear',self.period()),400)
 def test_reset_cycle_prevents_historical_stock_inflation(self):
  d,_=self.sale()
  with self.c.store.connect() as db:db.execute('UPDATE inv_warehouses SET cycle=cycle+1 WHERE id=?',(self.w,))
  pending=self.api('cancelaciones',{'id':d['id'],'revision':d['revision'],'motivo':'Cambio de ciclo'})['solicitud'];self.assertEqual(self.request('cancelaciones/resolver',{'id':pending['id'],'revision':1,'aprobar':True}),409);self.assertEqual(self.quantity(),'9')
 def test_global_requires_manager_and_scope(self):
  email='tpv@example.test';self.c.value('/api/users',{'email':email,'name':'Operador','role':'expendios','password':self.c.password,'active':True});self.api('accesos',{'email':email,'revision':0,'empresas':[self.c.company],'sucursales':['CENTRAL'],'cajas':[self.box],'acciones':[]});actor=self.c.login(email)
  self.assertEqual(self.request('tpv/global/revisar',self.period(),actor),403)
  self.assertEqual(self.request('tpv/configuracion',{'empresa':self.c.company,'sucursal':'CENTRAL','revision':1,'almacen':self.w},actor),403)
 def test_global_excludes_cancelled_nominative_ambiguous_payment_and_retention(self):
  cancelled,_=self.sale();self.cancel(cancelled)
  ambiguous,_=self.sale(metodo='TARJETA',formaPago=None)
  d,_=self.sale()
  with self.c.store.connect() as db:
   v=json.loads(db.execute('SELECT payload FROM cm_documents WHERE id=?',(d['id'],)).fetchone()[0]);v['partidas'][0]['iva']='-16';db.execute('UPDATE cm_documents SET payload=? WHERE id=?',(json.dumps(v),d['id']))
  review=self.review();self.assertEqual(review['notas'],[]);self.assertEqual(len(review['excluidas']),3)

if __name__=='__main__':unittest.main()
