// SKU: producto(2) + categoría(2) + subcategoría(2) + consecutivo(7) + verificador Luhn base36(1).
const CAT={};
const SUB={};
const TIP={};
const ALIASES={'FIGURAS':'FIGURA','COBERTURA':'COBERTURA Y CONFITERIA','CONFITERIA Y COBERTURAS':'COBERTURA Y CONFITERIA','EQUIPO DE PROTECCION BASICO':'EQUIPO DE PROTECCION','ARTCULOS DE LIMPIEZA':'ARTICULOS DE LIMPIEZA','INSUMOS':'INSUMO'};
const norm=s=>String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().replace(/\s+/g,' ').toUpperCase();
function resolve(v,cat){let n=norm(v);n=ALIASES[n]||n;return Object.keys(cat).find(k=>k===n||k===n.padStart(2,'0')||norm(cat[k])===n)||'';}
const alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';
function checkDigit(body){let sum=0,factor=2;for(let i=body.length-1;i>=0;i--){const v=alphabet.indexOf(body[i]);if(v<0)throw Error('Caracter inválido para el verificador.');const x=v*factor;sum+=Math.floor(x/36)+x%36;factor=factor===2?1:2;}return alphabet[(36-sum%36)%36];}
function makeSKU(r){if(!r.tipo||!r.categoria||!r.subcategoria)return '';if(!Number.isSafeInteger(r.id)||r.id<1||r.id>9999999)throw Error('Consecutivo fuera de rango.');const body=r.tipo+r.categoria+r.subcategoria+String(r.id).padStart(7,'0');return body+checkDigit(body);}
function verifySKU(s){return /^[A-Z0-9]{6}\d{7}[0-9A-Z]$/.test(s)&&checkDigit(s.slice(0,-1))===s.slice(-1)&&Object.hasOwn(TIP,s.slice(0,2))&&Object.hasOwn(CAT,s.slice(2,4))&&Object.hasOwn(SUB,s.slice(4,6))&&Number(s.slice(6,13))>0;}
const identity=r=>[r.tipo,r.categoria,r.subcategoria,norm(r.nombre),norm(r.proveedor),norm(r.claveProveedor),norm(r.unidadCompra),norm(r.unidadEntrega)].join('|');
function validateState(s){
 if(!s||s.version!==3||!Array.isArray(s.registros)||!Array.isArray(s.reservados)||!Number.isSafeInteger(s.maxId)||s.maxId<0||s.maxId>9999999)throw Error('Respaldo incompatible o consecutivo inválido.');
 const ids=new Set(),skus=new Set(),filas=new Set();
 for(const r of s.registros){
  if(!Number.isSafeInteger(r.id)||r.id<1||r.id>s.maxId||ids.has(r.id)||typeof r.nombre!=='string'||!r.nombre.trim()||r.nombre.length>300||typeof r.eliminado!=='boolean'||typeof r.estado!=='string')throw Error('Registro inválido o ID repetido.');ids.add(r.id);
  for(const [campo,cat] of [['tipo',TIP],['categoria',CAT],['subcategoria',SUB]])if(r[campo]!==''&&!Object.hasOwn(cat,r[campo]))throw Error('Clasificación desconocida.');
  if(r.sku!==makeSKU(r)||r.sku&&(!verifySKU(r.sku)||skus.has(r.sku)||!r.eliminado&&s.reservados.includes(r.sku)))throw Error('SKU duplicado, reservado o verificador incorrecto.');if(r.sku)skus.add(r.sku);
  if(r.fila!=null){if(!Number.isSafeInteger(r.fila)||r.fila<2||filas.has(r.fila))throw Error('Fila del maestro inválida o repetida.');filas.add(r.fila);}
 }
 if(s.reservados.some(x=>typeof x!=='string'||!x))throw Error('Reserva inválida.');return s;
}
function nextRecord(s,fields){if(s.maxId>=9999999)throw Error('Se agotaron los consecutivos.');const r={...fields,id:s.maxId+1,eliminado:false,editado:true,fila:null};r.sku=makeSKU(r);return r;}
function updateRecord(s,id,fields){
 const r=s.registros.find(x=>x.id===id);if(!r||r.eliminado)throw Error('Artículo no disponible.');const updated={...r,...fields,id:r.id,fila:r.fila,eliminado:false,editado:true};updated.sku=makeSKU(updated);
 if(identity(updated)!==identity(r)&&s.registros.some(x=>x.id!==id&&!x.eliminado&&identity(x)===identity(updated)))throw Error('Ya existe ese artículo con la misma clasificación y proveedor.');
 if(updated.sku!==r.sku&&s.reservados.includes(updated.sku))throw Error('Ese SKU ya fue utilizado. No puede volver a asignarse.');
 const reservados=[...s.reservados];if(r.sku&&r.sku!==updated.sku)reservados.push(r.sku);
 return validateState({...s,reservados:[...new Set(reservados)],registros:s.registros.map(x=>x.id===id?updated:x)});
}
function deleteRecord(s,id){const r=s.registros.find(x=>x.id===id);if(!r||r.eliminado)throw Error('Artículo no disponible.');return validateState({...s,reservados:[...new Set([...s.reservados,...(r.sku?[r.sku]:[])])],registros:s.registros.map(x=>x.id===id?{...x,eliminado:true}:x)});}
function parseCSV(text){text=text.replace(/^\uFEFF/,'');const first=text.split(/\r?\n/)[0];const count=sep=>{let n=0,q=false;for(let i=0;i<first.length;i++){if(first[i]==='"'){if(q&&first[i+1]==='"')i++;else q=!q;}else if(!q&&first[i]===sep)n++;}return n;};const sep=['\t',';',','].sort((a,b)=>count(b)-count(a))[0];const rows=[];let row=[],field='',quoted=false;for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){field+='"';i++;}else quoted=!quoted;}else if(!quoted&&c===sep){row.push(field);field='';}else if(!quoted&&(c==='\n'||c==='\r')){if(c==='\r'&&text[i+1]==='\n')i++;row.push(field);rows.push(row);row=[];field='';}else field+=c;}if(quoted)throw Error('Comillas sin cerrar.');row.push(field);rows.push(row);return rows.filter(r=>r.some(x=>x.trim()));}
