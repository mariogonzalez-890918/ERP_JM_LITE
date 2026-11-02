// Regresión del controlador real: viewport CSS, altura variable, reapertura y escritorio.
import assert from 'node:assert/strict';import fs from 'node:fs/promises';import vm from 'node:vm';
const source=await fs.readFile('sku/erp-ui.js','utf8'),begin=source.indexOf('const jmMobileNav='),end=source.indexOf('function jmNavigate',begin);assert(begin>=0&&end>begin);
const classes=new Set(),listeners={},mediaListeners={},elements={};let focusCount=0;
const media={matches:true,addEventListener:(name,fn)=>mediaListeners[name]=fn};
for(const id of ['jmShade','jmSidebar','jmMenuToggle','jmMenuClose'])elements[id]={hidden:false,inert:false,attributes:{},setAttribute(name,value){this.attributes[name]=value;},focus(){focusCount++;}};
const document={body:{classList:{contains:name=>classes.has(name),remove:name=>classes.delete(name),toggle(name,value=!classes.has(name)){if(value)classes.add(name);else classes.delete(name);return value;}}},addEventListener:(name,fn)=>listeners[name]=fn};
const window={innerWidth:1400,innerHeight:844,matchMedia:query=>{assert.equal(query,'(max-width: 1024px)');return media;},addEventListener:(name,fn)=>listeners[name]=fn};
vm.runInNewContext(source.slice(begin,end),{window,document,$:id=>elements[id]});
function opened(value){assert.equal(classes.has('jm-menu-open'),value);assert.equal(elements.jmSidebar.inert,!value);assert.equal(elements.jmShade.hidden,!value);assert.equal(elements.jmMenuToggle.attributes['aria-expanded'],String(value));}
opened(false);elements.jmMenuToggle.onclick();opened(true);
// innerWidth puede incluir desbordamiento; debe prevalecer la media query de CSS.
assert.equal(window.innerWidth,1400);window.innerHeight=700;listeners.resize?.();opened(true);
elements.jmMenuClose.onclick();opened(false);assert.equal(focusCount,1);elements.jmMenuToggle.onclick();opened(true);elements.jmShade.onclick();opened(false);elements.jmMenuToggle.onclick();listeners.keydown({key:'Escape'});opened(false);
elements.jmMenuToggle.onclick();media.matches=false;mediaListeners.change();assert.equal(elements.jmSidebar.inert,false);assert.equal(elements.jmMenuClose.hidden,true);assert.equal(elements.jmMenuToggle.attributes['aria-expanded'],'true');elements.jmMenuToggle.onclick();assert(classes.has('jm-compact'));
media.matches=true;mediaListeners.change();opened(false);assert(!classes.has('jm-compact'));elements.jmMenuToggle.onclick();opened(true);
console.log('PASS: menú celular/tablet usa viewport CSS, no se cierra con altura variable, reabre y conserva navegación de escritorio.');
