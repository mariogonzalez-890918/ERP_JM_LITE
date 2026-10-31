// Presentación y navegación. Los permisos y las operaciones siguen en el servidor.
const jmPaths={brain:'<path d="M12 5a4 4 0 0 0-7-2 4 4 0 0 0-3 6 4 4 0 0 0 0 6 4 4 0 0 0 4 6 4 4 0 0 0 6-2V5Zm0 0a4 4 0 0 1 7-2 4 4 0 0 1 3 6 4 4 0 0 1 0 6 4 4 0 0 1-4 6 4 4 0 0 1-6-2M5 7l3 2v4M4 16l4-1M19 7l-3 2v4M20 16l-4-1"/>',currency:'<path d="M12 2v20M18 6H9a4 4 0 0 0 0 8h6a3 3 0 0 1 0 6H5"/>',computer:'<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 22h8M12 17v5M6 7h12"/>',warehouse:'<path d="m2 9 10-7 10 7v13H2V9Zm5 13V11h10v11M7 15h10M7 19h10"/>',pos:'<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M7 6h10v4H7zM8 14h1M12 14h1M16 14h1M8 18h1M12 18h5"/>',home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>',buy:'<path d="M3 3h2l2.5 12h11L21 6H6"/><circle cx="9" cy="20" r="1"/><circle cx="18" cy="20" r="1"/>',sell:'<path d="M20 13 11 22 2 13V3h10z"/><circle cx="7" cy="8" r="1"/>',box:'<path d="m3 7 9-5 9 5v10l-9 5-9-5zM3 7l9 5 9-5M12 12v10M7.5 4.5l9 5"/>',chart:'<path d="M4 3v18h17M8 16v-4M13 16V7M18 16V4"/>',check:'<path d="m9 12 2 2 4-5"/><path d="M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6z"/>',users:'<circle cx="9" cy="8" r="4"/><path d="M2 21v-3a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v3M17 4a4 4 0 0 1 0 8M22 21v-3a5 5 0 0 0-3-4.6"/>',lock:'<rect x="4" y="10" width="16" height="12" rx="3"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 15v3"/>',menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>',logout:'<path d="M10 4H4v16h6M9 12h12m-4-4 4 4-4 4"/>',plus:'<path d="M12 4v16M4 12h16"/>',branch:'<circle cx="5" cy="4" r="2"/><circle cx="5" cy="20" r="2"/><circle cx="19" cy="4" r="2"/><path d="M5 6v12M19 6v2a4 4 0 0 1-4 4H5"/>',list:'<rect x="5" y="3" width="14" height="19" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>'};
function jmIcon(name){const span=document.createElement('span');span.innerHTML='<svg class="jm-icon" viewBox="0 0 24 24" aria-hidden="true">'+(jmPaths[name]||jmPaths.box)+'</svg>';return span.firstChild;}
function jmLabel(button,label,icon){button.replaceChildren(jmIcon(icon));const text=document.createElement('span');text.className='jm-nav-text';text.textContent=label;button.append(text);button.title=label;button.setAttribute('aria-label',label);}
const jmAllowed={inicio:true,compras:canReadPurchases,ventas:salesRead,requisiciones:currentUser.modulos.includes('requisiciones'),reportes:currentUser.modulos.includes('requisiciones')&&currentUser.role!=='requisicion',autorizaciones:canDelete||currentUser.role!=='requisicion'&&currentUser.modulos.includes('requisiciones')&&rwEnabled,usuarios:canDelete,perfiles:canDelete,respaldos:canDelete};
const jmNames={inicio:'Inicio',compras:'SKU Compras',ventas:'SKU Ventas',requisiciones:'Requisición de materiales',reportes:'Reportes de requisición',autorizaciones:'Autorizaciones',usuarios:'Usuarios',perfiles:'Accesos por perfil',respaldos:'Respaldo y restauración'};
const jmViews={inicio:$('jmHome'),compras:$('comprasPanel'),ventas:$('ventasPanel'),requisiciones:$('requisicionesPanel'),reportes:$('jmReportsPage'),autorizaciones:$('jmApprovalsPage'),usuarios:$('jmUsersPage'),perfiles:$('jmProfilesPage'),respaldos:$('jmBackupsPage')};
const jmButtons={inicio:$('jmNavHome'),compras:$('tabCompras'),ventas:$('tabVentas'),requisiciones:$('tabRequisiciones'),reportes:$('jmNavReports'),autorizaciones:$('jmNavApprovals'),usuarios:$('jmNavUsers'),perfiles:$('jmNavProfiles'),respaldos:$('jmNavBackups')};
const jmIcons={inicio:'home',compras:'brain',ventas:'currency',requisiciones:'box',reportes:'chart',autorizaciones:'check',usuarios:'users',perfiles:'computer',respaldos:'lock'};
let jmActive='inicio',jmNavGeneration=0;
$('jmNav').append($('jmNavBackups'));
for(const route of ['compras','ventas','requisiciones'])$('jmModuleLinks').append(jmButtons[route]);
for(const [route,button] of Object.entries(jmButtons)){button.hidden=!jmAllowed[route];button.removeAttribute('role');button.removeAttribute('aria-selected');button.type='button';button.dataset.route=route;jmLabel(button,jmNames[route],jmIcons[route]);button.onclick=()=>jmNavigate(route);}
$('jmAdminCaption').hidden=!canDelete;
$('jmAppVersion').textContent=appInfo.titulo+' · Versión '+appInfo.version;$('jmAppSupport').textContent=appInfo.soporte;
$('jmMenuToggle').append(jmIcon('menu'));
$('jmAccountName').textContent=currentUser.name;$('jmAccountName').title=currentUser.internalAdmin?'Sistemas':currentUser.email;$('jmAccountRole').textContent=roleNames[currentUser.role];$('jmRoleBadge').textContent=roleNames[currentUser.role];$('jmAvatar').textContent=currentUser.name.split(/\s+/).slice(0,2).map(w=>w[0]).join('').toUpperCase();
$('jmLogout').append($('salir'));$('salir').prepend(jmIcon('logout'));
for(const [target,panel] of [['jmReportsPage','rpPanel'],['jmApprovalsPage','rwPanel'],['jmUsersPage','usuariosPanel'],['jmProfilesPage','perfilesModulosPanel']]){const detail=$(panel);$(target).append(detail);detail.classList.add('jm-flat-panel');if(['rpPanel','rwPanel'].includes(panel))detail.ontoggle=null;detail.open=true;}
for(const dialog of document.querySelectorAll('main dialog'))$('jmMain').append(dialog);
const jmBuilder=document.createElement('details');jmBuilder.id='jmReportBuilder';const jmBuilderSummary=document.createElement('summary');jmBuilderSummary.textContent='Configurar filtros e impuestos';jmBuilder.append(jmBuilderSummary);$('rpEditor').before(jmBuilder);jmBuilder.append($('rpEditor'));jmBuilder.hidden=!rpCanEdit;
for(const id of ['rpNuevo','rpCopia']){const original=$(id).onclick;$(id).onclick=async e=>{await original(e);jmBuilder.open=true;jmBuilder.scrollIntoView({behavior:'smooth',block:'start'});};}
const jmSegments={};
function jmTabs(parent,key,definitions,defaultTab){
 const nav=document.createElement('div');nav.className='jm-segments';nav.setAttribute('role','tablist');nav.setAttribute('aria-label','Opciones de '+jmNames[key]);parent.querySelector('.section-heading').after(nav);
 const views={},buttons={};
 for(const [id,label,nodes,allowed=true] of definitions){const view=document.createElement('div');view.id='jm-'+key+'-'+id;view.className='jm-subview';view.setAttribute('role','tabpanel');view.setAttribute('aria-labelledby','jm-tab-'+key+'-'+id);for(const node of nodes.filter(Boolean))view.append(node);parent.append(view);views[id]=view;
  const button=document.createElement('button');button.type='button';button.id='jm-tab-'+key+'-'+id;button.setAttribute('role','tab');button.setAttribute('aria-controls',view.id);button.textContent=label;button.hidden=!allowed;button.onclick=()=>jmSelect(key,id);nav.append(button);buttons[id]=button;
 }
 jmSegments[key]={views,buttons};jmSelect(key,defaultTab);
}
function jmSelect(key,id){const group=jmSegments[key];if(!group||!group.views[id]||group.buttons[id].hidden)return;for(const [name,view] of Object.entries(group.views)){view.hidden=name!==id;group.buttons[name].setAttribute('aria-selected',String(name===id));group.buttons[name].tabIndex=name===id?0:-1;}group.active=id;}
// Accesibilidad de las pestañas secundarias: flechas, Inicio y Fin.
document.addEventListener('keydown',e=>{if(!e.target.matches('.jm-segments [role=tab]'))return;const buttons=[...e.target.parentElement.querySelectorAll('button:not([hidden])')];let index=buttons.indexOf(e.target);if(e.key==='ArrowRight')index=(index+1)%buttons.length;else if(e.key==='ArrowLeft')index=(index+buttons.length-1)%buttons.length;else if(e.key==='Home')index=0;else if(e.key==='End')index=buttons.length-1;else return;e.preventDefault();buttons[index].click();buttons[index].focus();});
const purchaseNotes=[...$('comprasPanel').querySelectorAll(':scope > p')];const purchaseHelp=document.createElement('div');purchaseHelp.className='jm-help';for(const p of purchaseNotes)purchaseHelp.append(p);
jmTabs($('comprasPanel'),'compras',[
 ['catalogo','Catálogo',[$('excel').closest('.actions'),$('buscar').closest('.grid'),$('total'),$('registros').closest('.scroll')]],
 ['nuevo','Nuevo artículo',[$('nuevo').closest('details')],canEdit],
 ['cargar','Carga de lista',[$('listaTexto').closest('details')],canEdit],
 ['maestro','Maestro de compras',[$('maestroArchivo').closest('details')],canLoadMasters&&canReadPurchases],
 ['ayuda','Ayuda y códigos',[purchaseHelp,$('skuVerificar').closest('details'),$('catalogos').closest('details')]]
],'catalogo');
const salesNotes=[...$('ventasPanel').querySelectorAll(':scope > p:not([id])')],salesHelp=document.createElement('div');salesHelp.className='jm-help';for(const p of salesNotes)salesHelp.append(p);
jmTabs($('ventasPanel'),'ventas',[
 ['catalogo','Catálogo',[$('ventasActualizar').closest('.actions'),$('vBuscar').closest('.grid'),$('vTotal'),$('vRegistros').closest('.scroll')]],
 ['nuevo','Nuevo artículo',[$('ventasAltaPanel')],salesWrite&&salesRead],
 ['cargar','Carga de lista',[$('ventasLotePanel')],salesWrite&&salesRead],
 ['maestro','Maestro de ventas',[$('ventasImportarPanel')],canLoadMasters&&salesRead],
 ['ayuda','Ayuda y códigos',[salesHelp,$('vCatalogos').closest('details')]]
],'catalogo');
const jmOriginalEdit=vEdit;vEdit=function(record){jmSelect('ventas','nuevo');jmOriginalEdit(record);};
const reqHistoryHeading=$('rqHistSucursal').closest('.section-heading');if(currentUser.role==='requisicion')reqHistoryHeading.querySelector('h3').textContent='Mis requisiciones emitidas';
jmTabs($('requisicionesPanel'),'requisiciones',[
 ['nueva','Nueva solicitud',[$('rqAlta')],rqCanWrite],
 ['historial',currentUser.role==='requisicion'?'Mis requisiciones':'Historial',[reqHistoryHeading,$('rqHistTotal'),$('rqHistorial').closest('.scroll'),$('rqAnterior').closest('.actions')]],
 ['catalogo','Consultar materiales',[$('rqMasterInfo'),$('rqBuscarCatalogo').closest('details')],currentUser.role!=='requisicion'],
 ['maestro','Cargar maestro',[$('rqCargarPanel')],rqCanImport],
 ['imagenes','Imágenes por SKU',[$('rqImagesPanel')],currentUser.modulos.includes('imagenes')],
 ['series','Series y folios',[$('rqSeriesPanel')],rqCanConfigure],
 ['areas','Áreas solicitantes',[$('rqAreasPanel')],rqCanConfigure]
],rqCanWrite?'nueva':'historial');
for(const panel of [$('rqAlta'),$('ventasAltaPanel'),$('nuevo').closest('details')]){panel.classList.add('jm-flat-panel');panel.open=true;}
$('rqBuscarCatalogo').closest('details').open=true;$('rqSeriesPanel').open=true;
const jmMasterDownloads=document.createElement('div');jmMasterDownloads.className='actions';jmMasterDownloads.append($('rqCatalogoCSV'),$('rqMaestroOriginal'));jmSegments.requisiciones.views.catalogo.prepend(jmMasterDownloads);
const jmOriginalMaterials=rqRenderMaterials;rqRenderMaterials=function(){jmOriginalMaterials();const select=$('rqMaterial');select.size=Math.min(5,Math.max(1,select.options.length));select.style.height=select.options.length<=1?'48px':'145px';};
$('rqBuscarMaterial').oninput=rqRenderMaterials;
function jmStatusCell(cell,state){const badge=document.createElement('span');badge.className='jm-status jm-status-'+state.toLowerCase();badge.textContent=state;cell.replaceChildren(badge);}
const jmHistoryOriginal=rqHistory;rqHistory=async function(){await jmHistoryOriginal();for(const row of $('rqHistorial').rows){const cell=row.cells[5];if(cell)jmStatusCell(cell,cell.textContent.trim());}};
const jmChangesOriginal=rwLoad;rwLoad=async function(){await jmChangesOriginal();for(const row of $('rwTabla').rows){const cell=row.cells[0],parts=cell.textContent.split(' · '),status=parts.pop(),stamp=parts.join(' · ');const date=document.createElement('small');date.textContent=stamp;date.className='jm-status-date';jmStatusCell(cell,status);cell.prepend(date);}};
// Los maestros y la ayuda no compiten visualmente con la acción principal.
for(const id of ['excel','ventasActualizar','rqActualizar']){const actions=$(id).closest('.actions');if(actions){actions.classList.add('jm-section-tools');}}
// La media query coincide con CSS; los cambios de altura del navegador no cierran el menú.
const jmMobileNav=window.matchMedia('(max-width: 1024px)');
function jmSetMenu(open=false){
 const mobile=jmMobileNav.matches,expanded=mobile&&open;
 document.body.classList.toggle('jm-menu-open',expanded);
 $('jmShade').hidden=!expanded;$('jmSidebar').inert=mobile&&!expanded;
 $('jmMenuToggle').setAttribute('aria-expanded',String(mobile?expanded:!document.body.classList.contains('jm-compact')));
 $('jmMenuClose').hidden=!mobile;
}
function jmCloseMenu(){jmSetMenu(false);}
$('jmMenuToggle').onclick=()=>{if(jmMobileNav.matches){document.body.classList.remove('jm-compact');jmSetMenu(!document.body.classList.contains('jm-menu-open'));}else{document.body.classList.toggle('jm-compact');jmSetMenu();}};
$('jmMenuClose').onclick=()=>{jmCloseMenu();$('jmMenuToggle').focus({preventScroll:true});};
$('jmShade').onclick=jmCloseMenu;document.addEventListener('keydown',e=>{if(e.key==='Escape')jmCloseMenu();});
jmMobileNav.addEventListener('change',()=>{document.body.classList.remove('jm-compact');jmCloseMenu();});jmCloseMenu();
function jmNavigate(route,sub){if(!jmAllowed[route])route='inicio';const value=route+(sub?'/'+sub:'');if(location.hash.slice(1)===value)void jmRenderRoute();else location.hash=value;}
async function jmRenderRoute(){
 const generation=++jmNavGeneration;let [route,sub]=location.hash.slice(1).split('/');if(!jmAllowed[route]){route='inicio';history.replaceState(null,'','#inicio');}jmActive=route;
 for(const [name,view] of Object.entries(jmViews))view.hidden=name!==route;
 $('sinModulos').hidden=true;for(const [name,button] of Object.entries(jmButtons)){if(name===route)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');}
 $('jmPageTitle').textContent=jmNames[route];$('jmBreadcrumb').textContent='ERP JM Lite / '+(['usuarios','perfiles','respaldos'].includes(route)?'Administración':route==='inicio'?'Mi espacio':'Operación');jmCloseMenu();window.scrollTo({top:0,behavior:'instant'});
 if(sub&&jmSegments[route])jmSelect(route,sub);
 try{
  if(route==='ventas')await salesInit();
  if(['requisiciones','reportes','autorizaciones'].includes(route)&&currentUser.modulos.includes('requisiciones')&&!rqMeta)await rqLoad();
  if(route==='reportes')await rpInit();
  if(route==='autorizaciones'&&currentUser.modulos.includes('requisiciones'))await rwLoad();
  if(generation!==jmNavGeneration)return;
 }catch(err){if(generation!==jmNavGeneration)return;const id=route==='ventas'?'ventasMensaje':route==='reportes'?'rpMensaje':route==='autorizaciones'?'rwMensaje':'rqMensaje';$(id).textContent=err.message;}
}
const jmCardDescriptions={compras:['Productos de compra','Consulta el catálogo y crea códigos para tus insumos.','Catálogo','#f1eaf4','#87618f'],ventas:['Productos de venta','Administra tus productos comerciales y sus códigos.','Catálogo','#e7f1f5','#4e879d'],requisiciones:['Requisición de materiales','Solicita materiales o consulta el historial por sucursal.','Operación','#fcf0e1','#bc8b46'],reportes:['Reportes y costos','Revisa el consumo y descarga reportes en Excel o PDF.','Análisis','#e8f1ec','#5b9275'],autorizaciones:['Autorizar cambios','Revisa modificaciones, cancelaciones y sus resoluciones.','Control','#f7e9ed','#b06e83'],usuarios:['Usuarios','Administra las cuentas y sus almacenes asignados.','Administración','#eaf0fa','#6b86b8'],perfiles:['Accesos por perfil','Configura qué módulos puede consultar cada perfil.','Administración','#f0eaf3','#9476a3'],respaldos:['Respaldo y restauración','Guarda o recupera los datos de compras, ventas o requisiciones.','Administración','#e8f1ec','#5b9275']};
$('jmWelcome').textContent='Hola, '+currentUser.name+'.';
for(const [route,[title,description,category,fill,ink]] of Object.entries(jmCardDescriptions)){if(!jmAllowed[route])continue;const card=document.createElement('button');card.className='jm-app-card';card.type='button';card.style.setProperty('--card-fill',fill);card.style.setProperty('--card-ink',ink);const icon=document.createElement('span');icon.className='jm-card-icon';icon.append(jmIcon(jmIcons[route]));const h=document.createElement('strong'),p=document.createElement('small'),tag=document.createElement('span');h.textContent=title;p.textContent=description;if(route==='autorizaciones'&&!rwCanManage){h.textContent='Mis autorizaciones';p.textContent='Consulta el estado de tus propuestas de cambio.';}if(route==='requisiciones'&&!rqCanWrite)p.textContent='Consulta las solicitudes de tus sucursales autorizadas.';if(route==='compras'&&!canEdit||route==='ventas'&&!salesWrite)p.textContent='Consulta el catálogo y descarga el maestro actualizado.';tag.textContent=category;tag.className='jm-card-category';card.append(icon,jmIcon('arrow'),h,p,tag);card.onclick=()=>jmNavigate(route);$('jmHomeCards').append(card);}
$('jmAccessCount').textContent=Object.values(jmAllowed).filter(Boolean).length-1+' accesos disponibles';
const jmQuick=[];if(rqCanWrite&&jmAllowed.requisiciones)jmQuick.push(['Nueva requisición','requisiciones','nueva','plus']);if(canEdit)jmQuick.push(['Crear SKU de compra','compras','nuevo','plus']);if(!jmQuick.length&&jmAllowed.reportes)jmQuick.push(['Consultar reportes','reportes',null,'chart']);if(!jmQuick.length&&jmAllowed.ventas)jmQuick.push(['Abrir ventas','ventas',null,'sell']);
for(const [label,route,sub,icon] of jmQuick.slice(0,2)){const button=document.createElement('button');button.type='button';button.append(jmIcon(icon),document.createTextNode(label));button.onclick=()=>jmNavigate(route,sub);$('jmHeroActions').append(button);}
function jmMetric(id,label,icon,value){const div=document.createElement('div');div.className='jm-metric';const badge=document.createElement('span');badge.className='jm-metric-icon';badge.append(jmIcon(icon));const text=document.createElement('div'),strong=document.createElement('strong'),small=document.createElement('small');strong.id=id;strong.textContent=value;small.textContent=label;text.append(strong,small);div.append(badge,text);$('jmMetrics').append(div);}
jmMetric('jmMetricModules','Módulos habilitados','box',currentUser.modulos.length);jmMetric('jmMetricProducts',canReadPurchases?'Artículos de compra':'Perfil de acceso','list',canReadPurchases?state.registros.filter(r=>!r.eliminado).length:roleNames[currentUser.role].toLowerCase());jmMetric('jmMetricRequests','Solicitudes visibles','chart',jmAllowed.requisiciones?'…':'—');jmMetric('jmMetricBranches','Sucursales autorizadas','branch',jmAllowed.requisiciones?'…':'—');
if(!currentUser.modulos.length)$('jmHomeStatus').textContent='No tienes módulos asignados. Solicita acceso al superadministrador.';
if(jmAllowed.requisiciones)void rqJSON('/meta').then(meta=>{$('jmMetricRequests').textContent=meta.totalSolicitudes;$('jmMetricBranches').textContent=meta.sucursales.length;}).catch(()=>{$('jmMetricRequests').textContent=$('jmMetricBranches').textContent='—';$('jmHomeStatus').textContent='No se pudieron actualizar los indicadores. Abre Requisiciones para reintentar.';});
// Corrección de textos de ayuda para reflejar el flujo de autorización vigente.
const jmOldLocations=renderUserLocations;renderUserLocations=function(values){jmOldLocations(values);if($('usuarioRol').value==='gerente')$('usuarioAccesosNota').textContent='Tiene acceso a las sucursales configuradas. Puede crear requisiciones, cargar maestros, modificar series y folios, editar reportes y autorizar cambios.';if($('usuarioRol').value==='almacenista')$('usuarioAccesosNota').textContent='Selecciona sus almacenes. Puede consultar sus requisiciones y proponer modificaciones o cancelaciones para aprobación.';};
window.addEventListener('hashchange',()=>void jmRenderRoute());await jmRenderRoute();document.documentElement.setAttribute('data-erp-ready','true');


