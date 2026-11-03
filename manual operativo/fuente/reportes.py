"""Fichas de los reportes que ofrece cada pantalla del piloto."""
REPORTS=[]
def add(title,route,formats,filters,steps,read,example,errors,access):
 REPORTS.append(dict(title=title,route=route,formats=formats,filters=filters,steps=steps,read=read,example=example,errors=errors,access=access))

add('SKU Compras: catálogo y maestro','SKU Compras / Catálogo o Maestro de compras','Maestro Excel y catálogo CSV; no es reporte de ventas.',
 'Búsqueda y selección de estado del catálogo; el alcance del maestro descargado puede ser más amplio que la lista visible.',
 ['Actualiza catálogo y busca SKU/descripción; decide si necesitas activos, bajas o el maestro completo.',
  'Usa la descarga del catálogo/maestro y verifica sus columnas y número de registros.',
  'Compara SKU, clasificación, descripción y estado; conserva el archivo con fecha.'],
 'Describe artículos y códigos. No demuestra existencia física, compras recibidas ni costo valorizado de almacén.',
 'Para saber si un material está dado de alta usa el catálogo; para saber cuántos hay usa Existencias/Kárdex.',
 [('Descarga más filas que las visibles','Catálogo filtrado y maestro completo no son lo mismo','Revisar alcance del archivo antes de contar.'),('SKU existe pero stock es cero','Alta no equivale a recepción','Abrir Inventarios con el almacén correcto.'),('Artículo duplicado aparente','Cambio de presentación, estado o clasificación','Revisar SKU y datos antes de unificar.')],
 'Consulta y descarga según módulos del perfil. La edición del catálogo exige el permiso correspondiente.')

add('SKU Ventas: catálogo y maestro','SKU Ventas / Maestro de ventas o Catálogo','Maestro Excel y catálogo CSV.',
 'Consulta por descripción/estado en catálogo; el CSV y maestro pueden descargar el catálogo completo permitido.',
 ['Actualiza el catálogo de ventas y busca el SKU.',
  'Descarga Maestro Excel o catálogo CSV según el dato que necesites conservar.',
  'Valida códigos, descripción, estado, clasificación y agrupación TPV; para precios por empresa consulta Productos/Precios.'],
 'El catálogo de códigos no es el historial de facturas ni la lista de existencias. Un SKU reservado sin ficha puede no estar disponible para vender.',
 'Si buscas precio de un cliente, no lo deduzcas del código: consulta la lista y el cliente de la empresa.',
 [('No aparecen precios esperados','Se descargó catálogo de códigos','Usar la lista/precio comercial de la empresa.'),('No filtra como la pantalla','Exporta universo completo del catálogo','Comparar alcance y estado de los registros.'),('Tiene código pero no vende','Canal, ficha o impuesto pendiente','Completar la ficha, no inventar un reporte de stock.')],
 'Módulo SKU Ventas habilitado. Los permisos de códigos no conceden acceso a carteras ajenas.')

add('Requisiciones: generador y costeo','Reportes de requisición / Generador de reportes','Excel, PDF y detalle CSV; Excel de detalle seleccionado.',
 'Desde/hasta, sucursal, área, solicitante, material, folios y agrupación; impuestos configurados en el reporte.',
 ['Selecciona un reporte guardado o, con permiso, arma uno nuevo con nombre, filtros y agrupación.',
  'Pulsa Ver reporte. Revisa resumen, cantidades por unidad y partidas sin costo/equivalencia.',
  'En Ver requisiciones abre el detalle. Descarga todo el reporte o el detalle seleccionado según el botón usado.'],
 'Costea lo realmente surtido y muestra por separado lo requisitado. Usa COSTO del maestro por unidad de entrega o precio/equivalencia cuando corresponde. Canceladas excluidas del costeo.',
 'Solicitado 10 kg, surtido 6 kg y costo 10: costo de lo surtido 60, no 100. Si falta equivalencia, el total se marca parcial.',
 [('TOTAL PARCIAL','Hay partidas sin costo o equivalencia','Completar maestro y recalcular; no asumir cero.'),('Excel difiere de vista anterior','Exportación recalcula con datos vigentes','Comparar hora/filtros y movimientos nuevos.'),('Cantidad agrupada no es sumable','Se mezclaron unidades','Agrupar por unidad o revisar partidas.')],
 'Editar reportes: Gerencia, AUXTI y Superadministrador según acceso. Consulta respeta almacenes/sucursales autorizados.')

