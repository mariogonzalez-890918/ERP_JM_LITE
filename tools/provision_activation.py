"""Crear un verificador privado de activacion. Nunca incluye el token en argumentos o salidas."""
import argparse,getpass,hashlib,json,pathlib,secrets
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',type=pathlib.Path,required=True);args=parser.parse_args();target=args.data_dir/'activation-verifier.json'
 if target.exists():parser.error('Ya existe un verificador. No se sobrescribe.')
 token=getpass.getpass('Token privado de activación: ')
 if not 16<=len(token)<=250 or token!=getpass.getpass('Confirma el token: '):parser.error('Token inválido o confirmación diferente.')
 salt=secrets.token_hex(16);args.data_dir.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps({'salt':salt,'token_hash':hashlib.pbkdf2_hmac('sha256',token.encode(),bytes.fromhex(salt),310000).hex()}),encoding='utf8');print('Verificador privado creado. No lo publiques ni lo incluyas en la distribución pública.')
if __name__=='__main__':main()
