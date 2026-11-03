"""Datos comerciales previos al PAC; no produce XML ni UUID fiscales."""
import json,pathlib,re
from decimal import Decimal
from functools import lru_cache
from inventarios import dec,fmt
from requisiciones import now
@lru_cache(maxsize=1)
def catalogs():
 value=json.loads(pathlib.Path(__file__).with_name('catalogos-fiscales.json').read_text(encoding='utf8'));today=now()[:10]
 return {key:[r for r in rows if (not r.get('inicio') or r['inicio']<=today) and (not r.get('fin') or r['fin']>=today)] if isinstance(rows,list) else rows for key,rows in value.items()}
def validate(customer,data):
 c=catalogs();rfc=str(customer.get('rfc','')).strip().upper();postal=str(customer.get('codigoPostalFiscal','')).strip();name=str(customer.get('nombreFiscal') or customer.get('nombre') or '').strip();regime=str(customer.get('regimenFiscal',''));use=str(customer.get('usoCFDI',''));method=str(data.get('metodoPago','PPD'));form=str(data.get('formaPago','99'));currency=data.get('moneda','MXN');exchange=dec(data.get('tipoCambio','1'),True)
 if not re.fullmatch(r'[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}',rfc) or not re.fullmatch(r'\d{5}',postal) or not name:raise ValueError('Completa nombre fiscal, RFC y código postal fiscal del cliente.')
 for field,value in [('regimen',regime),('uso',use),('metodo',method),('forma',form)]:
  if value not in {row['clave'] for row in c[field]}:raise ValueError('Selecciona una clave SAT válida para '+field+'.')
 person='fisica' if len(rfc)==13 else 'moral';regime_row=next(r for r in c['regimen'] if r['clave']==regime);use_row=next(r for r in c['uso'] if r['clave']==use)
 if regime_row.get(person) is False or use_row.get(person) is False or use_row.get('regimenes') and regime not in use_row['regimenes']:raise ValueError('El régimen fiscal y uso de CFDI no son compatibles con el tipo de persona del cliente.')
 if currency not in ('MXN','USD','EUR') or currency=='MXN' and exchange!=1:raise ValueError('Selecciona MXN, USD o EUR; MXN utiliza tipo de cambio 1.')
 if method=='PPD' and form!='99':raise ValueError('Para PPD selecciona forma 99 Por definir; registra los cobros posteriores por separado.')
 return {'nombreFiscal':name,'rfc':rfc,'codigoPostalFiscal':postal,'regimenFiscal':regime,'usoCFDI':use,'metodoPago':method,'formaPago':form,'moneda':currency,'tipoCambio':fmt(exchange),'validacion':'DATOS_PREVIOS_PAC'}
