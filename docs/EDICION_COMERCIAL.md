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

Sistemas configura los módulos adquiridos desde Menú de aplicaciones / Módulos contratados. Se aplica en servidor a cada sesión: el perfil puede acceder solo a la intersección entre sus permisos y lo contratado. Las cuentas internas conservan acceso de configuración. El instalador activa `require_module_contract=true`; hasta configurar el contrato, los usuarios operativos no reciben módulos. Compras enlaza sus SKU con materiales y almacenes. En cargas de Ventas se selecciona Ventas/CRM/pedidos institucionales, PDV, ambos o respetar el canal por fila del archivo. Los destinos forman parte de la revisión y no pueden alterarse al aplicar la carga revisada. Las oportunidades CRM permiten asociar un SKU de venta habilitado para la empresa.

Calidad cuenta con layouts de Documentos, Formatos, Registros, Auditorías, No conformidades y Acciones correctivas. Los formatos usan una fila por campo; los registros una fila por valor, indicando formato y versión aprobada. Los layouts de proveedores, clientes, precios e inventarios se aplican desde sus importadores específicos. Los de configuración sirven como guía de captura en sus pantallas.

## QualityLite integrado

La integración usa la misma sesión y la misma base SQLite. No requiere abrir otro servidor o mantener usuarios independientes. Incluye documentos, formatos con campos editables, registros capturados contra una versión aprobada, auditorías, no conformidades, acciones correctivas, adjuntos con SHA256 y bitácora. Las versiones aprobadas o cerradas quedan bloqueadas; una nueva versión conserva la anterior. Exportación a Excel, PDF y CSV.

El perfil Calidad puede operar estos módulos. Otros perfiles deben recibir el módulo explícitamente; tenerlo habilitado no concede permiso para editar si no son Calidad o Superadministrador. El icono es una pizarra. Esta integración no otorga una certificación de calidad o inocuidad.

## CRM y vendedores

Ventas ya tenía clientes, presupuestos y pedidos, pero no aislamiento por cartera ni seguimiento de oportunidades. Ahora Vendedores y CRM incorpora prospectos, etapas, próxima actividad, notas de seguimiento y tablero personal.

Cada vendedor consulta únicamente sus clientes asignados, oportunidades y seguimientos. Las mismas restricciones se aplican a documentos, impresiones y exportaciones; no se confía en filtros del navegador. Un prospecto sin cliente pertenece a quien lo creó. Una oportunidad con cliente sigue la asignación vigente del cliente: al reasignar, el vendedor anterior pierde acceso al historial asociado.

Gerencia y Sistemas consultan el conjunto y pueden agregar clientes. Solo las cuentas internas de Sistemas asignan o reasignan carteras, con control de revisión y auditoría. Los vendedores deben estar activos y tener acceso a la empresa destino. Las plantillas genéricas sin cliente pueden compartirse; las ligadas a un cliente respetan su cartera.

El tablero muestra prospectos/oportunidades, ganadas, pedidos, importe de pedidos, presupuestos, cartera abierta y seguimientos pendientes. Ventas cobradas PDV incluye solamente operaciones pagadas; los pedidos institucionales no se cuentan como ingreso cobrado. Se respetan empresas y módulos autorizados.

CRM incorpora alta de vendedor por Sistemas con acceso a la empresa seleccionada. Los presupuestos mensuales agrupan clientes, proyectos y pendientes, con meta, facturación real capturada, condiciones de pago, pedidos, observaciones, gráficas y CSV. Sistemas autoriza a usuarios específicos la consulta/captura del tablero mensual; esa autorización conserva el aislamiento de cartera. Gerencia y Sistemas tienen vista global.

Solo Gerencia y Superadministrador ven y configuran porcentajes por cliente/vendedor, con base sobre facturado o sobre cobrado. Cada factura CXC guarda la regla vigente al registrarse. Los reportes usan esas reglas históricas, consideran cobros parciales y reembolsos, y separan las monedas. La base de comisión puede capturarse distinta al total de factura; los cobros se prorratean contra esa base. Otros cargos y saldos iniciales no generan comisión. Hay filtros por empresa, vendedor y periodo, con exportación Excel, PDF y CSV. Las API y exportaciones rechazan a los demás perfiles. El presupuesto mensual capturado no se usa como factura para calcular comisiones.