add('Compras: pedidos y recepciones','Compras / Reportes de compras','Exportar Excel y Descargar PDF.',
 'Sucursal, estado, proveedor, fecha de pedido o de entrega prevista, desde y hasta.',
 ['Entra a Reportes de compras y confirma razón social y Sucursal del reporte.',
  'Escoge tipo de fecha, estado y proveedor; pulsa Consultar reporte.',
  'Revisa totales por sucursal, por proveedor y detalle por producto/pedido antes de exportar.'],
 'Borradores, cotizaciones enviadas y cancelados no se suman al importe de pedidos confirmados. Las cantidades conservan su unidad de captura; recibido refleja devoluciones/cancelaciones autorizadas.',
 'Un pedido de 10 cajas con 6 recibidas puede mostrar saldo pendiente aunque la compra ya esté confirmada. Confirma la equivalencia de cada caja.',
 [('Importe menor que lista de documentos','No todos los estados se suman','Comparar confirmados contra borradores/cancelados.'),('Periodo no corresponde','Se filtró entrega en vez de pedido','Elegir el campo de fecha correcto.'),('Cantidades parecen distintas','Compra y entrega usan unidades diferentes','Revisar equivalencia conservada en el Excel.')],
 'Módulo Compras y alcance de empresa/sucursal. Costos y datos se limitan a la autorización de la cuenta.')

add('Inventarios: físico, Kárdex y resumen','Inventarios / Existencias, Kárdex o Resumen','Existencias Excel/PDF; Kárdex y resúmenes con las exportaciones habilitadas, incluida impresión/XML en su vista.',
 'Almacén, SKU, periodo y dirección de movimiento según la vista; resumen general puede reunir almacenes autorizados.',
 ['Para stock actual abre Existencias y elige almacén; para explicar un cambio abre Kárdex.',
  'Filtra SKU, periodo y entradas/salidas. En resumen distingue existencia al corte de existencia actual.',
  'Descarga desde esa vista y comprueba saldo inicial, entradas, salidas y saldo final.'],
 'Inicial + entradas - salidas = saldo al corte. El disponible descuenta reservas, el físico no. Costos requieren permiso. El XML de Kárdex es un reporte de inventario, no un CFDI.',
 'Central 10, Norte 4: traspasar 2 deja Central 8 y tránsito 2; Norte sigue 4 hasta recibir. Un total general no demuestra disponibilidad en Norte.',
 [('Stock actual difiere del corte','Son momentos distintos','Comparar fechas y existencia actual por separado.'),('No aparecen costos','Cuenta no autorizada','Solicitar reporte a responsable autorizado.'),('No cuadra disponibilidad','Reservas o tránsito pendientes','Revisar documentos reservados y recepciones.')],
 'Inventarios habilitado y almacenes asignados; la descarga respeta ocultamiento de costos.')

