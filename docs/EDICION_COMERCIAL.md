# ERP JM Lite · Edición comercial

Implementación del 31/10/2026. Estado: piloto de desarrollo, con cambios respaldados en la rama `codex/comercial-quality-configuracion`. No constituye una certificación de compatibilidad Windows ni de capacidad multiusuario.

## Configuración de empresa

Empresa contiene nombre, RFC, domicilio, rubro, responsable, correo y teléfono. Las razones sociales operativas se asignan a las sucursales configuradas. Las instalaciones nuevas inician sin sucursales; Sistemas las configura con nombres y series únicas. Las sucursales históricas de una instalación con documentos se conservan.

Los catálogos SKU de Compras, Ventas y agrupaciones PDV **inician vacíos**. Sistemas configura tipos, categorías y subcategorías de dos caracteres y agrupaciones PDV de tres. Las descripciones pueden editarse. Un código utilizado no puede eliminarse porque integra el historial de SKU. La configuración comercial se guarda en SQLite y se carga en los formularios y generadores.

## Cuentas internas y seguridad

Las cuentas técnicas se aprovisionan mediante configuración privada; no aparecen en Usuarios ni en selectores comerciales o de compras. No pueden modificarse, desactivarse o degradarse desde Usuarios. El restablecimiento conserva las cuentas técnicas y su seguridad. No existe una contraseña de producción dentro del código o de las distribuciones públicas.

Las contraseñas tienen un mínimo de cuatro caracteres y se guardan mediante PBKDF2-SHA256 con sal aleatoria. Mostrar contraseña se limita a la entrada que se está capturando; no recupera contraseñas guardadas.

Mi seguridad permite activar TOTP opcional, confirmar la aplicación autenticadora y obtener ocho códigos de recuperación de un solo uso. Los códigos TOTP consumidos no pueden repetirse. Los secretos TOTP se protegen con DPAPI de Windows en el ámbito del equipo. Tras mover una instalación a otro Windows, el secreto DPAPI no es portable: conservar códigos de recuperación y reprovisionar el autenticador. Cambiar una contraseña cierra las sesiones de esa cuenta. La contraseña y un código válido son obligatorios para desactivar 2FA.

## Activación

Solo las cuentas internas de Sistemas pueden ingresar el token. El servidor compara PBKDF2 con el verificador privado; el token no se guarda en texto, no se devuelve por API y no se registra en auditoría. El estado público muestra solamente si está activo y la fecha.

La instalación Windows establece `require_activation=true`: las cuentas internas pueden configurar el producto, pero los usuarios operativos no acceden hasta la activación. El instalador acepta `-AdminSeed` y `-ActivationVerifier` como archivos privados separados. Para preparar el verificador en el equipo de Sistemas puede usarse `tools/provision_activation.py --data-dir RUTA_PRIVADA`, que pide el token sin mostrarlo. Las semillas, alias internos y verificadores quedan fuera de Git y del ZIP público. No equivale a un sistema de licenciamiento remoto firmado, por empresa y con caducidad: esa etapa sigue pendiente.

## Cargas iniciales y layouts

Layouts y cargas presenta archivos por módulo e instrucciones de destino, respetando los permisos. Compras enlaza el SKU generado con el material de requisiciones, pedidos de compra e inventarios. Ventas y PDV conservan los SKU históricos y enlazan el catálogo con productos comerciales, canales y precios por empresa.

La vista previa ejecuta y valida la operación completa en una transacción que se revierte. Aplicar exige la misma huella de archivo y base; una falla revierte todos los destinos. La revisión no guarda productos parciales. Se requieren clasificaciones configuradas, unidad, impuestos y precios del canal.

Solicitud para la siguiente etapa: Sistemas debe seleccionar los módulos de destino del SKU (Compras y Almacenes para compra; Ventas, CRM, Pedidos institucionales y PDV para venta), y habilitar los módulos adquiridos por cada instalación. Los permisos actuales por perfil no sustituyen ese control de módulos contratados. El piloto todavía no implementa esa selección ni el licenciamiento por módulo.

Calidad cuenta con layouts de Documentos, Formatos, Registros, Auditorías, No conformidades y Acciones correctivas. Los formatos usan una fila por campo; los registros una fila por valor, indicando formato y versión aprobada. Los layouts de proveedores, clientes, precios e inventarios se aplican desde sus importadores específicos. Los de configuración sirven como guía de captura en sus pantallas.

