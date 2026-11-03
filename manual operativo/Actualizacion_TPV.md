# TPV, inventario y preparación de factura global

Esta actualización sustituye la descripción del TPV del piloto `ca0ce1e` en los manuales PDF. Se aplica a las notas emitidas con la versión que incluye este cambio.

1. En **TPV → Ajustes TPV / Factura global**, selecciona la razón social y sucursal. Selecciona el almacén General o de Producto Terminado. Debe tener un inventario inicial autorizado y existencias disponibles.
2. Emite la nota. Cada producto descuenta del almacén seleccionado y aparece en Kárdex con su folio. Los servicios no mueven inventario. Si falta existencia, se rechaza toda la nota.
3. En **Ventas y tickets**, registra el cobro real mientras la caja original siga abierta. Selecciona efectivo, transferencia, tarjeta de crédito o débito. El cobro no vuelve a descontar mercancía.
4. Para cancelar una nota, solicita la cancelación y confirma el regreso físico con el responsable autorizado. La aprobación registra una entrada al almacén original con el costo de la salida. Las notas históricas que nunca descontaron inventario no generan una entrada artificial. Si hubo cobro, registra el reembolso por separado.
5. Gerencia o Superadministrador pueden habilitar **Factura global** por razón social y sucursal. Captura el CP de expedición, régimen fiscal y serie. En las notas nuevas, el ticket conserva los datos del emisor y el CP de expedición.
6. Revisa un día, una semana de siete días dentro del mes o un mes cerrado. Consulta las notas excluidas antes de confirmar. La preparación guarda los folios e impuestos, evita repetir notas y permite descargar PDF y JSON. Los casos con pagos parciales o diferidos, retenciones, clientes nominativos e impuestos no contemplados requieren revisión fiscal fuera de esta preparación.

La regla 2.7.1.21 prevé el desglose de IVA e IEPS y un plazo ordinario de 24 horas desde el cierre. El ERP identifica períodos fuera de ese plazo. La preparación queda **pendiente de timbrado** y el PAC se mantiene para la etapa fiscal posterior. [RMF 2026, regla 2.7.1.21](https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/documentos2026/rmf/rmf/RMF_2026-DOF-28122025.pdf#page=108) · [Guías del SAT para CFDI 4.0](https://www.sat.gob.mx/minisitio/Factura/emite_materialdeayudaparafactura.htm)

| Situación | Acción |
| --- | --- |
| Falta existencia o conteo inicial | Revisa la bodega y el saldo disponible. Registra el conteo o un traspaso físico antes de emitir. |
| La nota forma parte de una global | Cancela primero la preparación local. El CFDI timbrado requiere el proceso fiscal de cancelación. |
| La nota aparece excluida | Revisa el motivo por folio. Una nota emitida sin cobro real queda pendiente. |
| Cambió el ciclo de inventario | Sistemas debe conciliar el regreso. El ERP bloquea la entrada automática de otro ciclo. |
| Recuperación de datos | Usa el respaldo general para recuperar juntos notas, preparaciones, ajustes de sucursal y Kárdex. |
