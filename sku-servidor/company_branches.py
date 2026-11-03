"""Alta de sucursales dentro de una razón social y principal explícita."""
import json
from requisiciones import BRANCHES,Conflict
from sucursales import save_branch,load_branches

def save_company(cm,data,actor):
 if actor['role']!='superadmin':raise PermissionError('Solo Superadministrador configura razones sociales y sucursales.')
 id=data.get('id');branches=data.get('sucursales',[])
 with cm.store.atomic() as db:
  previous=cm.company(id,actor,db=db) if id else None
  if branches and not id:raise ValueError('Guarda la razón social y agrega sus propias sucursales.')
  if previous and any(b not in previous['sucursales'] for b in branches):raise ValueError('Agrega las nuevas sucursales desde la razón social seleccionada.')
  if branches and data.get('sucursalPrincipal') not in branches:raise ValueError('Selecciona la sucursal principal de esta razón social.')
  return cm.save_company(data,actor,allow_empty=True)

def add_branch(cm,data,actor):
 if actor['role']!='superadmin':raise PermissionError('Solo Superadministrador configura sucursales por razón social.')
 with cm.store.atomic() as db:
  company=cm.company(data.get('empresa'),actor,db=db)
  if data.get('revision')!=company['revision']:raise Conflict('La razón social cambió. Actualiza sus sucursales.')
  name=' '.join(str(data.get('nombre','')).upper().split())
  if name in BRANCHES:raise ValueError('Ese nombre de sucursal ya está registrado. Usa un nombre que identifique esta ubicación sin confundirla con otra.')
  try:
   save_branch(cm.store,{'nombre':name,'serie':data.get('serie','')},actor)
   value={**company,'sucursales':company['sucursales']+[name]}
   value.pop('id',None)
   if data.get('principal') is True or not company.get('sucursalPrincipal'):value['sucursalPrincipal']=name
   result=cm.save_company({**value,'id':company['id']},actor,allow_empty=True)
  except Exception:
   # save_branch actualiza el catálogo en memoria; la transacción aún no se ha confirmado.
   BRANCHES.pop(name,None);raise
 load_branches(cm.store)
 return {**result,'sucursal':name}
