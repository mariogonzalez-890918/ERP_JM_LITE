import base64,json,unittest
import test_backup_import as fixtures

class QualityTests(unittest.TestCase):
 setUp=fixtures.ModuleBackupTests.setUp;tearDown=fixtures.ModuleBackupTests.tearDown;call=fixtures.ModuleBackupTests.call;value=fixtures.ModuleBackupTests.value;login=fixtures.ModuleBackupTests.login
 def save(self,module,code='FOR-001',data=None,**extra):return self.value('/api/calidad/guardar',{'modulo':module,'codigo':code,'titulo':'Registro ficticio','datos':data or {},**extra})['id']
 def get(self,id):return self.value('/api/calidad/registros?id='+id)
 def state(self,id,state):return self.value('/api/calidad/estado',{'id':id,'revision':self.get(id)['revision'],'estado':state})
 def test_extended_quality_modules_keep_registered_calibration_reminders(self):
  meta=self.value('/api/calidad/registros');self.assertEqual(len(meta['modulos']),15);id=self.save('calibrations','CAL-TEST',{'equipo':'Equipo ficticio','responsable':'Responsable de prueba','fecha':'2026-01-01','proxima_revision':'2026-01-02'});self.state(id,'REGISTRADO');pending=self.value('/api/calidad/tablero')['vencidosPendientes'];self.assertIn(id,[r['id'] for r in pending]);self.assertEqual(self.call('/api/calidad/guardar',{'id':id,'modulo':'calibrations','codigo':'CAL-TEST','titulo':'Modificar cerrado','revision':self.get(id)['revision'],'datos':{}})[0],400)
 def test_approved_form_record_snapshot_and_new_version(self):
  schema=[{'id':'medida','label':'Medida','type':'numero','required':True},{'id':'resultado','label':'Resultado','type':'lista','required':True,'options':['CUMPLE','NO CUMPLE']}]
  form=self.save('forms',data={'schema':schema});self.state(form,'APROBADO')
  self.assertEqual(self.call('/api/calidad/guardar',{'id':form,'revision':2,'modulo':'forms','codigo':'FOR-001','titulo':'Cambio no autorizado','datos':{'schema':schema}})[0],400)
  record=self.save('records','REG-001',{'formato':form,'valores':{'medida':'12.5','resultado':'CUMPLE'}});self.state(record,'REGISTRADO')
  new=self.value('/api/calidad/version',{'id':form,'revision':2})['id'];self.assertEqual(self.get(new)['version'],2);self.assertEqual(self.get(record)['datos']['versionFormato'],1);self.assertEqual(self.get(form)['estado'],'APROBADO')
 def test_invalid_record_and_revision_do_not_write(self):
  form=self.save('forms',data={'schema':[{'id':'f1','label':'Fecha','type':'fecha','required':True}]});self.state(form,'APROBADO')
  self.assertEqual(self.call('/api/calidad/guardar',{'modulo':'records','codigo':'R1','titulo':'Prueba','datos':{'formato':form,'valores':{}}})[0],400)
  self.assertEqual(self.value('/api/calidad/registros?modulo=records')['registros'],[])
  self.assertEqual(self.call('/api/calidad/estado',{'id':form,'revision':1,'estado':'OBSOLETO'})[0],409)
 def test_quality_profile_files_and_closed_version(self):
  self.value('/api/users',{'email':'quality@example.test','name':'Calidad prueba','role':'calidad','password':self.password,'active':True});quality=self.login('quality@example.test')
  item=self.value('/api/calidad/guardar',{'modulo':'documents','codigo':'DOC-001','titulo':'Documento prueba','datos':{}},quality)['id']
  self.value('/api/calidad/archivo',{'id':item,'revision':1,'nombre':'evidencia.txt','contenido':base64.b64encode(b'evidencia ficticia').decode()},quality);item_data=self.get(item)
  status,body,_=self.call('/api/calidad/archivo/'+item_data['archivos'][0]['id'],actor=quality);self.assertEqual(status,200);self.assertEqual(body,b'evidencia ficticia')
  self.assertEqual(self.call('/api/empresa/config',actor=quality)[0],403);self.state(item,'APROBADO');self.assertEqual(self.call('/api/calidad/archivo',{'id':item,'revision':3,'nombre':'otro.txt','contenido':'YQ=='},quality)[0],400)

if __name__=='__main__':unittest.main()
