# Producción: flujo propuesto y criterios de implementación

Estado: análisis del flujo. No representa funcionalidades ya habilitadas.

## Objetivo operativo

Capturar una receta del producto A, indicar cuántas unidades se van a fabricar,
consultar el explosionado y faltantes, surtir materiales a Producción, registrar
lo realmente consumido y recibir el resultado. La hoja de producción reúne
cantidades, costos y movimientos con un folio estable y PDF.

## Almacenes por empresa y sucursal

Cada almacén debe tener nombre configurable y función: General/materiales,
Producción, Producto terminado (PT) o Cuarentena. No crear nombres de empresas,
sucursales o almacenes de muestra. Una sucursal puede tener varios almacenes.
La función no sustituye los permisos ni la razón social del almacén.

El esquema actual de Inventarios impone un almacén por empresa/sucursal mediante
UNIQUE(company,branch). Es necesario migrar esa restricción, conservando los IDs,
existencias, ciclos, movimientos y referencias actuales. El almacén existente
queda como predeterminado; los nuevos se agregan mediante configuración.
Recepciones, requisiciones y traspasos deben conservar su destino anterior.

La producción de una orden pertenece a una sola empresa. El movimiento entre
empresas se resuelve mediante el traspaso multiempresa existente, con su propia
salida y recepción, antes de surtir la orden.

## Recetas y explosionado

- Producto de salida: SKU de venta inventariable, unidad controlada y cantidad
  base de rendimiento mayor que cero. No fabricar servicios.
- Componentes: SKU inventariables de compra o semielaborados, cantidad y unidad
  de inventario. No convertir kilogramos a piezas sin una equivalencia explícita.
- Recetas versionadas y activas/inactivas. Guardar la versión completa dentro de
  la orden; una edición posterior no cambia órdenes emitidas.
- Requerimiento = cantidad solicitada / rendimiento base × cantidad de receta.
  Mostrar requerido, disponible, reservado y faltante por componente y almacén.
- Permitir receta de varios niveles con detección de ciclos. Los semielaborados
  disponibles se consumen como tales; fabricar sus faltantes mediante órdenes
  vinculadas, evitando descontar sus componentes dos veces.
- Mostrar costo estimado con promedio actual y fecha de cálculo. Si falta costo
  o conversión, señalarlo y bloquear la confirmación correspondiente.
- Layout de recetas con producto, versión, rendimiento, componente, cantidad y
  unidad; revisión de errores antes de aplicar, sin alta implícita de catálogos.

## Orden y hoja de producción

Flujo: Borrador → Planeada → Surtida → En proceso → Terminada.
La liberación de Calidad es un movimiento posterior cuando hay cuarentena.

1. Seleccionar empresa, sucursal, producto, receta, cantidad, fechas y responsable.
2. Revisar explosionado, costo estimado y faltantes. Planear reserva materiales;
   la reserva reduce disponibilidad, no el físico ni el valor del Kárdex.
3. Surtir del almacén de materiales al de Producción. Registrar salida y entrada
   vinculadas; la mercancía conserva su valor. Puede haber surtidos parciales.
4. Capturar consumo real, devoluciones de material sin consumir, merma y unidades
   obtenidas. No confundir material surtido con material consumido.
5. Cerrar con consumos y entradas definitivas, liberando reservas pendientes.
   El producto va a PT o Cuarentena según su configuración y control de Calidad.

La hoja muestra plan y real por separado, lote, materiales surtidos/consumidos/
devueltos, merma con motivo, avance, resultado, usuarios, fechas y referencias
del Kárdex. Cada registro actualiza la vista; el PDF reproduce el estado guardado
y su fecha. Un PDF anterior no se sobrescribe como si fuera el nuevo estado.

Folios por empresa, sucursal y serie: prefijo, consecutivo siguiente, longitud
y cambio opcional por ejercicio. Sólo Gerencia y Superadministrador configuran;
asignación transaccional al emitir, nunca reutilizar un folio cancelado ni
permitir retroceder a uno utilizado. El borrador usa ID interno sin gastar folio.

## Costeo y movimientos

- Surtido: traspaso Materiales → Producción, sin generar gasto ni nuevo costo.
- Consumo: salida de Producción a la orden, valuada al costo promedio vigente.
- Devolución sin consumo: Producción → Materiales, conservando el valor transferido.
- Producto terminado: entrada a PT/Cuarentena con costo real de la orden.
- Merma normal: queda identificada y su costo se absorbe en el rendimiento útil.
  Merma extraordinaria: pérdida separada con autorización y motivo. No descontar
  el mismo material como consumo y nuevamente como merma.
- Costo distribuible = material consumido + cargos de fabricación autorizados
  − recuperaciones valorizadas − pérdida extraordinaria. No incluir impuestos
  recuperables en el costo de forma automática.
- Costo unitario = costo distribuible / unidades útiles obtenidas. Sin unidades
  útiles, resolver como pérdida autorizada; nunca dividir entre cero.
- PT y cuarentena participan en el mismo reparto de costo por unidad de la orden.
  Cuarentena no está disponible para venta, surtido ni TPV.
- Liberación: traspaso Cuarentena → PT por Calidad autorizado, sin nuevo costeo.
  Rechazo: devolución controlada a reproceso o merma; conservar lote y referencia.
- La devolución posterior de PT se registra con referencia a la orden/movimiento;
  no borrar ni modificar el diario. Si ya se vendió o trasladó, impedir una
  reversión que deje existencias negativas.

El registro de fabricación es único por evento. Confirmar dos veces no duplica
movimientos. Materiales, costo y entrada de producto se aplican en una única
transacción SQLite. Ante un error se revierte todo el evento. Respetar el ciclo
de inventario: no revertir una orden histórica dentro de un ciclo diferente.

## Permisos y comprobaciones antes de habilitar

Producción será módulo contratable y con permisos explícitos por perfil.
Almacén surte/recibe; Producción captura avances; Calidad libera cuarentena;
Gerencia/Superadministrador autorizan ajustes, cancelaciones y pérdidas. Los
costos siguen los permisos de Inventarios y nunca se filtran a ventas restringidas.

Probar con bases aisladas: migración de almacenes sin perder datos; recetas
cíclicas; unidades incompatibles; faltantes y reservas simultáneas; surtido
parcial; doble confirmación; fallo entre salida y entrada; rendimiento distinto
al previsto; merma total; devoluciones; cuarentena bloqueada para venta;
liberación parcial; aislamiento entre empresas; folios concurrentes; PDF con
datos reales de la hoja; restauración general que conserve toda la trazabilidad.

Las pruebas no deben crear producción ni cambiar existencias de la instalación
real. El módulo se habilita después de completar estas verificaciones.
