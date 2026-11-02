"""Almacenes nombrados por sucursal; conserva los destinos históricos."""
import json,uuid
from decimal import Decimal
from comercial import dumps
from requisiciones import Conflict,now,text

FUNCTIONS={'GENERAL':'General','MATERIA_PRIMA':'Materias primas','PRODUCCION':'Producción','PT':'Producto terminado','CUARENTENA':'Cuarentena','MERMA':'Merma','DEVOLUCIONES':'Devoluciones'}
LEGACY_SCHEMA='CREATE TABLE inv_warehouses(id TEXT PRIMARY KEY,company INTEGER NOT NULL,branch TEXT NOT NULL,cycle INTEGER NOT NULL DEFAULT 1,active INTEGER NOT NULL DEFAULT 0,revision INTEGER NOT NULL DEFAULT 1,UNIQUE(company,branch))'

def migrate(db):
 # La restricción anterior se retira en una sola transacción. Las referencias
 # usan IDs de texto; no se cambian claves, ciclos, saldos ni diarios.
 if not any(unique and origin=='u' for _,_,unique,origin,*_ in db.execute('PRAGMA index_list(inv_warehouses)')):return
 db.execute('BEGIN IMMEDIATE')
 db.execute('CREATE TABLE inv_warehouses_multi(id TEXT PRIMARY KEY,company INTEGER NOT NULL,branch TEXT NOT NULL,cycle INTEGER NOT NULL DEFAULT 1,active INTEGER NOT NULL DEFAULT 0,revision INTEGER NOT NULL DEFAULT 1)')
 db.execute('INSERT INTO inv_warehouses_multi SELECT id,company,branch,cycle,active,revision FROM inv_warehouses')
 db.execute('DROP TABLE inv_warehouses')
 db.execute('ALTER TABLE inv_warehouses_multi RENAME TO inv_warehouses')
 db.commit()

def details(db,id,branch):
 row=db.execute('SELECT value FROM app_meta WHERE key=?',('warehouse:'+id,)).fetchone()
 return json.loads(row[0]) if row else {'nombre':branch,'funcion':'GENERAL'}

class WarehouseConfiguration:
 def __init__(self,inv):self.inv=inv;self.store=inv.store
 def save(self,data,actor):
  self.inv.scope(actor)
  if actor['role'] not in ('superadmin','gerente'):raise PermissionError('Solo Gerencia y Superadministrador configuran almacenes.')
  name=text(data.get('nombre',''),120);function=data.get('funcion','GENERAL');id=data.get('id')
  if id is not None and (not isinstance(id,str) or not 1<=len(id)<=250):raise ValueError('Identificador de almacén inválido.')
  if not name or not isinstance(function,str) or function not in FUNCTIONS:raise ValueError('Indica un nombre y una función de almacén válidos.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');self.inv.sync(db)
   if id:
    w=self.inv.scope(actor,id,db,True)
    if data.get('revision')!=w['revision']:raise Conflict('El almacén cambió. Actualiza antes de guardar.')
    company=w['empresa'];branch=w['sucursal'];prior=details(db,id,branch)
    if function!=prior['funcion'] and any(Decimal(q)!=0 for q, in db.execute('SELECT qty FROM inv_balances WHERE warehouse=?',(id,))):raise ValueError('No cambies la función de un almacén con existencias; realiza primero los traspasos autorizados.')
   else:
    company=data.get('empresa');branch=data.get('sucursal')
    if type(company) is not int:raise ValueError('Selecciona una razón social.')
    if not isinstance(branch,str):raise ValueError('Selecciona una sucursal configurada.')
    self.inv.scope(actor,str(company)+':'+branch,db,True)
    id=uuid.uuid4().hex
   for other, in db.execute('SELECT id FROM inv_warehouses WHERE company=? AND branch=?',(company,branch)):
    if other!=id and details(db,other,branch)['nombre'].casefold()==name.casefold():raise ValueError('Ya existe un almacén con ese nombre en la sucursal.')
   if not data.get('id'):db.execute('INSERT INTO inv_warehouses(id,company,branch) VALUES(?,?,?)',(id,company,branch))
   else:db.execute('UPDATE inv_warehouses SET revision=revision+1 WHERE id=?',(id,))
   value={'nombre':name,'funcion':function}
   db.execute('INSERT INTO app_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('warehouse:'+id,dumps(value)))
   db.execute('INSERT INTO app_audit(actor,action,created,payload) VALUES(?,?,?,?)',(actor['email'],'almacen_configurado',now(),dumps({'id':id,'empresa':company,'sucursal':branch,**value})))
   return {'ok':True,'almacen':self.inv.scope(actor,id,db)}
 def release(self,data,actor):
  from inventarios import dec,fmt
  self.inv.scope(actor)
  if actor['role'] not in ('gerente','superadmin'):raise PermissionError('Solo Gerencia y Superadministrador autorizan liberaciones de cuarentena.')
  if any(not isinstance(data.get(k),str) or not 1<=len(data[k])<=250 for k in ('origen','destino')):raise ValueError('Selecciona los almacenes de origen y destino.')
  reason=text(data.get('motivo',''),2000);responsible=text(data.get('responsable',''),160);quantity=dec(data.get('cantidad'),True);sku=str(data.get('sku','')).strip().upper()
  if not reason or not responsible:raise ValueError('Indica responsable de Calidad y motivo de la liberación.')
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');source=self.inv.scope(actor,data.get('origen'),db,True);target=self.inv.scope(actor,data.get('destino'),db,True)
   repeat=self.inv.repeat(db,data)
   if repeat:return repeat
   if not source['activo'] or not target['activo']:raise ValueError('Autoriza primero el inventario inicial de ambos almacenes.')
   if source['empresa']!=target['empresa'] or source['funcion']!='CUARENTENA' or target['funcion'] not in ('GENERAL','PT'):raise ValueError('Libera desde Cuarentena a General o PT de la misma razón social.')
   balance=self.inv.balance(db,source['id'],sku)
   if not balance:raise ValueError('El SKU no tiene existencias en cuarentena.')
   material={'sku':sku,'nombre':balance['nombre'],'unidad':balance['unidad'],'materialId':balance.get('materialId')};cost=Decimal(balance['costo']);key=data['clave'];extra={'responsableCalidad':responsible,'origen':source['id'],'destino':target['id']}
   outgoing=self.inv.post(db,source['id'],material,-quantity,cost,'calidad-salida:'+key,'CALIDAD_LIBERACION',actor,'CAL-'+key[:10].upper(),reason,extra)
   incoming=self.inv.post(db,target['id'],material,quantity,Decimal(outgoing['costoUnitario']),'calidad-entrada:'+key,'CALIDAD_LIBERACION',actor,'CAL-'+key[:10].upper(),reason,extra)
   db.execute('INSERT INTO app_audit(actor,action,created,payload) VALUES(?,?,?,?)',(actor['email'],'cuarentena_liberada',now(),dumps({'sku':sku,'cantidad':fmt(quantity),**extra})))
   return self.inv.remember(db,data,{'ok':True,'movimientos':[outgoing,incoming]})
