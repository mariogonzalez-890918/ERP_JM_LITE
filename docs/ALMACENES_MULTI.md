# Almacenes por empresa y sucursal

En **Almacenes e inventarios**, selecciona un destino y usa **Agregar almacén**. Sólo Gerencia y Superadministrador pueden configurar nombres y funciones. Se permite más de un almacén por sucursal; un nombre no se repite dentro de la misma razón social/sucursal. Se pueden repetir nombres en empresas distintas.

La función identifica General, Materias primas, Producción, Producto terminado, Cuarentena, Merma o Devoluciones. No se crean empresas, sucursales ni almacenes de ejemplo. El almacén existente conserva su ID, existencias, ciclos, costos y movimientos. Los nuevos requieren su inventario inicial autorizado; no se presume que las celdas vacías equivalen a cero.

**Editar almacén** conserva su empresa y sucursal. El nombre puede cambiar; la función no se cambia si hay existencias. Los permisos por empresa y sucursal se siguen asignando en Compras → Accesos.

Las recepciones de Compras mantienen su destino anterior. Los pedidos pendientes y las recepciones no se duplican en todos los almacenes de la sucursal. Para trasladar mercancía a otro almacén se usa el traspaso existente con salida y recepción. El indicador multiempresa compara razones sociales, sin depender del formato del ID del almacén.

En **Cuarentena**, las salidas ordinarias, ajustes negativos y traspasos de salida quedan bloqueados. Para liberar: selecciona el almacén → **Liberar Cuarentena** → elige General o PT de la misma empresa → registra producto, cantidad aprobada, responsable de Calidad y motivo. Gerencia o Superadministrador confirma. Se comprueba existencia y se registra una salida y una entrada al mismo costo, en una sola transacción. No se habilitan negativos para esta operación. Repetir el envío no duplica movimientos. Una liberación entre empresas requiere primero el proceso de liberación en origen y después un traspaso multiempresa separado.

El Kárdex y sus exportaciones identifican el nombre del almacén junto con sucursal y razón social. Los costos conservan los permisos previos. El respaldo general contiene nombres, funciones y movimientos; se admite el esquema anterior de un almacén por sucursal mediante una adaptación validada sólo en la copia temporal, sin aceptar otras diferencias de estructura.

Esta ampliación prepara los almacenes para fabricación. Las recetas, explosionado, consumo contra orden, recepción de PT costeada y hojas de producción siguen pendientes; no se presentan como funcionalidad terminada.
