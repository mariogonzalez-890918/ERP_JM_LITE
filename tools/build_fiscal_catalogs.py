"""Extracto reproducible del XLS oficial del SAT; xlrd sólo se usa al compilar."""
import argparse,hashlib,json,pathlib,re
import xlrd

def build(source,url,target):
 book=xlrd.open_workbook(source,on_demand=True);result={'fuente':url,'sha256':hashlib.sha256(pathlib.Path(source).read_bytes()).hexdigest()}
 for key,name in [('regimen','c_RegimenFiscal'),('uso','c_UsoCFDI'),('forma','c_FormaPago'),('metodo','c_MetodoPago'),('moneda','c_Moneda')]:
  sheet=book.sheet_by_name(name);rows=[];header=next(i for i in range(12) if sheet.cell_value(i,0)==name);head=[str(v).lower() for v in sheet.row_values(header)]
  for i in range(header+1,sheet.nrows):
   raw=sheet.row_values(i);code=str(int(raw[0])) if isinstance(raw[0],(int,float)) else str(raw[0]).strip()
   if key=='forma' and code.isdigit():code=code.zfill(2)
   if not re.fullmatch(r'\d{2,3}|[A-Z]{3}|[A-Z]\d{2}',code):continue
   value={'clave':code,'descripcion':str(raw[1]).strip()}
   for j,title in enumerate(head):
    if 'vigencia' in title and raw[j]:
     date=xlrd.xldate_as_datetime(raw[j],book.datemode).date().isoformat() if isinstance(raw[j],(int,float)) else str(raw[j])
     value['fin' if 'fin' in title else 'inicio']=date
    if 'gimen' in title and key=='uso':value['regimenes']=re.findall(r'\d{3}',str(raw[j]))
   if key in ('regimen','uso') and len(raw)>3:
    value['fisica']=str(raw[2]).strip().lower() in ('sí','si','s');value['moral']=str(raw[3]).strip().lower() in ('sí','si','s')
   rows.append(value)
  result[key]=rows;book.unload_sheet(name)
 pathlib.Path(target).write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf8')
 return {key:len(value) for key,value in result.items() if isinstance(value,list)}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('--url',required=True);parser.add_argument('--output',default='sku-servidor/catalogos-fiscales.json');args=parser.parse_args();print(build(args.source,args.url,args.output))
