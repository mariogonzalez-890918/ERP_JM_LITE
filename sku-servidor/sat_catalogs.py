"""Consulta local de las claves oficiales, sin permitir edición desde la aplicación."""
import datetime,functools,gzip,json,pathlib,unicodedata

def normalized(value):return ''.join(c for c in unicodedata.normalize('NFD',str(value).upper()) if not unicodedata.combining(c))
@functools.lru_cache(maxsize=1)
def catalogs():
 path=pathlib.Path(__file__).resolve().parent/'sat-catalogos.json.gz'
 with gzip.open(path,'rt',encoding='utf8') as f:value=json.load(f)
 for kind in ('productos','unidades'):
  value[kind+'_index']={r['clave']:r for r in value[kind]}
  value[kind+'_search']=[(r,normalized(r['clave']+' '+r['nombre']+' '+r.get('descripcion','')+' '+r.get('simbolo',''))) for r in value[kind]]
 return value
def active(row):
 today=datetime.date.today().isoformat();return (not row['inicio'] or row['inicio']<=today) and (not row['fin'] or today<=row['fin'])
def validate(kind,key):
 if not key:return ''
 if kind not in ('productos','unidades'):raise ValueError('Catálogo SAT inválido.')
 row=catalogs()[kind+'_index'].get(key)
 if not row or not active(row):raise ValueError('Selecciona una clave SAT vigente del catálogo de '+kind+'.')
 return key
def search(query):
 kind=query.get('tipo','productos');q=str(query.get('q','')).strip()[:120]
 if kind not in ('productos','unidades'):raise ValueError('Selecciona productos o unidades SAT.')
 data=catalogs();tokens=normalized(q).split();result=[];total=0
 for row,label in data[kind+'_search']:
  if active(row) and all(t in label for t in tokens):
   total+=1
   if len(result)<50:result.append(row)
 exact=data[kind+'_index'].get(q.upper())
 if exact and active(exact):result=[exact]+[r for r in result if r['clave']!=exact['clave']];result=result[:50]
 return {'resultados':result,'coincidencias':total,'totalCatalogo':len(data[kind]),'version':data['version'],'fuente':data['fuente'],'sha256Original':data['sha256Original']}
