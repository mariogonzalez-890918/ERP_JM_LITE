"""Existencias físicas explícitas para pruebas de emisión TPV."""
from decimal import Decimal
import uuid

def seed_pos_stock(case,company,sku,quantity='100',warehouse=None):
 inv=case.http.RequestHandlerClass.inventory.inv
 with case.store.atomic() as db:
  inv.sync(db);w=warehouse or str(company)+':CENTRAL'
  db.execute('UPDATE inv_warehouses SET active=1 WHERE id=?',(w,))
  m=inv.materials()[sku];inv.post(db,w,m,Decimal(quantity),Decimal('20'),'test-pos-'+uuid.uuid4().hex,'INICIAL',{'email':'fixture@example.test','role':'superadmin'})
