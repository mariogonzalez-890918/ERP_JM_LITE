# Ciclo comercial integrado

Actualizado el 3 de noviembre de 2026. Se amplían los documentos comerciales existentes; no se sustituyen CRM, catálogos ni CXC.

## Operación

Desde Ventas institucionales → Remisiones, facturas y cobros, o Menú de aplicaciones → Ciclo comercial.

1. Capturar presupuesto con cliente, empresa, partidas, descuentos, impuestos, condiciones, vigencia, moneda y tipo de cambio. Gerencia puede aprobar o rechazar. La configuración por empresa determina si la aprobación es obligatoria.
2. Convertir a pedido conserva el presupuesto y genera folio independiente. La confirmación y reserva lógica no modifican el físico ni el Kárdex. Disponibilidad muestra faltantes por almacén; el usuario decide si solicita compra o fabrica.
3. Generar una o varias remisiones con cantidades efectivamente entregadas, almacén, persona que preparó y autorizador. Cada confirmación genera una sola salida física. Las reservas sobrantes se reducen conforme al pendiente.
4. Facturar cantidades pendientes de una o varias remisiones compatibles. La opción de facturar directamente pedidos requiere configuración por empresa. Se valida empresa, cliente, moneda, tipo de cambio y cantidad previamente facturada. La factura crea una cuenta en CXC y nunca vuelve a descontar una remisión.
5. Registrar cobros parciales o totales, fecha, referencia y forma; consultar saldo, vencimiento, reembolsos y recibo PDF. Son registros internos, sin conexión bancaria. Cancelar un cobro conserva su registro y revisa dependencias.
6. La nota de crédito ajusta el saldo sin entrada de inventario. La devolución física se captura desde la remisión y produce una entrada real; los productos sin aprobación se reciben en Cuarentena, Devoluciones o Merma.

Series y folios por empresa, con control de consecutivos y reutilización prohibida. Los documentos e importes anteriores conservan sus versiones. Cancelar documentos físicos genera movimientos inversos auditados y exige resolver los documentos dependientes.

## Permisos y reportes

Cada vendedor consulta únicamente su cartera. Gerencia y Superadministrador autorizan remisiones, facturas, créditos, devoluciones y movimientos financieros. La asignación de clientes y las comisiones conservan los controles existentes. El perfil de captura restringida no puede cambiar precios autorizados ni su moneda MXN.

Reportes Excel, CSV y PDF por empresa, sucursal, almacén, periodo, producto, cliente y estados aplicables; columnas seleccionables. Incluyen documentos, pendientes de surtido/facturación, saldos y cobros/reembolsos. Los créditos no se cuentan como efectivo cobrado para comisiones. Los reportes por partida repiten los datos del documento; el saldo corresponde a la factura, no debe sumarse entre sus partidas.

## Fiscal y comunicación

Catálogos de régimen, uso, forma, método y moneda extraídos del XLS oficial SAT de 29 de octubre de 2026, con descripciones, vigencias y compatibilidad entre régimen/uso/tipo de persona. La validación definitiva del contribuyente y CFDI corresponde al PAC.

Por instrucción del propietario, PAC queda al final: sin timbrado, UUID, XML certificado, CFDI de egreso ni complemento de pago. Facturas y notas se identifican como documentos comerciales pendientes de timbrado. La opción XML informa esta condición; no fabrica certificados.

Preparar correo descarga un EML con destinatario, asunto y PDF adjunto para abrir en el cliente de correo. No envía mensajes ni incorpora credenciales SMTP.

## Validación

Pruebas aisladas de venta sin Producción, fabricación bajo pedido, remisiones y recepciones parciales, consolidación, cobros, reembolsos, créditos, devolución física, doble envío, permisos, reversión transaccional y restauración general. Las pruebas nunca operan la base de la instalación del cliente.