Pendientes del análisis CRM: contactos múltiples por cuenta, campañas y adjuntos comerciales. No se envían correos automáticamente al registrar un seguimiento.

## Cuentas y pagos

Compras dispone de CXP, cargos, conceptos por empresa y pagos a proveedores. Una compra registrada puede ligarse una sola vez y exige que coincidan proveedor, empresa, moneda e importe. Ventas dispone de CXC, saldos de clientes, cobros y reembolsos. Las cuentas registran referencia, fecha, vencimiento, moneda, tipo y observaciones. Los conceptos inician vacíos y se pueden agregar o renombrar mediante API.

Los pagos son parciales e idempotentes, con revisión de concurrencia y control del saldo. No se aceptan sobrepagos; los reembolsos no exceden lo aplicado. Gerencia/Superadministrador pueden cancelar con motivo, conservando movimientos y bitácora. CXP también permite operar al perfil Compras; CXC se reserva a Gerencia/Superadministrador y se respetan empresas asignadas. Los saldos se totalizan por moneda. No se ejecutan transferencias bancarias ni se timbran CFDI desde estos registros.

## Menú, calidad y catálogos iniciales

El menú de aplicaciones agrupa Comercial, Compras, Almacenes, Calidad y Administración, con búsqueda y permisos. Conserva la identidad JM y los temas existentes. Sistemas configura la edición Lite o Avanzada; los módulos se contratan explícitamente, sin inferir un paquete de permisos por el nombre de la edición.

Calidad añade inspecciones/liberación, riesgos, calibraciones, mantenimiento, capacitación, quejas/devoluciones, evaluación de proveedores, control de cambios y mejora continua. Incluye panel de pendientes y estructuras opcionales de formatos para recepción, auditoría, equipos y quejas. No se precargan registros empresariales.

Las áreas solicitantes nuevas también inician vacías. Se agregan manualmente o mediante layout XLSX con revisión y aplicación atómica. Las pantallas de alta SKU incluyen configuración de tipos, categorías, subcategorías y PDV; los selectores vacíos muestran el paso requerido y bloquean la creación hasta configurar sus clasificaciones.

## Movimientos, restablecimiento y apariencia

Kárdex permite filtrar almacén, fechas, SKU, dirección, tipo, referencia, usuario y texto del movimiento. Los filtros se aplican en servidor y se usan para la exportación; los saldos conservan el contexto del periodo.

Restablecer toda la operación exige una vista previa, la frase de confirmación y la contraseña de la cuenta interna. Antes de escribir se realiza una copia completa de SQLite y se comparan nuevamente las huellas. Conserva empresa, activación, sucursales, clasificaciones, configuración, máximos de folios, cuentas internas y su 2FA. Elimina los datos operativos y usuarios adicionales. No se ha ejecutado sobre una base empresarial; las pruebas usan bases ficticias temporales.

Todas las pantallas comparten modos Claro, Oscuro y Sistema, colores Azul, Rosa, Verde y Morado, y estilos JM, PROF, MX, Halloween y Navidad. PROF usa paneles clásicos grises; MX combina navegación azul, acciones rojas y encabezados verdes. Halloween usa naranja/morado y Navidad rojo/verde. Estos tres estilos tienen paleta propia; JM y PROF permiten elegir los cuatro colores. La preferencia queda en el navegador. La interfaz conserva la identidad JM, sin logos empresariales heredados. El nombre visible del punto de venta es TPV; se conservan los códigos internos antiguos para no alterar bases ni archivos existentes, y el layout acepta CANAL=TPV.

## Distribución y validación

El ejecutable incorpora Python, SQLite y sus bibliotecas. El instalador piloto incorpora el runtime C++ oficial, puerto configurable, inicio automático con SYSTEM, registros de arranque y verificación HTTP. Las nuevas funcionalidades requieren regenerar el paquete; usar siempre el manifiesto correspondiente a la compilación.

GitHub Actions ejecuta comprobaciones de JavaScript y pruebas aisladas sobre Windows. Esto no sustituye pruebas de instalación elevada, reinicio completo ni LAN. La descarga oficial de Windows 11 está disponible en el laboratorio local; el montaje de la ISO falló con HRESULT 0x80070003 y todavía no existe evidencia de una instalación y reinicio satisfactorios de la VM. La matriz Windows 10/11 y Server, en especial el paquete Legacy para 2012 R2, y la carga de 40–50 usuarios permanecen pendientes de certificación.
