"""Convierte exclusivamente los dos catálogos oficiales SAT a un recurso local."""
import argparse,gzip,hashlib,json,pathlib,re
import xlrd

def build(source,url,version,output):
 if not re.fullmatch(r'https?://(?:[a-z0-9-]+\.)*sat\.gob\.mx/[^\s]+',url):raise ValueError('Usa una fuente oficial SAT.')
 book=xlrd.open_workbook(str(source),on_demand=True);catalogs={}
 def code(value):return str(int(value)) if isinstance(value,float) and value.is_integer() else str(value).strip()
 def date(value):return xlrd.xldate_as_datetime(value,book.datemode).date().isoformat() if isinstance(value,(int,float)) and value>0 else ''
 for name,header,start,end in [('productos','c_ClaveProdServ',5,6),('unidades','c_ClaveUnidad',4,5)]:
  sheet=book.sheet_by_name(header);first=next(i for i in range(12) if sheet.cell_value(i,0)==header)+1;rows=[];seen=set()
  for i in range(first,sheet.nrows):
   values=sheet.row_values(i);key=code(values[0]);label=str(values[1]).strip()
   if not key or not label:continue
   if key in seen:raise ValueError('Clave SAT repetida: '+key)
   seen.add(key);rows.append({'clave':key,'nombre':label,'descripcion':str(values[2]).strip() if name=='unidades' else '', 'simbolo':str(values[6]).strip() if name=='unidades' else '', 'inicio':date(values[start]),'fin':date(values[end])})
  if len(rows)<(50000 if name=='productos' else 2000):raise ValueError('Catálogo incompleto: '+name)
  catalogs[name]=rows
 value={'fuente':url,'version':version,'sha256Original':hashlib.sha256(source.read_bytes()).hexdigest(),**catalogs};output.parent.mkdir(exist_ok=True);output.write_bytes(gzip.compress(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode(),mtime=0));print('SAT oficial:',{key:len(catalogs[key]) for key in catalogs},'archivo:',output)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=pathlib.Path,required=True);parser.add_argument('--url',required=True);parser.add_argument('--version',required=True);parser.add_argument('--output',type=pathlib.Path,default=pathlib.Path('sku-servidor/sat-catalogos.json.gz'));args=parser.parse_args();build(args.source,args.url,args.version,args.output)
