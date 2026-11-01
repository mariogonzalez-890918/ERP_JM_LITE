"""Unidades y líneas controladas; se conservan las etiquetas históricas."""
import secrets
from requisiciones import text,norm,Conflict
from sat_catalogs import validate

def initialize(db):db.execute('CREATE TABLE IF NOT EXISTS app_product_options(id TEXT PRIMARY KEY,kind TEXT NOT NULL,name TEXT NOT NULL,sat TEXT NOT NULL,active INTEGER NOT NULL,revision INTEGER NOT NULL)')
def listed(db):return [{'id':i,'tipo':k,'nombre':n,'claveSat':s,'activo':bool(a),'revision':r} for i,k,n,s,a,r in db.execute('SELECT id,kind,name,sat,active,revision FROM app_product_options ORDER BY kind,name')]
def save(store,data,actor):
 if actor['role']!='superadmin':raise PermissionError('Solo Superadministrador configura unidades y líneas.')
 kind=data.get('tipo');name=text(data.get('nombre',''),100);sat=str(data.get('claveSat','')).strip().upper();enabled=data.get('activo',True)
 if kind not in ('unidad','linea') or not name or type(enabled) is not bool:raise ValueError('Indica tipo, nombre y estado válidos.')
 if kind=='unidad':
  if not sat:raise ValueError('Selecciona la clave SAT de la unidad.')
  validate('unidades',sat)
 else:sat=''
 with store.atomic() as db:
  id=data.get('id') or secrets.token_hex(16);old=db.execute('SELECT kind,revision FROM app_product_options WHERE id=?',(id,)).fetchone()
  if old and old[0]!=kind:raise ValueError('No se cambia el tipo del registro.')
  if data.get('revision',0)!=(old[1] if old else 0):raise Conflict('El catálogo cambió. Actualiza antes de guardar.')
  if any(norm(n)==norm(name) and i!=id for i,n in db.execute('SELECT id,name FROM app_product_options WHERE kind=?',(kind,))):raise ValueError('Ya existe ese nombre en el catálogo.')
  db.execute('INSERT INTO app_product_options VALUES(?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET name=excluded.name,sat=excluded.sat,active=excluded.active,revision=app_product_options.revision+1',(id,kind,name,sat,int(enabled)))
 return {'ok':True,'id':id}
def resolve(db,kind,id,label,previous=''):
 if kind=='linea' and not id and not label:return ('','','')
 row=db.execute('SELECT id,name,sat,active FROM app_product_options WHERE kind=? AND '+('id=?' if id else 'name=?'),(kind,id or label)).fetchone()
 if row and row[3]:return row[:3]
 if not id and label and label==previous:return ('',label,'')
 raise ValueError('Selecciona '+('una unidad de venta' if kind=='unidad' else 'una línea')+' activa del catálogo configurado.')
