"""Impuestos configurables y vínculos por empresa, ámbito y SKU."""
import json,secrets
from decimal import Decimal,InvalidOperation
from requisiciones import Conflict,text

def initialize(db):
 db.executescript('''CREATE TABLE IF NOT EXISTS app_taxes(id TEXT PRIMARY KEY,company INTEGER NOT NULL,name TEXT NOT NULL,rate TEXT NOT NULL,active INTEGER NOT NULL,revision INTEGER NOT NULL);
 CREATE TABLE IF NOT EXISTS app_product_taxes(company INTEGER NOT NULL,scope TEXT NOT NULL,sku TEXT NOT NULL,tax TEXT NOT NULL,revision INTEGER NOT NULL,PRIMARY KEY(company,scope,sku));''')

def configured(db,company,scope,sku,strict=True):
 row=db.execute('SELECT t.id,t.name,t.rate,t.active FROM app_product_taxes p JOIN app_taxes t ON t.id=p.tax AND t.company=p.company WHERE p.company=? AND p.scope=? AND p.sku=?',(company,scope,sku)).fetchone()
 if not row:return None
 if strict and not row[3]:raise ValueError('El impuesto de '+sku+' está inactivo. Configura otro impuesto antes de operar.')
 return {'impuestoId':row[0],'nombreImpuesto':row[1],'iva':row[2]}

def selected(db,company,id):
 row=db.execute('SELECT name,rate FROM app_taxes WHERE id=? AND company=? AND active=1',(id,company)).fetchone()
 if not row:raise ValueError('Selecciona un impuesto activo de esta empresa.')
 return row

def listed(db,company):return [{'id':i,'nombre':n,'tasa':r,'activo':bool(a),'revision':v} for i,n,r,a,v in db.execute('SELECT id,name,rate,active,revision FROM app_taxes WHERE company=? ORDER BY name',(company,))]

def save(db,data):
 name=text(data.get('nombre',''),100)
 try:rate=Decimal(str(data.get('tasa')))
 except (InvalidOperation,TypeError):raise ValueError('Tasa inválida.')
 if not name or not rate.is_finite() or not 0<=rate<=100 or rate.as_tuple().exponent < -4 or type(data.get('activo',True)) is not bool:raise ValueError('Indica nombre y tasa de 0 a 100 con hasta cuatro decimales.')
 company=data['empresa'];id=data.get('id') or secrets.token_hex(16);row=db.execute('SELECT company,revision FROM app_taxes WHERE id=?',(id,)).fetchone()
 if row and row[0]!=company:raise PermissionError('Impuesto de otra empresa.')
 if data.get('revision',0)!=(row[1] if row else 0):raise Conflict('El impuesto cambió. Actualiza la configuración.')
 db.execute('INSERT INTO app_taxes VALUES(?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET name=excluded.name,rate=excluded.rate,active=excluded.active,revision=app_taxes.revision+1',(id,company,name,format(rate,'f'),int(data.get('activo',True))))
 return {'ok':True,'id':id}

def link(db,data):
 company=data['empresa'];scope=data.get('ambito');sku=text(data.get('sku',''),80)
 if scope not in ('compras','ventas'):raise ValueError('Selecciona compras o ventas.')
 selected(db,company,data.get('impuesto'))
 rows=db.execute('SELECT payload FROM req_materials') if scope=='compras' else db.execute('SELECT payload FROM cm_products WHERE sku=?',(sku,))
 if not any(json.loads(row[0]).get('sku',sku if scope=='ventas' else '')==sku for row in rows):raise ValueError('Selecciona un SKU existente en este ámbito.')
 old=db.execute('SELECT revision FROM app_product_taxes WHERE company=? AND scope=? AND sku=?',(company,scope,sku)).fetchone()
 if data.get('revision',0)!=(old[0] if old else 0):raise Conflict('El vínculo cambió. Actualiza la configuración.')
 db.execute('INSERT INTO app_product_taxes VALUES(?,?,?,?,1) ON CONFLICT(company,scope,sku) DO UPDATE SET tax=excluded.tax,revision=app_product_taxes.revision+1',(company,scope,sku,data['impuesto']))
 return {'ok':True}