## QualityLite integrado

La integración usa la misma sesión y la misma base SQLite. No requiere abrir otro servidor o mantener usuarios independientes. Incluye documentos, formatos con campos editables, registros capturados contra una versión aprobada, auditorías, no conformidades, acciones correctivas, adjuntos con SHA256 y bitácora. Las versiones aprobadas o cerradas quedan bloqueadas; una nueva versión conserva la anterior. Exportación a Excel, PDF y CSV.

El perfil Calidad puede operar estos módulos. Otros perfiles deben recibir el módulo explícitamente; tenerlo habilitado no concede permiso para editar si no son Calidad o Superadministrador. El icono es una pizarra. Esta integración no otorga una certificación de calidad o inocuidad.

## CRM y vendedores

Ventas ya tenía clientes, presupuestos y pedidos, pero no aislamiento por cartera ni seguimiento de oportunidades. Ahora Vendedores y CRM incorpora prospectos, etapas, próxima actividad, notas de seguimiento y tablero personal.

Cada vendedor consulta únicamente sus clientes asignados, oportunidades y seguimientos. Las mismas restricciones se aplican a documentos, impresiones y exportaciones; no se confía en filtros del navegador. Un prospecto sin cliente pertenece a quien lo creó. Una oportunidad con cliente sigue la asignación vigente del cliente: al reasignar, el vendedor anterior pierde acceso al historial asociado.

Gerencia y Sistemas consultan el conjunto y pueden agregar clientes. Solo las cuentas internas de Sistemas asignan o reasignan carteras, con control de revisión y auditoría. Los vendedores deben estar activos y tener acceso a la empresa destino. Las plantillas genéricas sin cliente pueden compartirse; las ligadas a un cliente respetan su cartera.

El tablero muestra prospectos/oportunidades, ganadas, pedidos, importe de pedidos, presupuestos, cartera abierta y seguimientos pendientes. Ventas cobradas PDV incluye solamente operaciones pagadas; los pedidos institucionales no se cuentan como ingreso cobrado. Se respetan empresas y módulos autorizados.

Pendientes del análisis CRM: contactos múltiples por cuenta, campañas, adjuntos comerciales, reglas de comisión y conexión a facturación/cobranza. No se envían correos automáticamente al registrar un seguimiento.

## Movimientos, restablecimiento y apariencia

Kárdex permite filtrar almacén, fechas, SKU, dirección, tipo, referencia, usuario y texto del movimiento. Los filtros se aplican en servidor y se usan para la exportación; los saldos conservan el contexto del periodo.

Restablecer toda la operación exige una vista previa, la frase de confirmación y la contraseña de la cuenta interna. Antes de escribir se realiza una copia completa de SQLite y se comparan nuevamente las huellas. Conserva empresa, activación, sucursales, clasificaciones, configuración, máximos de folios, cuentas internas y su 2FA. Elimina los datos operativos y usuarios adicionales. No se ha ejecutado sobre una base empresarial; las pruebas usan bases ficticias temporales.

Todas las pantallas comparten modos Claro, Oscuro y Sistema, y colores Azul, Rosa y Verde. La preferencia queda en el navegador. La interfaz usa menús, barras de acciones y tablas con identidad JM, sin logos empresariales heredados.

## Distribución y validación

El ejecutable incorpora Python, SQLite y sus bibliotecas. El instalador piloto incorpora el runtime C++ oficial, puerto configurable, inicio automático con SYSTEM, registros de arranque y verificación HTTP. Las nuevas funcionalidades requieren regenerar el paquete; usar siempre el manifiesto correspondiente a la compilación.

GitHub Actions ejecuta comprobaciones de JavaScript y pruebas aisladas sobre Windows. Esto no sustituye pruebas de instalación elevada, reinicio completo ni LAN. La descarga oficial de Windows 11 está disponible en el laboratorio local; el montaje de la ISO falló con HRESULT 0x80070003 y todavía no existe evidencia de una instalación y reinicio satisfactorios de la VM. La matriz Windows 10/11 y Server, en especial el paquete Legacy para 2012 R2, y la carga de 40–50 usuarios permanecen pendientes de certificación.
