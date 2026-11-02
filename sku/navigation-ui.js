// Cada módulo muestra una tarea a la vez y sus opciones se eligen en el menú lateral.
function jmSubviewHeading(parent,title){const heading=document.createElement('div');heading.className='section-heading';const h=document.createElement('h3');h.textContent=title;heading.append(h);parent.querySelector(':scope > summary')?.after(heading);if(!heading.parentNode)parent.prepend(heading);}
const reportPanel=$('rpPanel'),reportNotes=[...reportPanel.querySelectorAll(':scope > p')],reportSelection=$('rpSeleccion').closest('.grid'),reportActions=$('rpVer').closest('.actions');
jmSubviewHeading(reportPanel,'Reportes de requisición');jmTabs(reportPanel,'reportes',[
 ['consulta','Consultar y descargar',[reportNotes[0],reportSelection,reportActions,reportNotes[1],$('rpResultado')]],
 ['configurar','Configurar reportes',[$('jmReportBuilder')],rpCanEdit],
 ['costos','Costos y unidades',[$('rpCostosPanel')],rpCanEdit]
],'consulta');
$('rpCostosPanel').ontoggle=null;$('rpCostosPanel').classList.add('jm-flat-panel');
$('jmReportBuilder').open=true;$('jmReportBuilder').classList.add('jm-flat-panel');
for(const id of ['rpNuevo','rpCopia']){const old=$(id).onclick;$(id).onclick=async e=>{await old(e);jmNavigate('reportes','configurar');};}
const jmShowReport=rpShow;rpShow=function(result){jmShowReport(result);jmNavigate('reportes','consulta');};
const backupPage=$('jmBackupsPage'),backupCards=[...backupPage.querySelectorAll('.jm-backup-card:not(#bkGeneralCard)')],backupShared=document.createElement('div');backupShared.className='jm-catalog-toolbar';backupShared.append($('bkModulo').closest('label'),$('bkMensaje'),$('bkPrevio'));backupPage.querySelector('.jm-page-intro').after(backupShared);jmSubviewHeading(backupPage,'Administrar datos');jmTabs(backupPage,'respaldos',[
 ['general','Respaldo general',[$('bkGeneralCard')],currentUser.internalAdmin===true],['descargar','Respaldo por módulo',[backupCards[0]]],['restaurar','Restaurar respaldo',[backupCards[1]]],['reiniciar','Vaciar módulo',[backupCards[2]]]
],currentUser.internalAdmin?'general':'descargar');
backupShared.hidden=currentUser.internalAdmin===true;const jmBackupSelect=jmSelect;jmSelect=function(key,id){jmBackupSelect(key,id);if(key==='respaldos')backupShared.hidden=id==='general';};
const jmSubmenus={},jmSubButtons={};
for(const [route,group] of Object.entries(jmSegments)){
 const parent=jmButtons[route];if(!parent||!jmAllowed[route])continue;
 const originalTabs=Object.values(group.buttons)[0]?.parentElement;if(originalTabs)originalTabs.hidden=true;
 const panel=document.createElement('div');panel.id='jmSubmenu-'+route;panel.className='jm-submenu';panel.setAttribute('aria-label','Opciones de '+jmNames[route]);panel.hidden=true;parent.after(panel);parent.classList.add('jm-nav-parent');parent.setAttribute('aria-controls',panel.id);parent.setAttribute('aria-expanded','false');const chevron=document.createElement('span');chevron.className='jm-nav-chevron';chevron.textContent='⌄';chevron.setAttribute('aria-hidden','true');parent.append(chevron);jmSubmenus[route]=panel;jmSubButtons[route]={};
 for(const [id,tab] of Object.entries(group.buttons)){if(tab.hidden)continue;const button=document.createElement('button');button.type='button';button.id='jm-nav-'+route+'-'+id;button.textContent=tab.textContent;button.onclick=()=>jmNavigate(route,id);panel.append(button);jmSubButtons[route][id]=button;}
 parent.onclick=()=>{if(jmMobileNav.matches){const opening=panel.hidden;for(const [other,view] of Object.entries(jmSubmenus)){view.hidden=true;jmButtons[other].setAttribute('aria-expanded','false');}panel.hidden=!opening;parent.setAttribute('aria-expanded',String(opening));return;}if(document.body.classList.contains('jm-compact'))document.body.classList.remove('jm-compact');jmNavigate(route,group.active);};
}
function jmSyncSubmenus(){for(const [route,panel] of Object.entries(jmSubmenus)){const active=route===jmActive;panel.hidden=!active;jmButtons[route].setAttribute('aria-expanded',String(active));jmButtons[route].removeAttribute('aria-current');jmButtons[route].classList.toggle('jm-parent-active',active);for(const [id,button] of Object.entries(jmSubButtons[route])){if(active&&jmSegments[route].active===id)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');}}if(jmSegments[jmActive]){const tab=jmSegments[jmActive].buttons[jmSegments[jmActive].active];$('jmPageTitle').textContent=tab.textContent;$('jmBreadcrumb').textContent='ERP JM Lite / '+jmNames[jmActive];}}
const jmSelectWithSidebar=jmSelect;jmSelect=function(key,id){jmSelectWithSidebar(key,id);jmSyncSubmenus();};
const jmRouteWithSidebar=jmRenderRoute;jmRenderRoute=async function(){await jmRouteWithSidebar();jmSyncSubmenus();if(jmActive==='requisiciones'&&jmSegments.requisiciones.active==='imagenes')await rqImagesLoad();if(jmActive==='reportes'&&jmSegments.reportes.active==='costos'){const panel=$('rpCostosPanel');if(!panel.open)panel.open=true;await rpLoadCosts();}};
for(const id of ['rqCargarPanel','cpMasterPanel','ventasImportarPanel','ventasLotePanel']){const panel=$(id);if(panel){panel.open=true;panel.classList.add('jm-flat-panel');}}
await jmRenderRoute();document.documentElement.setAttribute('data-submenus-ready','true');
