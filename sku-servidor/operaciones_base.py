"""Reservas lógicas compartidas: no cambian cantidades ni valores del Kárdex."""
import json
from decimal import Decimal
from comercial import dumps,fingerprint
from requisiciones import Conflict,now

SCHEMA={
 'op_reservations': 'CREATE TABLE op_reservations(document TEXT NOT NULL,warehouse TEXT NOT NULL,sku TEXT NOT NULL,qty TEXT NOT NULL,PRIMARY KEY(document,warehouse,sku))',
 'pr_recipes': 'CREATE TABLE pr_recipes(id TEXT PRIMARY KEY,company INTEGER NOT NULL,code TEXT NOT NULL,version INTEGER NOT NULL,payload TEXT NOT NULL,UNIQUE(company,code,version))',
 'pr_orders': 'CREATE TABLE pr_orders(id TEXT PRIMARY KEY,company INTEGER NOT NULL,branch TEXT NOT NULL,state TEXT NOT NULL,revision INTEGER NOT NULL,payload TEXT NOT NULL)',
 'pr_events': 'CREATE TABLE pr_events(id TEXT PRIMARY KEY,document TEXT NOT NULL,company INTEGER NOT NULL,kind TEXT NOT NULL,client_key TEXT NOT NULL UNIQUE,request_hash TEXT NOT NULL,actor TEXT NOT NULL,created TEXT NOT NULL,payload TEXT NOT NULL)',
 'pr_events_no_update': "CREATE TRIGGER pr_events_no_update BEFORE UPDATE ON pr_events BEGIN SELECT RAISE(ABORT,'El historial de producción es inmutable'); END",
 'pr_events_no_delete': "CREATE TRIGGER pr_events_no_delete BEFORE DELETE ON pr_events BEGIN SELECT RAISE(ABORT,'El historial de producción es inmutable'); END"
}
def initialize(db,production=False):
 names=SCHEMA if production else ('op_reservations',)
 for name in names:
  if not db.execute('SELECT 1 FROM sqlite_master WHERE name=?',(name,)).fetchone():db.execute(SCHEMA[name])
def reserved(db,w,sku,exclude=''):
 return sum((Decimal(q) for document,q in db.execute('SELECT document,qty FROM op_reservations WHERE warehouse=? AND sku=?',(w,sku)) if document!=exclude),Decimal(0))
def reserve(db,document,w,sku,quantity):
 from inventarios import fmt
 if quantity<=0:db.execute('DELETE FROM op_reservations WHERE document=? AND warehouse=? AND sku=?',(document,w,sku))
 else:db.execute('INSERT INTO op_reservations VALUES(?,?,?,?) ON CONFLICT(document,warehouse,sku) DO UPDATE SET qty=excluded.qty',(document,w,sku,fmt(quantity)))
def consume_reserve(db,document,w,sku,quantity):
 row=db.execute('SELECT qty FROM op_reservations WHERE document=? AND warehouse=? AND sku=?',(document,w,sku)).fetchone()
 reserve(db,document,w,sku,max(Decimal(0),Decimal(row[0])-quantity) if row else Decimal(0))
def setting(db,key,default):
 row=db.execute('SELECT value FROM app_meta WHERE key=?',(key,)).fetchone();return json.loads(row[0]) if row else default

def save_setting(db,key,data,revision):
 old=setting(db,key,{'revision':0})
 if type(revision) is not int or old['revision']!=revision:raise Conflict('La configuración cambió. Actualiza antes de guardar.')
 value={**data,'revision':revision+1};db.execute('INSERT INTO app_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,dumps(value)));return value

def series(cm,db,company,kind,data=None):
 old=cm.sequence(db,company,kind)
 if data is None:return old
 import re
 prefix=str(data.get('serie','')).strip().upper();following=data.get('siguiente');width=data.get('ancho',6)
 if not re.fullmatch('[A-Z0-9][A-Z0-9-]{1,34}',prefix) or type(following) is not int or not 1<=following<=999999999 or type(width) is not int or not 1<=width<=12:raise ValueError('Configura una serie, consecutivo y ancho válidos.')
 if old['revision']!=data.get('revision'):raise Conflict('Cambió la serie o se emitió otro documento.')
 owner=db.execute('SELECT kind FROM cm_sequence_registry WHERE company=? AND series=?',(company,prefix)).fetchone()
 if owner and owner[0]!=kind:raise ValueError('La serie pertenece a otro documento o sucursal.')
 # Nunca retroceder una serie ya utilizada, incluso después de cambiar de prefijo.
 if prefix==old['serie'] and following<old['siguiente']:raise ValueError('No se pueden retroceder folios.')
 if prefix!=old['serie'] and owner:raise ValueError('Esta serie ya fue utilizada; elige una nueva.')
 db.execute('INSERT OR IGNORE INTO cm_sequence_registry VALUES(?,?,?)',(company,prefix,kind));db.execute('UPDATE cm_sequences SET series=?,next=?,width=?,revision=revision+1 WHERE company=? AND kind=?',(prefix,following,width,company,kind))
 return cm.sequence(db,company,kind)
