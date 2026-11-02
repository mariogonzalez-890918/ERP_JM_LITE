TITLE='ERP JM Lite'
VERSION='0.1.0-dev'
SUPPORT_LINE='Soporte y administración ERP JM Lite'
ADMIN_EMAIL='mario.gonzalez@jad-ayt.com'
ADMIN_NAME='Mario González'
def is_internal_admin(actor):return actor.get('role')=='superadmin' and (actor.get('internalAdmin') is True or actor.get('email')==ADMIN_EMAIL)