add('Ventas institucionales y TPV: reportes propios','Pedidos institucionales o TPV / Reportes','Excel, CSV, Descargar PDF e Imprimir; selección de columnas/filas y configuración guardada.',
 'Cliente, producto, tipo de fecha (emisión, pedido o entrega), desde/hasta y estado en el canal seleccionado.',
 ['Abre el canal correcto y entra a Reportes; no mezcles presupuestos/pedidos con tickets TPV.',
  'Aplica filtros y abre Columnas de exportación y selección. Marca filas sólo si quieres exportar un subconjunto.',
  'Sin filas marcadas se exporta todo el resultado filtrado. Guarda configuración cuando tengas el permiso.'],
 'Cancelaciones excluidas del total de ventas. Presupuestos y pedidos se presentan separados. Ticket EMITIDO no significa PAGADO. La impresión no genera otro documento.',
 'Un pedido de 580 no debe presentarse como efectivo cobrado; consulta cobros/CXC o una operación TPV realmente pagada.',
 [('Sólo exporta algunas filas','Hay filas marcadas','Quitar selección para exportar todo el resultado.'),('Reporte de otro canal','Se abrió TPV en vez de institucionales','Entrar al canal de la operación original.'),('Total no equivale al banco','Incluye documentos sin cobro real','Separar estado y clase documental.')],
 'Acceso al canal y a su cartera. Guardar configuraciones depende del permiso; consultar no amplía la cartera.')

add('CRM: tablero, plan y comisiones','Vendedores y CRM / Consultar tablero / Reporte de comisiones','Tablero en pantalla; plan mensual CSV con permiso; comisiones Excel/PDF/CSV para responsables autorizados.',
 'Empresa, vendedor autorizado, desde/hasta y etapa; comisiones con su propio periodo.',
 ['Consulta tablero con la empresa y periodo; revisa qué indicador estás interpretando.',
  'Si tienes acceso al tablero mensual, consulta el plan autorizado sin ampliar clientes de tu cartera.',
  'Gerencia/Superadministrador consultan comisiones por periodo y descargan el formato requerido.'],
 'El indicador Ventas cobradas TPV usa operaciones TPV pagadas. Pedidos hechos, oportunidades e importe de pedidos son indicadores distintos. Comisiones usan la regla guardada por factura: FACTURADO/COBRADO y NETO/BRUTO.',
 'Una nota de crédito disminuye la base que corresponde; no cuenta como dinero cobrado. Reembolsos reducen cobros netos.',
 [('Tablero no muestra CXC pagada','Es indicador TPV, no saldo de factura','Consultar CXC/Ciclo comercial para cobranza.'),('No aparece reporte de comisiones','Privacidad para vendedor','Gerencia/Sistemas realiza la consulta.'),('Plan mensual no está visible','Acceso especial no concedido','Solicitar autorización sin cambiar cartera.')],
 'Vendedor sólo su cartera. Comisiones sólo Gerencia/Superadministrador. El tablero mensual requiere autorización específica.')

add('Ciclo comercial: documentos y cobros','Ciclo comercial / Reportes','Excel, CSV y PDF con filtros y columnas seleccionables.',
 'Empresa, sucursal, almacén, periodo, producto, cliente, tipo, estado documental, surtido/cobro y pendientes de facturar, según contenido.',
 ['Elige Contenido: Documentos comerciales o Cobros y reembolsos.',
  'Para documentos selecciona tipo y estados; para cobranza revisa factura/recibo y periodo de los movimientos.',
  'Abre Columnas del reporte, selecciona datos útiles, consulta y descarga; usa el folio para conciliar con el documento.'],
 'Un reporte por partida repite encabezados. El saldo pertenece a la factura, no debe sumarse por cada SKU. En cobros los créditos no se presentan como efectivo recibido. Se conserva estado de cancelación.',
 'Factura con tres partidas y saldo 100 puede repetir ese 100 en tres renglones: saldo de la factura = 100, no 300.',
 [('Saldo aparentemente triplicado','Se sumó el saldo repetido por partida','Consolidar por factura o usar la cuenta CXC.'),('Remisión ya no está pendiente','Fue facturada total o parcialmente','Consultar pendientes actuales por partida.'),('No devuelve registros','Filtros de tipo y estado incompatibles','Elegir una combinación válida y empresa correcta.')],
 'Carteras del usuario; autorizaciones comerciales y financieras permanecen en Gerencia/Superadministrador.')

