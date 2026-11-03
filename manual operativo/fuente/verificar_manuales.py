"""Control documental: contenido, anexos, ausencia de claves y renderizado completo."""
from pathlib import Path
import hashlib,json
import pymupdf
from PIL import Image,ImageDraw
from contenido import MODULES,QUALITY_AREAS
from reportes import REPORTS
ROOT=Path(__file__).resolve().parents[2];FOLDER=ROOT/'manual operativo';REVIEW=ROOT/'tmp/pdfs/revision-final';REVIEW.mkdir(parents=True,exist_ok=True)
expected={'Manual_Tecnico_y_Dueno_ERP_JM.pdf':64,'Manual_Usuario_ERP_JM.pdf':60}
manifest={'edicion_documental':'1.0','fecha':'2026-11-03','piloto_documentado':'ca0ce1e','fichas_operativas':len(MODULES),'fichas_reportes':len(REPORTS),'areas_qualitylite':len(QUALITY_AREAS),'archivos':{}}
for name,count in expected.items():
 path=FOLDER/name;doc=pymupdf.open(path);assert len(doc)==count,(name,len(doc));text='\n'.join(p.get_text() for p in doc)
 for module in MODULES:assert module['title'] in text,(name,module['title'])
 for report in REPORTS:assert report['title'] in text,(name,report['title'])
 assert len(doc.get_toc())>=40;assert '\ufffd' not in text and '\u25a0' not in text
 # Las claves reales no se insertan en la documentación; este control detecta campos sensibles impropios.
 assert 'token_hash' not in text and 'password_hash' not in text
 for n in range(12):
  p=doc[len(doc)-12+n];assert f'{n+1:02d}' in p.get_text();assert p.rect.width>p.rect.height
 for i,p in enumerate(doc):
  assert len(p.get_text().strip())>80,(name,i+1)
  p.get_pixmap(matrix=pymupdf.Matrix(.9,.9)).save(REVIEW/f'{path.stem}-{i+1:02d}.png')
  for block in p.get_text('dict')['blocks']:
   for line in block.get('lines',[]):
    x0,y0,x1,y1=line['bbox'];assert -1<=x0 and x1<=p.rect.width+1 and -1<=y0 and y1<=p.rect.height+1,(name,i+1,line['bbox'])
 for start in range(0,len(doc),12):
  sheet=Image.new('RGB',(4*320,3*470),'#dbe4eb');draw=ImageDraw.Draw(sheet)
  for index in range(start,min(start+12,len(doc))):
   image=Image.open(REVIEW/f'{path.stem}-{index+1:02d}.png');image.thumbnail((310,438));x=(index-start)%4*320;y=(index-start)//4*470;sheet.paste(image,(x,y));draw.text((x+5,y+445),str(index+1),fill='black')
  sheet.save(REVIEW/f'{path.stem}-contacto-{start//12+1}.png')
 manifest['archivos'][name]={'paginas':len(doc),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size};doc.close()
flow=FOLDER/'recursos/Flujo_completo_del_ERP.pdf';doc=pymupdf.open(flow);assert len(doc)==12;manifest['archivos']['recursos/Flujo_completo_del_ERP.pdf']={'paginas':12,'sha256':hashlib.sha256(flow.read_bytes()).hexdigest(),'bytes':flow.stat().st_size};doc.close()
(FOLDER/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(manifest,ensure_ascii=True))
