"""2FA TOTP opcional, secretos protegidos por Windows y recuperación de un solo uso."""
import base64,ctypes,hashlib,hmac,json,os,secrets,struct,time
from urllib.parse import quote

def totp(secret,counter):
 digest=hmac.new(base64.b32decode(secret),struct.pack('>Q',counter),hashlib.sha1).digest();offset=digest[-1]&15
 return str((struct.unpack('>I',digest[offset:offset+4])[0]&0x7fffffff)%1000000).zfill(6)

def protect(value,decode=False):
 if os.name!='nt':raise ValueError('La protección del secreto 2FA requiere el servidor Windows.')
 class Blob(ctypes.Structure):_fields_=[('size',ctypes.c_ulong),('data',ctypes.POINTER(ctypes.c_ubyte))]
 raw=base64.b64decode(value) if decode else value.encode();buffer=ctypes.create_string_buffer(raw);source=Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));target=Blob()
 if decode:ok=ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target))
 else:ok=ctypes.windll.crypt32.CryptProtectData(ctypes.byref(source),None,None,None,None,5,ctypes.byref(target))
 if not ok:raise ValueError('Windows no pudo proteger o recuperar el secreto 2FA.')
 try:result=ctypes.string_at(target.data,target.size);return result.decode() if decode else base64.b64encode(result).decode()
 finally:ctypes.windll.kernel32.LocalFree(target.data)

class AccountSecurity:
 def __init__(self,store):
  self.store=store
  with store.connect() as db:db.execute("CREATE TABLE IF NOT EXISTS user_2fa(email TEXT PRIMARY KEY,secret TEXT NOT NULL,pending TEXT NOT NULL,pending_until REAL NOT NULL,last_counter INTEGER NOT NULL,recovery TEXT NOT NULL)")
 def password(self,db,actor,password):
  row=db.execute('SELECT salt,password_hash FROM users WHERE email=? AND active=1',(actor['email'],)).fetchone()
  if not isinstance(password,str) or not row or not hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(row[0]),310000).hex(),row[1]):raise PermissionError('Contraseña actual incorrecta.')
 def status(self,actor):
  with self.store.connect() as db:row=db.execute('SELECT secret,recovery FROM user_2fa WHERE email=?',(actor['email'],)).fetchone()
  return {'habilitado':bool(row and row[0]),'codigosDisponibles':len(json.loads(row[1])) if row else 0,'minimoPassword':4}
 def begin(self,data,actor):
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');self.password(db,actor,data.get('password'));row=db.execute('SELECT secret FROM user_2fa WHERE email=?',(actor['email'],)).fetchone()
   if row and row[0]:raise ValueError('2FA ya está activo. Desactívalo con tu código antes de cambiar el autenticador.')
   secret=base64.b32encode(secrets.token_bytes(20)).decode();protected=protect(secret)
   db.execute("INSERT INTO user_2fa VALUES(?,'',?,?, -1,'[]') ON CONFLICT(email) DO UPDATE SET pending=excluded.pending,pending_until=excluded.pending_until",(actor['email'],protected,time.time()+600))
  return {'secreto':secret,'uri':'otpauth://totp/'+quote('ERP JM Lite:'+actor['email'],safe='')+'?secret='+secret+'&issuer=ERP%20JM%20Lite&algorithm=SHA1&digits=6&period=30','venceEnSegundos':600}
 def matching_counter(self,secret,code,minimum=-1):
  counter=int(time.time()//30)
  return next((c for c in (counter-1,counter,counter+1) if c>minimum and c>=0 and hmac.compare_digest(totp(secret,c),str(code))),None)
 def confirm(self,data,actor):
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT pending,pending_until FROM user_2fa WHERE email=?',(actor['email'],)).fetchone()
   if not row or not row[0] or row[1]<time.time():raise ValueError('La preparación 2FA caducó. Iníciala nuevamente.')
   counter=self.matching_counter(protect(row[0],True),data.get('codigo',''))
   if counter is None:raise PermissionError('Código 2FA incorrecto.')
   codes=[secrets.token_hex(8).upper() for _ in range(8)];hashes=[hashlib.sha256(c.encode()).hexdigest() for c in codes]
   db.execute("UPDATE user_2fa SET secret=pending,pending='',pending_until=0,last_counter=?,recovery=? WHERE email=?",(counter,json.dumps(hashes),actor['email']));db.execute('DELETE FROM sessions WHERE email=? AND csrf<>?',(actor['email'],actor['csrf']))
  return {'ok':True,'codigosRecuperacion':codes,'nota':'Guárdalos fuera de este equipo. Cada código se usa una sola vez.'}
 def verify_login(self,db,email,code):
  row=db.execute('SELECT secret,last_counter,recovery FROM user_2fa WHERE email=?',(email,)).fetchone()
  if not row or not row[0]:return True
  if not isinstance(code,str) or len(code)>64:return False
  recovery=json.loads(row[2]);digest=hashlib.sha256(code.strip().upper().encode()).hexdigest()
  if digest in recovery:
   recovery.remove(digest);db.execute('UPDATE user_2fa SET recovery=? WHERE email=?',(json.dumps(recovery),email));return True
  try:counter=self.matching_counter(protect(row[0],True),code,row[1])
  except ValueError:return False
  if counter is None:return False
  db.execute('UPDATE user_2fa SET last_counter=? WHERE email=?',(counter,email));return True
 def disable(self,data,actor):
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');self.password(db,actor,data.get('password'))
   if not self.verify_login(db,actor['email'],data.get('codigo','')):raise PermissionError('Código 2FA o de recuperación incorrecto.')
   db.execute('DELETE FROM user_2fa WHERE email=?',(actor['email'],));db.execute('DELETE FROM sessions WHERE email=? AND csrf<>?',(actor['email'],actor['csrf']))
  return {'ok':True}
 def change_password(self,data,actor):
  from server import new_password
  with self.store.connect() as db:
   db.execute('BEGIN IMMEDIATE');self.password(db,actor,data.get('password'))
   if not self.verify_login(db,actor['email'],data.get('codigo','')):raise PermissionError('Confirma tu código 2FA o de recuperación.')
   if data.get('nueva')!=data.get('confirmacion'):raise ValueError('Las contraseñas nuevas no coinciden.')
   salt,digest=new_password(data.get('nueva'));db.execute('UPDATE users SET salt=?,password_hash=? WHERE email=?',(salt,digest,actor['email']));db.execute('DELETE FROM sessions WHERE email=?',(actor['email'],))
  return {'ok':True,'requiereLogin':True}
