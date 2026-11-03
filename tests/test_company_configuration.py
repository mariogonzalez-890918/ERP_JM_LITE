import base64,io,json,unittest,uuid
from PIL import Image
import test_purchase_v3 as cases

class CompanyConfigurationTests(unittest.TestCase):
 def setUp(self):
  self.c=cases.PurchaseV3Tests();self.c.setUp();self.addCleanup(self.c.tearDown)
 def test_negative_retention_reduces_purchase_and_sales_tax_amount(self):
  c=self.c;tax=c.value('/api/empresa/impuestos',{'empresa':c.company,'nombre':'Retención configurada','tasa':'-16'})['id'];c.value('/api/empresa/impuestos',{'empresa':c.company,'vincular':True,'ambito':'compras','sku':c.material['sku'],'impuesto':tax})
  doc=c.order();self.assertEqual((doc['base'],doc['importeImpuesto'],doc['total']),('200.00','-32.00','168.00'))
  sku='010101TEST0001';c.value('/api/comercial/productos',{'empresa':c.company,'sku':sku,'nombre':'Producto con retención','unidad':'PIEZA','canales':['ventasins','expendios'],'impuestoId':tax,'precios':{'PUBLICO':'84','MINIMO':'80','REMATE':'70'}})
  doc=c.value('/api/comercial/pedidos',{'empresa':c.company,'sucursal':'CENTRAL','clave':uuid.uuid4().hex,'partidas':[{'sku':sku,'cantidad':'1'}]})['documento'];self.assertEqual((doc['base'],doc['impuesto'],doc['total']),('100.00','-16.00','84.00'))
  status,html,_=c.call('/api/comercial/imprimir?id='+doc['id']);self.assertEqual(status,200);self.assertIn(b'-16.00',html);self.assertIn('Retención configurada',html.decode())
  c.value('/api/empresa/impuestos',{'empresa':c.company,'id':tax,'revision':1,'nombre':'Retención configurada','tasa':'-10'});self.assertEqual(c.value('/api/comercial/documento?id='+doc['id'])['impuesto'],'-16.00')
  self.assertEqual(c.call('/api/empresa/impuestos',{'empresa':c.company,'nombre':'Inválida','tasa':'-101'})[0],400)
  from comercial import tax_line
  with self.assertRaises(ValueError):tax_line('1','84','-100')
 def test_companies_start_without_other_branches_and_have_own_principal(self):
  c=self.c;path='/api/empresa/razones-sociales';a=c.value(path,{'nombre':'Razón A','sucursales':[]})['id'];b=c.value(path,{'nombre':'Razón B','sucursales':[]})['id']
  c.value('/api/empresa/sucursales',{'empresa':a,'revision':1,'nombre':'UBICACION A','serie':'REQ-A','principal':True})
  c.value('/api/empresa/sucursales',{'empresa':b,'revision':1,'nombre':'UBICACION B','serie':'REQ-B','principal':True})
  companies={v['id']:v for v in c.value('/api/empresa/config')['razonesSociales']};self.assertEqual(companies[a]['sucursales'],['UBICACION A']);self.assertEqual(companies[b]['sucursales'],['UBICACION B']);self.assertEqual(companies[a]['sucursalPrincipal'],'UBICACION A');self.assertEqual(companies[b]['sucursalPrincipal'],'UBICACION B')
  self.assertEqual(c.call(path,{**companies[a],'sucursales':['UBICACION B'],'sucursalPrincipal':'UBICACION B'})[0],400)
  self.assertEqual(c.call('/api/empresa/sucursales',{'empresa':a,'revision':1,'nombre':'FALLA REVISION','serie':'REQ-FAIL'})[0],409)
  self.assertNotIn('FALLA REVISION',[r['nombre'] for r in c.value('/api/empresa/config')['sucursales']])
  cfg=c.value('/api/empresa/config')['empresa'];c.value('/api/empresa/config',{'nombre':'Datos de instalación','responsable':'Responsable','rubro':'Comercio','revision':cfg['revision'],'razonSocialPrincipal':a});self.assertEqual(c.value('/api/empresa/config')['empresa']['razonSocialPrincipal'],a)
  self.assertEqual(c.call('/api/empresa/sucursales',{'empresa':a,'revision':2,'nombre':'NO AUTORIZADA','serie':'REQ-NO'},c.buyer)[0],403)
 def test_issuer_logo_in_a4_ticket_and_legacy_print_without_foreign_brand(self):
  c=self.c
  def logo(color,revision):
   out=io.BytesIO();Image.new('RGB',(20,20),color).save(out,format='PNG');c.value('/api/empresa/logo',{'empresa':c.company,'revision':revision,'contenido':base64.b64encode(out.getvalue()).decode()});return c.value('/api/empresa/logo?empresa='+str(c.company))['imagen']
  original=logo('blue',0);purchase=c.order();sku='010101TEST0001';c.value('/api/comercial/productos',{'empresa':c.company,'sku':sku,'nombre':'Producto','unidad':'PIEZA','canales':['ventasins'],'iva':'16','precios':{'PUBLICO':'116'}})
  doc=c.value('/api/comercial/pedidos',{'empresa':c.company,'sucursal':'CENTRAL','clave':uuid.uuid4().hex,'partidas':[{'sku':sku,'cantidad':'1'}]})['documento'];current=logo('red',1)
  for fmt in ('a4','ticket'):
   status,raw,_=c.call('/api/comercial/imprimir?id='+doc['id']+'&formato='+fmt);self.assertEqual(status,200);html=raw.decode();self.assertIn(original,html);self.assertNotIn(current,html);self.assertNotIn('src="/logo.svg"',html)
  with c.store.connect() as db:
   value=json.loads(db.execute('SELECT payload FROM cm_documents WHERE id=?',(doc['id'],)).fetchone()[0]);value['emisor'].pop('logo');db.execute('UPDATE cm_documents SET payload=? WHERE id=?',(json.dumps(value),doc['id']))
  self.assertIn(current,c.call('/api/comercial/imprimir?id='+doc['id'])[1].decode())
  from pypdf import PdfReader
  status,pdf,_=c.call('/api/pedidoscompra/documento/pdf?id='+purchase['id']);self.assertEqual(status,200);self.assertGreater(len(PdfReader(io.BytesIO(pdf)).pages[0].images),0)

if __name__=='__main__':unittest.main()
