INSTALL=[
 ('Paquete','Descargar el ZIP completo de la versión piloto; extraer EXE, VC_redist y scripts en una carpeta temporal local.'),
 ('Instalar','Abrir PowerShell como administrador y ejecutar el instalador. Elegir y custodiar la clave administrativa sin escribirla en este manual.'),
 ('Servicio','El instalador crea la tarea programada ERP-JM-Lite al iniciar Windows. No es un servicio nativo que se administre necesariamente desde services.msc.'),
 ('Rutas','Programa por defecto en Program Files; configuración y datos bajo ProgramData\\ERP JM Lite. El config.json determina data_dir y log_dir efectivos.'),
 ('Red','El servidor escucha IPv4 por 8098. Clientes usan http://NOMBRE-O-IP-DEL-SERVIDOR:8098. En VPN revisar conectividad y regla de firewall autorizada.'),
 ('Validación','Entrar local y desde un cliente; comprobar empresa, perfil, módulo y un documento de prueba en ambiente aislado. Validar reinicio real de Windows en el servidor destino.'),
 ('Compatibilidad','Objetivo Windows 10/11 y Server 2016/2019/2022/2025 x64; la matriz completa y carga real siguen sin certificar. Server 2012 R2 requiere compilación Legacy independiente.')]

COMMANDS=[
 ('Instalación desde la carpeta del ZIP',r'powershell -NoProfile -ExecutionPolicy Bypass -File .\install_windows.ps1 -OpenFirewall'),
 ('Consultar tarea',r'Get-ScheduledTask -TaskName "ERP-JM-Lite"'),
 ('Detener la instalación administrada',r'Stop-ScheduledTask -TaskName "ERP-JM-Lite"'),
 ('Iniciar la instalación administrada',r'Start-ScheduledTask -TaskName "ERP-JM-Lite"'),
 ('Consultar quién escucha en 8098',r'Get-NetTCPConnection -LocalPort 8098 -State Listen')]

MAINTENANCE=[
 ('Antes de actualizar','Identificar EXE, config.json y data_dir usados. No confundir una copia portable con la instalación administrada.'),
 ('Respaldar','Descargar ZIP general y conservar EXE/configuración previos. No copiar un archivo SQLite abierto como una copia ordinaria de archivos.'),
 ('Detener','Usar Detener servicio, o la tarea programada. En ejecución directa, Ctrl+C de su consola. Cerrar el navegador no detiene el proceso.'),
 ('Actualizar','Sustituir sólo el programa/paquete correspondiente y conservar datos y configuración. No inicializar otra base en una ruta nueva por accidente.'),
 ('Arrancar y comprobar','Iniciar servicio y validar URL local/LAN/VPN, autenticación y documentos/stock/saldos. Registrar versión y resultado.'),
 ('Si falla','Revisar puerto, tarea, proceso y rutas. No matar un proceso desconocido para liberar 8098. No usar otro puerto como solución automática.'),
 ('Recuperar','Diagnosticar primero. Cuando proceda restaurar, probar la copia, coordinar ventana de mantenimiento y verificar datos posteriores. No borrar el original.')]

COMMON_ERRORS=[
 ('No abre el sitio','Servicio/tarea detenidos, IP incorrecta o puerto bloqueado','Sistemas verifica primero local 127.0.0.1:8098 y después red/VPN. No cambiar el puerto.'),
 ('8098 ocupado','Otro proceso o una segunda copia del ERP','Identificar proceso y configuración; detener sólo la copia conocida y autorizada.'),
 ('Pantalla sin módulos','Contrato o perfil sin accesos efectivos','Propietario revisa módulos contratados; Sistemas revisa perfil y alcance.'),
 ('Módulo sin registros','Filtros, empresa/sucursal/almacén o cartera distintos','Consultar contexto; después verificar si se inició otra base por data_dir diferente.'),
 ('Sesión requerida / 401','Sesión caducó o fue invalidada','Entrar otra vez. Consultar el folio antes de repetir una confirmación.'),
 ('Acceso denegado / 403','Permiso, cartera o alcance insuficientes','Solicitar autorización. No usar otra cuenta ni desactivar controles.'),
 ('Documento cambió / 409','Otra revisión guardada o intento repetido distinto','Copiar notas pendientes, actualizar y comparar la versión vigente.'),
 ('Datos inválidos / 400','Campos, unidades, cantidades o dependencias incorrectos','Leer aviso y corregir el origen; no confirmar a ciegas varias veces.'),
 ('Saldo/stock inesperado','Reserva, tránsito, parcial, crédito o moneda no considerados','Conciliar por documento y almacén, usando el Kárdex y el historial financiero.'),
 ('Error no previsto','Fallo de aplicación, disco o recurso del sistema','Detener reintentos; guardar captura y aviso completo. Sistemas revisa registros y respaldo.')]

IMPACTS=[
 ('Crear SKU / precio / imagen','0','0','Datos de catálogo; no son mercancía.'),
 ('Revisar / aplicar carga','0 normalmente','Según el registro importado','Revisar no guarda; aplicar sí modifica datos.'),
 ('Emitir requisición','0','0','Surtir realmente sí genera salida.'),
 ('Pedido de compra','0','0','La recepción física genera entrada.'),
 ('Recepción de compra','+ en destino configurado','0 por sí sola','Compra y cargo CXP se revisan aparte.'),
 ('Traspaso enviado / recibido','- origen / + destino','0','Destino aumenta sólo al recibir.'),
 ('Presupuesto / pedido / reserva','0 físico','0','Reserva reduce disponible, no físico.'),
 ('Remisión','- almacén elegido','0 por sí sola','Sólo lo realmente entregado.'),
 ('Factura comercial','0 adicional','+ CXC','Pendiente de timbrado PAC.'),
 ('Cobro / pago registrado','0','Reduce saldo','No ejecuta transferencias bancarias.'),
 ('Nota de crédito','0','Reduce deuda / crea a favor','No prueba devolución física.'),
 ('Devolución física de cliente','+ receptor','0 por sí sola','Condición determina destino permitido.'),
 ('Orden / explosionado / autorización','0 físico','0','Surtido y consumo posteriores sí mueven stock.'),
 ('Consumo / recepción de producción','- Producción / + PT o Q','Costo a PT','No inventar recepción sólo con plan.'),
 ('Registro QualityLite','0','0','Liberación de stock se registra aparte.'),
 ('Ticket TPV visible actual','0 automático','No cobra por sí solo','Documento EMITIDO, no confundir con PAGADA.'),
 ('Consulta / reporte / impresión','0','0','Puede recalcular cifras actuales.'),
 ('Cancelación física autorizada','Inverso auditado','Según documento','Resolver dependencias antes del origen.')]

SOURCES=[
 'Piloto publicado: ca0ce1e, 3 de noviembre de 2026. Las capturas son de una base de demostración aislada.',
 'Referencias del repositorio: docs/PERFILES_Y_ACCESOS.md, docs/CICLO_COMERCIAL_PENDIENTES.md, docs/PRODUCCION_DISENO.md y scripts de instalación.',
 'Los reportes y botones documentados se contrastaron con las pantallas y código del piloto. La visibilidad real depende de contratación, rol y alcance.',
 'PAC permanece pendiente por instrucción del propietario. No hay CFDI certificado, UUID, XML timbrado ni complemento fiscal de pago en esta entrega.',
 'Los ejemplos son operativos, no asesoría fiscal ni pólizas contables. Las tasas y decisiones reales se configuran por la empresa.',
 'No se publican claves, tokens ni datos operativos de clientes. Los datos, categorías y ubicaciones de demostración no vienen precargados en una instalación nueva.']
