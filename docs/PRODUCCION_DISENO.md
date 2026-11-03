# Producción configurable

Actualizado el 3 de noviembre de 2026. Producción es opcional por empresa y módulo contratado; una empresa comercial puede vender sin fabricaciones.

## Preparación

Superadministrador habilita Producción e Inventarios en los perfiles autorizados y sus accesos de empresa/sucursal/almacén. En Inventarios se crean los almacenes necesarios con nombre libre y función General, Producción, PT, Cuarentena, Merma o Devoluciones. No se agregan sucursales ni almacenes de ejemplo.

En Producción → Configuración se eligen almacenes de materiales, consumo, PT, Cuarentena, Merma y alternativos; métodos, autorización, parcialidades, lotes, etapas, tolerancias, redondeo, calidad, criterios de aceptación/rechazo, costos y permisos individuales. Sólo Gerencia/Superadministrador configuran, autorizan, cancelan y consultan costos. El resto de los permisos es independiente. Se conservan accesos por empresa/sucursal.

Métodos seleccionables: discreta, lotes, bajo pedido, inventario, ensamble, subensambles, procesos y etapas. Las etapas se definen en orden y no pueden avanzar más de lo aprobado en la etapa previa. Los métodos comparten el flujo de movimientos y la valuación existente; no son motores industriales separados.

## Recetas y planeación

Recetas de producto terminado o subensamble, con versiones, vigencia, rendimiento base, instrucciones, componentes, unidad de consumo, factor explícito a inventario, merma prevista, alternativas compatibles y subrecetas. El rendimiento y la cantidad de la orden se expresan en la unidad de inventario del producto; las unidades de compra conservan las conversiones existentes de Compras. No se convierten piezas a kilos implícitamente.

Una orden conserva una copia de su receta y configuración técnica. Nuevas versiones no alteran documentos anteriores. El explosionado multinivel detecta ciclos y calcula requerimiento, físico, reserva, disponible, faltante y costo estimado. Distribuye disponibilidad compartida para no contar dos veces la misma materia prima entre niveles. La planeación no modifica el Kárdex.

El layout Excel/CSV de recetas se revisa antes de aplicar. Se validan catálogos, equivalencias y dependencias; aplicar exige la huella del archivo y catálogo revisados. No crea productos implícitos. Los subensambles faltantes se fabrican mediante sus propias órdenes y se reciben antes del consumo de la orden superior.

## Flujo real

1. Emitir orden manual para inventario o desde el faltante de un pedido. Se puede elegir cantidad capturada, todo el pendiente no programado o faltante recalculado. Se restan órdenes pendientes del mismo pedido/producto para evitar duplicar producción.
2. Autorizar asigna folio por empresa/sucursal y reserva materiales disponibles. No realiza salida física.
3. Surtir materiales mueve existencias de materiales a Producción con igual costo. Admitir parcialidades y devolver sobrantes sin consumir.
4. Registrar consumo real descuenta del almacén de Producción. Sustituciones requieren alternativas de la receta; consumos y rendimientos fuera de tolerancia requieren autorización y motivo. La merma indicada forma parte de la cantidad consumida, no se descuenta dos veces.
5. Registrar fabricación, rechazos, lote, fechas, caducidad y etapas. Las inspecciones opcionales de MP/proceso/PT impiden saltar sus controles. Un nuevo surtido, consumo o fabricación invalida el dictamen correspondiente.
6. Recibir cantidad fabricada pendiente en General/PT o Cuarentena. Sin aprobación de PT, la recepción sólo puede ir a Cuarentena; su liberación se realiza con la operación existente de Inventarios. La recepción puede ser parcial o por lote.
7. Cerrar exige resolver producción fabricada y costos pendientes; un cierre parcial requiere motivo. Cancelar genera inversos auditados en orden contrario y se bloquea si el stock ya no permite devolver o cambió el ciclo de almacén.

## Costos y documentos

Se reutiliza el costo promedio de Inventarios. Costos reales de consumos, mano de obra, indirectos y adicionales se asignan a las recepciones; pérdidas extraordinarias autorizadas se separan. La merma física se conserva a costo cero para evitar duplicar el valor absorbido por PT. Se registra el ajuste de redondeo a seis decimales. Sólo Gerencia puede cerrar anticipadamente un lote de costos.

La hoja PDF incluye empresa/logo, folio, revisión, receta, plan/real, consumos, costos según permiso, usuarios, fechas y movimientos. Cada descarga representa el estado consultado, sin modificar PDFs previamente descargados.

Reportes con filtros y columnas seleccionables: órdenes/costos/variación, movimientos, consumos, mermas/pérdidas, lotes y calidad, en Excel/CSV/PDF. Existencias de MP y PT, disponibilidad y Kárdex se consultan en Inventarios para conservar una sola fuente de saldos.

La copia general incluye recetas, órdenes, eventos, reservas, configuraciones y Kárdex. La restauración admite estructuras anteriores conocidas mediante migración en la copia temporal; rechaza otros cambios de esquema.

## Límites del piloto

El cierre de Producción no timbra facturas ni registra operaciones bancarias. No hay rutas industriales independientes, programación de máquinas, nómina ni MRP automático. El catálogo de métodos configura el mismo flujo de fabricación. PAC se mantiene pendiente por instrucción del propietario. Falta certificar la instalación en toda la matriz Windows y realizar pruebas de carga de la operación real.
