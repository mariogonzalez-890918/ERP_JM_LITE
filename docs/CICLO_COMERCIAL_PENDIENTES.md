# Ampliaciones solicitadas: conservar los módulos actuales

Orden de trabajo: entregar primero el piloto instalable corregido; ampliar el
ciclo documental y Producción reutilizando catálogos, usuarios, permisos,
empresas, almacenes, valuación y Kárdex. Integración PAC al final, sólo estudio
de opciones durante esta entrega.

Ya existen presupuestos/pedidos comerciales, precios, partidas, descuentos,
impuestos, condiciones, impresión, cobros TPV, CRM con carteras, CXP/CXC,
compras con recepción y devolución, y diario inmutable de inventarios.
No presentar esos procesos como remisión física o factura fiscal.

Pendientes del ciclo ampliado:

- Convertir cotización a pedido conservando referencia y sin recaptura; folios
  y estados separados por empresa, responsables, vigencia y autorizaciones.
- Reservas lógicas, disponibilidad y faltantes por almacén sin modificar físico.
- Remisiones parciales que descuenten únicamente lo entregado. Evitar duplicar
  salida al volver a enviar o al facturar; consultar pendientes por partida.
- Facturas comerciales desde pedido/remisión, consolidación compatible,
  cantidades pendientes de facturar, datos fiscales y estado pendiente de timbrado.
- Aplicación de cobros parciales a facturas, recibos y vencimientos reutilizando
  CXC y sus controles existentes.
- Notas de crédito separadas de las devoluciones físicas. Solamente la devolución
  autorizada recibida genera entrada de inventario; nunca borrar el diario.
- Producción opcional por empresa: métodos de fabricación configurables, recetas
  versionadas/multinivel y alternativas, detección de ciclos y explosionado.
- Planeación y reservas sin movimientos; consumo real, fabricación y recepción
  parcial con trazabilidad, lotes, merma, reproceso y controles de Calidad opcionales.
- Costos estimados/reales con materiales, indirectos y mano de obra, usando el
  promedio del Kárdex actual. Unidades compatibles y equivalencias explícitas.
- Series, folios, tolerancias, permisos y almacenes configurados por empresa;
  PDF de la hoja y reportes filtrables de documentos, saldos, producción y costos.

Ver [diseño de Producción](PRODUCCION_DISENO.md) y [estudio PAC](PAC_OPCIONES.md).
El diseño se amplía con consumos y recepciones parciales: la primera propuesta
de cierre único no cubre el alcance posterior del propietario.

Escenarios de aceptación pendientes: venta sin producción; venta con fabricación
del faltante; fabricación para stock; producción parcial; nota de crédito con
devolución física diferenciada; empresa comercializadora sin recetas ni órdenes
de producción. Todas las confirmaciones de stock deberán ser transaccionales,
sin movimientos duplicados y con inversos auditados en cancelaciones.
