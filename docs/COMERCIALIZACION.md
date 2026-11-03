# ERP JM Lite: base comercial instalable

Estado: paquete piloto 0.1.0-dev. Producto independiente de ERP JM Lite. No se han conectado ni copiado sus bases, credenciales o maestros.

## Arquitectura y acceso

Servidor web Python x64 con SQLite en disco local del servidor. El ejecutable incorpora Python, SQLite, ReportLab, Pillow y las bibliotecas nativas recogidas por PyInstaller. El paquete agrega Microsoft Visual C++ x64; no se requiere un compilador C++. Los clientes usan un navegador moderno y se conectan a `http://SERVIDOR:PUERTO`. No requieren instalar Python, Office, SQLite ni C++.

La instalación utiliza exclusivamente TCP 8098 y escucha en todas las interfaces IPv4 (`0.0.0.0`), incluidas las direcciones LAN y VPN. Si el puerto está ocupado o no está disponible, avisa y no selecciona otro. El acceso se realiza mediante `http://IP-DEL-SERVIDOR:8098`. El arranque técnico para pruebas todavía permite `--port 0` en bases aisladas; el instalador comercial solo acepta 8098.

## Instalación y arranque automático

Extraer todo `ERP_JM_Lite_Windows_Piloto.zip` y ejecutar PowerShell como administrador:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_windows.ps1 -OpenFirewall
```

Se verifica el manifiesto SHA256 y la firma Microsoft del redistribuible. El programa se instala en `Program Files\ERP JM Lite`; la configuración, las bases y los registros quedan en `ProgramData\ERP JM Lite`, con acceso a SYSTEM y Administradores. La tarea `ERP-JM-Lite` ejecuta el servidor al iniciar Windows con la cuenta SYSTEM y sin sesión de usuario. Ante fallos intenta reiniciar hasta cinco veces, cada minuto. Evita instancias duplicadas. El navegador puede minimizarse o cerrarse: no controla la vida del servidor.

La regla opcional de firewall permite TCP 8098 para el ejecutable instalado en todos los perfiles y desde cualquier dirección, para aceptar también redes VPN como ZeroTier, Radmin y Hamachi. La conectividad depende además de las reglas de la VPN. La instalación comprueba HTTP antes de informar éxito. Los registros de la ejecución actual y anterior quedan en `ProgramData\ERP JM Lite\logs`.

## Administrador

La cuenta permanente es **Mario González**, `mario.gonzalez@jad-ayt.com`, con perfil superadministrador. No puede desactivarse ni degradarse; AUXTI no puede modificarla. La inicialización solicita la contraseña oculta. Solo se guarda un hash PBKDF2-SHA256 con sal aleatoria; reinstalar no cambia la contraseña existente. No existe una contraseña comercial universal dentro del código, del EXE o del ZIP.

Para automatización de instalaciones nuevas, `--initialize --admin-seed ARCHIVO` admite exclusivamente sal/hash válidos. El archivo es privado, queda fuera de la distribución y debe retirarse tras provisionar. No sustituye contraseñas de usuarios existentes. La clave solicitada por Mario se preparó únicamente en los datos locales excluidos de Git.

## Matriz de sistemas

| Plataforma x64 | Objetivo | Estado |
|---|---|---|
| Windows 11 | Primera VM de pruebas | Ver registros del laboratorio; no inferir aprobación por crear el disco |
| Windows 10 | Segunda VM de pruebas | Pendiente |
| Server 2016, 2019, 2022, 2025 | Paquete moderno | Pendiente de pruebas por sistema |
| Server 2012 R2 | Paquete Legacy independiente | Pendiente de definir runtime, bibliotecas y certificación; el instalador moderno lo rechaza |

Microsoft limita el runtime v14 actual a Windows 10/11 y Server 2016/2019/2022/2025. No basta con agregar un redistribuible antiguo a este EXE para certificar Server 2012 R2. Fuente: [sistemas del redistribuible C++](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/).

## Pruebas de Windows

`verify_windows.ps1 -BeforeReboot` verifica tarea y web y registra el arranque actual. Después de reiniciar, `verify_windows.ps1` exige una fecha nueva de arranque de Windows y una ejecución posterior de la tarea. No declara éxito si solamente se reinició el proceso.

`create_windows_lab.ps1` requiere privilegios de administrador y una ISO oficial Enterprise de evaluación. Crea un VHDX nuevo, aplica Windows únicamente al disco virtual verificado y monta una VM de generación 2 con TPM virtual, 2 CPU y memoria dinámica (4 GB iniciales). Usa una red interna sin puente, NAT o acceso a servidores empresariales. No modifica VMs existentes ni reinicia el anfitrión. Las credenciales del sistema invitado son aleatorias y se guardan cifradas por Windows para el usuario del laboratorio.

La automatización instala el paquete en la VM, registra una comprobación inicial, reinicia exclusivamente la VM y comprueba el arranque automático y el acceso web desde el anfitrión. Solo `result.txt` con PASS confirma el recorrido completo. `lab-error.txt` y los registros conservan fallos. Una descarga o compilación terminada no acredita compatibilidad.

## Interfaz

Los temas incluyen New Year, Autumn, Spring y Calaveritas (calaveritas de azúcar, flores y papel picado), además de los estilos anteriores. El color amarillo se suma a azul, rosa, verde y morado. Las preferencias se mantienen al abrir módulos y se sincronizan entre pestañas del mismo servidor. Los temas nuevos se comprobaron en las doce rutas principales y se revisaron contrastes de texto, texto secundario y botones en claro/oscuro.

En Respaldo y restauración → Respaldo general, Sistemas puede descargar un ZIP con una copia consistente de toda la base mediante SQLite Backup API, configuración portable, verificador privado si existe, manifiesto SHA256 e instrucciones. Incluye logos, usuarios, permisos, Calidad y evidencias. La copia excluye sesiones activas y no modifica las sesiones originales. No duplica EXE, runtime, registros ni respaldos anteriores. Las pruebas comprueban escrituras confirmadas en WAL, integridad, archivos BLOB y rechazo a otros perfiles.

Identidad JM propia: navegación azul, formularios y tablas compactos, cabeceras de documentos y logotipo vectorial. No incorpora vistas ni código de Odoo, SAP, Oracle o Aspel. Se conserva la lógica y las rutas de los módulos existentes. Los identificadores internos heredados no son la marca del producto.

Empresa y configuración permite subir, sustituir o quitar un logo PNG/JPG por razón social. Valida el contenido, limita el archivo a 2 MB y guarda una copia PNG normalizada en SQLite. Solo Superadministrador puede modificarlo; consultar un logo requiere acceso a su razón social.

Los impuestos configurables son tasas porcentuales trasladadas, independientes por empresa y sin precarga. Pueden ligarse a SKU de compras o ventas; los productos de venta también los seleccionan durante su captura. Ventas desglosa el impuesto incluido en el precio y compras lo agrega al costo. Cambiar una tasa no recalcula documentos emitidos. Esta configuración no implementa retenciones ni timbrado fiscal.

Crear SKU Ventas incluye una ficha comercial: empresa, naturaleza de producto/servicio, unidad, línea, clave alterna o código de barras, claves SAT informativas, impuesto, destinos y precios. Al guardar, el código y el producto comercial se registran juntos en una transacción; un impuesto inválido no deja un SKU a medias. Puede reservarse solo el código desmarcando expresamente la ficha comercial. Las claves SAT capturadas no constituyen timbrado ni validación contra el catálogo del SAT.

Desde esa pantalla se agregan impuestos y se descarga el layout XLSX IMPUESTOS para carga masiva. Sus columnas son AMBITO, SKU, IMPUESTO, TASA y ACTIVO (SI/NO). AMBITO admite compras/ventas; dejando AMBITO y SKU vacíos se configura únicamente el impuesto. La vista previa identifica creaciones, actualizaciones y vínculos; aplicar exige el mismo archivo, empresa y estado de datos. La carga completa se revierte si alguna fila es inválida.

Referencia funcional consultada: [datos generales de productos y servicios SAE](https://saeportaldeclientes.aspel.com.mx/crear-o-dar-de-alta-productos-y-servicios/) y [precios e impuestos SAE](https://saeportaldeclientes.aspel.com.mx/crear-o-dar-de-alta-productos-y-servicios-precios-e-impuestos/). Se tomaron como referencia la organización y los campos; la implementación y la interfaz son propias.

La ficha utiliza precios Público, Mínimo y Remate, guardados como listas independientes. Las listas históricas de instalaciones anteriores se conservan para sus documentos; sus importes no se reinterpretan como mínimo o remate. Las cajas nuevas pueden elegir cualquiera de las tres listas actuales. Los layouts nuevos usan PRECIO MINIMO y PRECIO REMATE y siguen reconociéndose los encabezados de archivos históricos.

Las unidades de venta y líneas se seleccionan desde catálogos configurados por Superadministrador, con revisión y desactivación sin borrar historial. La línea admite vacío. Cada unidad configurable exige una clave SAT válida; el producto hereda esa clave y el servidor rechaza unidades inventadas o claves incompatibles. Los nombres históricos sin catálogo se conservan si no se modifican.

Se incluye una copia local completa de c_ClaveProdServ (52,513 claves) y c_ClaveUnidad (2,418), del [archivo oficial SAT del 29 de octubre de 2026](http://omawww.sat.gob.mx/tramitesyservicios/Paginas/documentos/catCFDI_V_4_20261029.xls), enlazado en el [Anexo 20](http://omawww.sat.gob.mx/tramitesyservicios/Paginas/anexo_20.htm). El buscador funciona sin conexión, por clave o descripción, y filtra las vigencias del archivo. Son catálogos de consulta, no editables por usuarios. El recurso incluye URL, versión y SHA256 del original. Esta incorporación no implica timbrado de CFDI.

Para regenerar el recurso a partir de una descarga oficial verificada: `python tools/build_sat_catalogs.py --source ARCHIVO.xls --url URL-OFICIAL-SAT --version AAAA-MM-DD`. Requiere xlrd de requirements-dev; los clientes y el EXE usan el recurso comprimido y no requieren Excel ni xlrd.

Gerencia y Superadministrador asignan y reasignan clientes. Solo esos perfiles consultan o configuran comisiones: sobre facturado o cobrado, antes de impuestos o con impuestos. CXC conserva la regla vigente al registrar cada factura y el subtotal capturado; los cobros parciales y reembolsos se prorratean. El reporte separa totales por moneda y se exporta a CSV, XLSX y PDF.

## Pendientes antes de vender

Probar cada sistema de la matriz, instalación/actualización/desinstalación, recuperación desde respaldo, navegadores y flujos completos; generalizar sucursales y parámetros heredados; configurar cada empresa; integrar HTTPS y licenciamiento; firmar el paquete propio y revisar las licencias de redistribución; ejecutar carga de 40–50 usuarios y decidir con evidencia si SQLite es suficiente. No se han certificado esos puntos ni migrado bases.

## Compilación

En Python Windows x64, instalar `requirements-dev.txt`, disponer de Node y obtener el redistribuible oficial Microsoft. Ejecutar:

```powershell
python tools/build_public.py --vc-redist RUTA\VC_redist.x64.exe
```

La compilación genera semillas vacías nuevas en una carpeta temporal y excluye la semilla del administrador. No incorpora la carpeta local `data`, configuraciones privadas ni maestros operativos. El manifiesto registra las versiones y los hashes de los componentes distribuidos.