add('Producción: órdenes, materiales y costos','Producción / Reportes','Excel, CSV y PDF con contenido y columnas seleccionables; hoja PDF por orden.',
 'Empresa, sucursal, almacén, periodo, producto, estado y pedido relacionado según el reporte.',
 ['Selecciona Contenido: Órdenes y costos, Movimientos, Consumos, Mermas, Lotes o Calidad.',
  'Aplica filtros y selecciona columnas. Órdenes se consulta en pantalla; los detalles específicos se descargan.',
  'Compara plan y real; para un caso individual abre la orden y Hoja PDF con su revisión.'],
 'Órdenes muestra avance y costos si están autorizados. Consumos muestra salida real, no receta planeada. Movimientos incluye surtidos/entradas/salidas y sus inversos. Lotes por etapas considera fabricación final.',
 'Una receta de 28 kg no demuestra consumo de 28: el reporte debe contener el evento real. Estimado 280 y real 300 muestran variación 20.',
 [('No hay detalle al pulsar Consultar','Ese contenido se ofrece por descarga','Usar Excel/CSV/PDF del contenido seleccionado.'),('No aparece costo real','Sin permiso de costos o sin consumo','Revisar permiso y eventos de la orden.'),('Periodo de movimientos difiere de órdenes','Fecha de evento frente a creación de OP','Usar el contenido y periodo que corresponden.')],
 'Permiso Reportes de Producción y alcance de almacén. Costos sólo Gerencia/Superadministrador con permiso de costos.')

add('QualityLite: tablero y registros','Calidad / Panel y filtros del área','Excel, PDF y Exportar registros CSV.',
 'Área/módulo de calidad, estado, código/título, desde y hasta.',
 ['Selecciona el área de Calidad y sus filtros; pulsa Consultar.',
  'Distingue conteos del panel de los registros filtrados y compromisos vencidos.',
  'Exporta el formato requerido y revisa versión, estado, responsable y fechas del registro.'],
 'El panel cuenta registros por área. No representa stock liberado. Una evidencia o una queja pueden estar registradas sin devolución física ni nota de crédito.',
 'Tres inspecciones aprobadas no significan tres entradas a almacén: conciliar cada liberación física en Inventarios.',
 [('Panel y tabla no tienen mismo total','Panel general y tabla filtrada','Comparar área, estado y fechas.'),('Registros de otra área','Selector de módulo incorrecto','Elegir el área real del documento.'),('Compromiso sigue pendiente','Fecha/estado no refleja conclusión','Responsable revisa registro e historial.')],
 'QualityLite es compartido por instalación para cuentas con acceso; no asumir filtro de empresa inexistente en esta vista.')

add('Finanzas: CXP y CXC','Finanzas / Consultar saldos','Exportar CSV del resultado consultado; recibos PDF del ciclo comercial para pagos de facturas.',
 'Libro CXP/CXC, empresa, proveedor/cliente y estado. La tabla muestra fecha y vencimiento.',
 ['Elige libro y empresa, luego tercero y estado; pulsa Consultar saldos.',
  'Revisa Importe, Aplicado, Saldo y moneda. En Ver/registrar pago consulta historial de la cuenta.',
  'Exporta CSV y concilia por referencia, tercero y moneda; para recibo de factura usa su historial en Ciclo comercial.'],
 'Saldos se totalizan por moneda. Créditos, abonos, reembolsos y cancelaciones cambian el saldo según su naturaleza. Este reporte no representa saldo bancario ni stock.',
 'Deuda 696, abonos 300 y crédito 232 dejan 164; si primero se pagó todo, el crédito puede generar saldo a favor.',
 [('Falta una factura en CSV','CSV refleja la consulta actual','Consultar libro, empresa, tercero y estado correctos.'),('Suma incorrecta entre monedas','Se agregaron MXN y USD como iguales','Mantener totales separados.'),('Cuenta cancelada cambia el total','Canceladas no forman deuda vigente','Revisar estado e historial de cancelación.')],
 'CXC: Gerencia/Superadministrador. CXP: también Compras autorizado. Exportación conserva el alcance financiero.')
