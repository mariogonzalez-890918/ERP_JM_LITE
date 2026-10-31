"""Sucursales comerciales persistentes; sin nombres de la empresa de origen."""
import re
DEFAULT_BRANCHES={'CENTRAL':'REQ-CEN','NORTE':'REQ-NOR','SUR':'REQ-SUR','ORIENTE':'REQ-ORI'}
BRANCHES=dict(DEFAULT_BRANCHES)

def load_branches(store):
 with store.connect() as db:
  db.execute('CREATE TABLE IF NOT EXISTS app_branches(name TEXT PRIMARY KEY,series TEXT UNIQUE NOT NULL,revision INTEGER NOT NULL)')
  if not db.execute('SELECT 1 FROM app_branches').fetchone():
   # Preservar sucursales de instalaciones que ya tienen documentos propios.
   tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   used=any(db.execute('SELECT 1 FROM '+table+' LIMIT 1').fetchone() for table in ('req_documents','cm_documents','po_orders') if table in tables)
   old=db.execute('SELECT branch,series FROM req_branches').fetchall() if used and 'req_branches' in tables else []
   db.executemany('INSERT INTO app_branches VALUES(?,?,1)',old or list(DEFAULT_BRANCHES.items()))
   if not used:
    for table in ('req_branches','req_series_registry'):
     if table in tables:db.execute('DELETE FROM '+table)
  values=dict(db.execute('SELECT name,series FROM app_branches ORDER BY name'))
 BRANCHES.clear();BRANCHES.update(values)

def save_branch(store,data,actor):
 from requisiciones import Conflict
 if actor['role']!='superadmin':raise PermissionError('Solo Superadministrador configura sucursales.')
 name=' '.join(str(data.get('nombre','')).upper().split());series=str(data.get('serie','')).upper().strip()
 if not 1<=len(name)<=80 or not re.fullmatch('[A-Z0-9][A-Z0-9-]{1,19}',series):raise ValueError('Indica nombre y una serie de 2–20 caracteres, sin espacios.')
 with store.connect() as db:
  db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT revision FROM app_branches WHERE name=?',(name,)).fetchone()
  if data.get('revision',0)!=(row[0] if row else 0):raise Conflict('La sucursal cambió. Actualiza la lista.')
  if row:raise ValueError('Las sucursales existentes conservan su nombre y serie. Los folios se configuran en Requisiciones.')
  if db.execute('SELECT 1 FROM app_branches WHERE series=?',(series,)).fetchone():raise ValueError('La serie ya pertenece a una sucursal.')
  db.execute('INSERT INTO app_branches VALUES(?,?,1)',(name,series))
  db.execute('INSERT INTO req_branches VALUES(?,?,1,1)',(name,series));db.execute('INSERT INTO req_series_registry VALUES(?,?)',(series,name))
 load_branches(store)
 return {'ok':True}
