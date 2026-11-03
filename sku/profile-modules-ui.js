async function loadModuleProfiles(){
 const response=await fetch('/api/perfiles',{cache:'no-store'}),data=await response.json();if(!response.ok)throw Error(data.error);
 $('perfilesModulosError').textContent='Los accesos efectivos requieren perfil y módulo contratado. Revisa Menú de aplicaciones → Módulos contratados. Las cuentas internas conservan acceso completo.';
 $('perfilesModulosTabla').replaceChildren();const head=$('perfilesModulosTabla').closest('table').querySelector('thead');head.replaceChildren();const header=document.createElement('tr');
 for(const label of ['Perfil',...Object.values(data.modulos),'Acceso efectivo / acciones']){const th=document.createElement('th');th.textContent=label;header.append(th);}head.append(header);
 for(const profile of data.perfiles){
  const tr=document.createElement('tr');td(tr,profile.nombre);const checks={};
  for(const key of Object.keys(data.modulos)){
   const cell=td(tr,''),input=document.createElement('input');input.type='checkbox';input.checked=profile.modulos.includes(key);
   input.disabled=profile.perfil==='superadmin'||currentUser.role!=='superadmin'||profile.perfil==='requisicion'&&key!=='requisiciones'||profile.perfil==='ventaspasteleria'&&key!=='ventasins';
   input.setAttribute('aria-label',profile.nombre+' · '+data.modulos[key]);checks[key]=input;cell.append(input);
   if(profile.perfil!=='superadmin'&&profile.pendientesContrato?.includes(key)){const note=document.createElement('small');note.textContent='Pendiente de contratación';cell.append(note);}
  }
  const action=td(tr,''),status=document.createElement('span');status.className='note';status.textContent=profile.perfil==='superadmin'?'Administración; las cuentas internas conservan acceso completo.':(profile.efectivos?.length??profile.modulos.length)+' módulos efectivos. '+(profile.pendientesContrato?.length?'Hay accesos pendientes de contratación.':'');
  if(profile.perfil!=='superadmin'&&currentUser.role==='superadmin'){
   const button=document.createElement('button');button.textContent='Guardar accesos';button.className='secondary';button.onclick=async()=>{
    button.disabled=true;try{
     const result=await fetch('/api/perfiles',{method:'PUT',headers:{'Content-Type':'application/json','X-CSRF-Token':currentUser.csrf},body:JSON.stringify({perfil:profile.perfil,revision:profile.revision,modulos:Object.keys(checks).filter(k=>checks[k].checked)})}),updated=await result.json();if(!result.ok)throw Error(updated.error);await loadModuleProfiles();
    }catch(err){status.textContent=err.message;}finally{button.disabled=false;}
   };action.append(button);
  }
  action.append(status);$('perfilesModulosTabla').append(tr);
 }
}
$('perfilesModulosPanel').hidden=!canDelete;$('perfilesModulosActualizar').onclick=async()=>{try{await loadModuleProfiles();}catch(err){$('perfilesModulosError').textContent=err.message;}};if(canDelete){try{await loadModuleProfiles();}catch(err){$('perfilesModulosError').textContent=err.message;}}
