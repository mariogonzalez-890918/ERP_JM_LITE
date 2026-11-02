"""Lectores concurrentes; restauración exclusiva sin operaciones a medio aplicar."""
import contextlib,threading,time
from requisiciones import Conflict

class MaintenanceGate:
 def __init__(self):
  self.condition=threading.Condition(threading.RLock());self.local=threading.local();self.readers=0;self.waiting=0;self.writer=None
 @contextlib.contextmanager
 def shared(self):
  ident=threading.get_ident();nested=getattr(self.local,'depth',0)>0 or self.writer==ident
  with self.condition:
   if not nested:
    while self.writer is not None or self.waiting:self.condition.wait()
    self.readers+=1
   self.local.depth=getattr(self.local,'depth',0)+1
  try:yield
  finally:
   with self.condition:
    self.local.depth-=1
    if not nested:self.readers-=1;self.condition.notify_all()
 @contextlib.contextmanager
 def exclusive(self,timeout=30):
  if getattr(self.local,'depth',0):raise RuntimeError('No se puede restaurar dentro de una operación activa.')
  deadline=time.monotonic()+timeout
  with self.condition:
   self.waiting+=1
   try:
    while self.writer is not None or self.readers:
     left=deadline-time.monotonic()
     if left<=0:raise Conflict('Hay operaciones activas. Espera a que terminen y vuelve a confirmar la restauración.')
     self.condition.wait(left)
    self.writer=threading.get_ident()
   finally:self.waiting-=1;self.condition.notify_all()
  try:yield
  finally:
   with self.condition:self.writer=None;self.condition.notify_all()
