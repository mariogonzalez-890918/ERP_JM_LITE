"""Clasificación SKU configurable; instalaciones nuevas sin clasificaciones precargadas."""
import json,re
from requisiciones import Conflict,text

class Taxonomy:
 def __init__(self,store):
  self.store=store
  with store.connect() as db:
   db.execute('CREATE TABLE IF NOT EXISTS sku_taxonomy(scope TEXT NOT NULL,kind TEXT NOT NULL,code TEXT NOT NULL,label TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(scope,kind,code))')
   tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   # Importar únicamente códigos ya utilizados en datos históricos de esta instalación.
   for scope,table in [('compras','catalog'),('ventas','sales_catalog')]:
    if table not in tables:continue
    row=db.execute('SELECT payload FROM '+table+' WHERE id=1').fetchone()
    if not row:continue
    for item in json.loads(row[0])['state']['registros']:
     for kind,field,column in [('TIP','tipo','E' if scope=='compras' else 'B'),('CAT','categoria','F' if scope=='compras' else 'C'),('SUB','subcategoria','G' if scope=='compras' else 'D'),*([('PDV','modulo','F')] if scope=='ventas' else [])]:
      code=item.get(field)
      if code and code not in ('00','000'):db.execute('INSERT OR IGNORE INTO sku_taxonomy VALUES(?,?,?,?,1)',(scope,kind,code,item.get('camposExcel',{}).get(column) or code))
  self.reload()
 def reload(self):
  import ventas
  with self.store.connect() as db:rows=db.execute('SELECT scope,kind,code,label FROM sku_taxonomy').fetchall()
  for group in self.store.catalogs.values():group.clear()
  for group in (ventas.TIP,ventas.CAT,ventas.SUB,ventas.PDV):group.clear()
  for scope,kind,code,label in rows:
   if scope=='compras':self.store.catalogs[kind][code]=label
   else:getattr(ventas,kind)[code]=label
 def get(self,actor):
  with self.store.connect() as db:rows=db.execute('SELECT scope,kind,code,label,revision FROM sku_taxonomy ORDER BY scope,kind,code').fetchall()
  return {'clasificaciones':[{'ambito':s,'grupo':k,'codigo':c,'nombre':l,'revision':r} for s,k,c,l,r in rows],'puedeConfigurar':actor['role']=='superadmin'}
 def save(self,data,actor):
  if actor['role']!='superadmin':raise PermissionError('Solo Superadministrador configura clasificaciones SKU.')
  scope=data.get('ambito');kind=data.get('grupo');code=text(data.get('codigo',''),3).upper();label=text(data.get('nombre',''),160);remove=data.get('eliminar') is True
  if scope not in ('compras','ventas') or kind not in (('TIP','CAT','SUB') if scope=='compras' else ('TIP','CAT','SUB','PDV')) or not re.fullmatch('[A-Z0-9]{'+('3' if kind=='PDV' else '2')+'}',code) or code in ('00','000') or not label:raise ValueError('Indica ámbito, grupo, código de 2 caracteres (3 para PDV) y nombre; 00 y 000 son reservados.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT revision FROM sku_taxonomy WHERE scope=? AND kind=? AND code=?',(scope,kind,code)).fetchone()
   if data.get('revision',0)!=(old[0] if old else 0):raise Conflict('La clasificación cambió. Actualiza antes de guardar.')
   if remove:
    table='catalog' if scope=='compras' else 'sales_catalog';row=db.execute('SELECT payload FROM '+table+' WHERE id=1').fetchone();field={'TIP':'tipo','CAT':'categoria','SUB':'subcategoria','PDV':'modulo'}[kind]
    if row and any(r.get(field)==code for r in json.loads(row[0])['state']['registros']):raise ValueError('Este código ya forma parte del historial SKU. Puedes editar su nombre, pero no eliminarlo.')
    db.execute('DELETE FROM sku_taxonomy WHERE scope=? AND kind=? AND code=?',(scope,kind,code))
   else:db.execute('INSERT INTO sku_taxonomy VALUES(?,?,?,?,?) ON CONFLICT(scope,kind,code) DO UPDATE SET label=excluded.label,revision=excluded.revision',(scope,kind,code,label,(old[0] if old else 0)+1))
  self.reload();return {'ok':True}
 def catalogs(self):
  import ventas
  return {'compras':self.store.catalogs,'ventas':{key:getattr(ventas,key) for key in ('TIP','CAT','SUB','PDV')}}
