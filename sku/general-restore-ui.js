// El ZIP se valida en servidor; seleccionar o revisar nunca restaura datos.
let bkGeneralReview=null;
const bkGeneralRestoreControls=['bkGeneralRestoreFile','bkGeneralRestoreReview','bkGeneralRestorePassword','bkGeneralRestoreText','bkGeneralRestoreCheck','bkGeneralRestoreCancel'];
function bkGeneralReady(){$('bkGeneralRestoreConfirm').disabled=bkBusy||!bkGeneralReview||!$('bkGeneralRestoreCheck').checked||$('bkGeneralRestoreText').value!=='RESTAURAR TODO'||!$('bkGeneralRestorePassword').value;}
function bkGeneralCancel(){bkGeneralReview=null;$('bkGeneralRestoreSummary').hidden=true;$('bkGeneralRestoreText').value='';$('bkGeneralRestorePassword').value='';$('bkGeneralRestoreCheck').checked=false;bkGeneralReady();}
$('bkGeneralRestoreCard').hidden=!currentUser.internalAdmin;
$('bkGeneralRestoreFile').onchange=()=>{bkGeneralCancel();$('bkGeneralRestoreReview').disabled=!$('bkGeneralRestoreFile').files.length;$('bkGeneralRestoreMessage').textContent='';};
$('bkGeneralRestoreCancel').onclick=bkGeneralCancel;
for(const id of ['bkGeneralRestorePassword','bkGeneralRestoreText','bkGeneralRestoreCheck'])$(id).addEventListener('input',bkGeneralReady);
$('bkGeneralRestoreReview').onclick=async()=>{
 const file=$('bkGeneralRestoreFile').files[0];if(!file||bkBusy)return;bkGeneralCancel();
 if(file.size>128*1024*1024){$('bkGeneralRestoreMessage').textContent='El ZIP no debe superar 128 MB.';return;}
 bkBusy=true;$('bkGeneralRestoreReview').disabled=true;
 try{
  $('bkGeneralRestoreMessage').textContent='Verificando ZIP, hashes, estructura y base de datos…';
  const response=await fetch('/api/respaldos/general/restaurar/revisar',{method:'POST',headers:{'Content-Type':'application/zip','X-CSRF-Token':currentUser.csrf},body:file});const result=await response.json();if(!response.ok)throw Error(result.error||'No se pudo revisar el respaldo.');
  bkGeneralReview=result;$('bkGeneralRestoreRows').replaceChildren();
  for(const label of Object.keys(result.actual)){const tr=document.createElement('tr');for(const value of [label,result.actual[label],result.respaldo[label]??'—'])td(tr,value);$('bkGeneralRestoreRows').append(tr);}
  $('bkGeneralRestoreInfo').textContent='Respaldo: '+result.creadoUTC+' · Versión '+result.version+'. Revisión válida durante 30 minutos; si cambian los datos debes revisarlo otra vez.';
  $('bkGeneralRestoreSummary').hidden=false;$('bkGeneralRestoreMessage').textContent='Revisión correcta. Aún no se han modificado datos.';
 }catch(error){$('bkGeneralRestoreMessage').textContent=error.message;}finally{bkBusy=false;$('bkGeneralRestoreReview').disabled=false;bkGeneralReady();}
};
$('bkGeneralRestoreConfirm').onclick=async()=>{
 if(bkBusy||!bkGeneralReview||$('bkGeneralRestoreConfirm').disabled)return;bkBusy=true;bkGeneralReady();for(const id of bkGeneralRestoreControls)$(id).disabled=true;
 try{
  $('bkGeneralRestoreMessage').textContent='Esperando operaciones activas, guardando copia previa y restaurando… No cierres esta página.';
  const result=await bkJSON('/general/restaurar/confirmar',{id:bkGeneralReview.id,texto:$('bkGeneralRestoreText').value,password:$('bkGeneralRestorePassword').value,confirmar:$('bkGeneralRestoreCheck').checked});
  $('bkGeneralRestorePassword').value='';$('bkGeneralRestoreMessage').textContent=result.mensaje+' La copia anterior está guardada en el servidor y podrás descargarla al volver a iniciar sesión.';
  sessionStorage.setItem('jm.general.previous',result.respaldoPrevio);$('bkGeneralRestoreLogin').hidden=false;$('bkGeneralRestoreSummary').hidden=true;
 }catch(error){$('bkGeneralRestorePassword').value='';$('bkGeneralRestoreMessage').textContent=error.message;bkBusy=false;for(const id of bkGeneralRestoreControls)$(id).disabled=false;bkGeneralReady();}
};
try{const id=sessionStorage.getItem('jm.general.previous');if(currentUser.internalAdmin&&/^[a-f0-9]{32}$/.test(id||'')){const link=$('bkGeneralRestorePrevious');link.href='/api/respaldos/general/previo/'+id;link.hidden=false;link.setAttribute('download','ERP_JM_General_Previo.zip');}}catch{}

$('bkGoGeneralRestore').hidden=!currentUser.internalAdmin;
