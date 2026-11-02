# Perfiles y acceso comercial

El acceso efectivo combina tres configuraciones existentes:

1. El propietario habilita los módulos adquiridos en **Menú de aplicaciones → Módulos contratados**.
2. El superadministrador configura los módulos del rol en **Accesos por perfil**. La tabla muestra los efectivos y los pendientes de contratación.
3. En **Comercial → Configuración → Accesos por usuario**, se asignan las razones sociales y sucursales del vendedor. En **Vendedores y CRM** se asignan los clientes a cada vendedor; únicamente Gerencia y Superadministrador pueden reasignarlos.

Un rol Ventas no habilita por sí solo módulos sin contratar ni el acceso a otras carteras. Un contrato pendiente permanece bloqueado para las cuentas ordinarias; el inicio explica cómo resolverlo. Las cuentas internas conservan su administración. Las comisiones se mantienen privadas para Gerencia y Superadministrador.

Los cambios de perfil y contratación se evalúan en cada petición. Actualiza la página para renovar los menús. No hace falta cambiar la contraseña ni desactivar la navegación de incógnito.

Para una ejecución portable, conserva el EXE y su `config.json`: `data_dir` identifica la base de esa instalación. Ejecutar otra copia del EXE sin esa configuración puede abrir una base nueva. Antes de cambiar la ruta, respaldar ambas bases mediante SQLite y conservar las configuraciones anteriores. No copiar un archivo SQLite abierto mediante una copia de archivos corriente.
