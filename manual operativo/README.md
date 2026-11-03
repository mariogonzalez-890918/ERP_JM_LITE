# Manual operativo de ERP JM

Documentación gráfica del piloto **ca0ce1e**, edición documental 1.0 del **3 de noviembre de 2026**. Las pantallas y los ejemplos utilizan datos de demostración; no contienen contraseñas, tokens de activación ni datos de clientes reales.

## Descargar los manuales

| Documento | Extensión | Contenido |
| --- | --- | --- |
| [Manual técnico y del dueño](Manual_Tecnico_y_Dueno_ERP_JM.pdf) | 64 páginas | Instalación, tarea de arranque, red, configuración, permisos, operación, reportes, mantenimiento y recuperación. |
| [Manual del usuario](Manual_Usuario_ERP_JM.pdf) | 60 páginas | Acceso, captura, consultas, entregas, recepción, producción, ventas, cobros, devoluciones y solución de errores. |
| [Previo: flujo completo de funcionamiento](recursos/Flujo_completo_del_ERP.pdf) | 12 hojas | Anexo gráfico incluido al final de ambos manuales. También se puede consultar por separado. |

Cada manual contiene **27 fichas de operación**, guías de las **15 áreas de QualityLite**, **11 fichas de reportes por módulo**, matrices de errores, una matriz de efectos sobre stock/saldos y marcadores para navegación en el lector PDF. El técnico agrega la administración de instalación y una visión gráfica de Sistemas.

## Qué explica el anexo gráfico

1. Arranque, configuración, contratación y permisos.
2. Catálogos, SKU, impuestos y cargas.
3. Compras, recepción física y cuentas por pagar.
4. Producción, consumo real, recepción y costo del terminado.
5. Traspasos, tránsito, multialmacén y multiempresa.
6. CRM, presupuestos, pedidos, reservas y faltantes.
7. Remisión, factura comercial, cobro y saldo.
8. Devolución del cliente, Cuarentena, crédito y reembolso.
9. Calidad, rechazo, merma, sobrantes y reproceso.
10. TPV, impresión, imágenes y consultas.
11. Modificaciones, dependencias y cancelaciones auditadas.
12. Respaldo, restauración y conciliación del ejemplo completo.

El ejemplo numérico sigue la compra de 100 kg de material, la fabricación de 14 piezas, los traslados entre Central y Norte, la entrega de 6 piezas, facturación/cobro y devolución de 2. Indica qué almacén cambia y qué saldo financiero cambia en cada etapa.

## Alcance real de esta versión

- El PAC está pendiente: las facturas y notas son comerciales, sin UUID ni XML certificado ni complementos fiscales de pago.
- La interfaz TPV visible abre sesiones de emisión de tickets. Un ticket emitido no registra por sí solo cobro ni salida automática de Kárdex.
- Una nota de crédito no acredita recepción física de mercancía; un registro de Calidad no mueve stock por sí solo.
- QualityLite es un repositorio compartido por instalación para quienes tienen acceso al módulo. No se documenta un filtro de empresa inexistente en esa vista.
- El instalador configura la tarea `ERP-JM-Lite`; no se describe como un servicio nativo de Windows. El objetivo de compatibilidad no equivale a certificación de toda la matriz Windows.
- Los permisos y los botones disponibles dependen de contratación, perfil y alcance. Las capturas de Sistemas no conceden esas funciones a todos los usuarios.

## Reproducir la documentación

Las fuentes están en [`fuente`](fuente), y las capturas/diagramas usados están en [`recursos`](recursos). Se conserva el material necesario para reconstruir los PDF sin depender de datos operativos ni de una sesión activa del ERP.

Con Python y las dependencias de `fuente/requirements.txt`, desde la raíz del repositorio:

```powershell
python "manual operativo/fuente/graficos_base.py"
python "manual operativo/fuente/flujo_completo.py"
python "manual operativo/fuente/construir_manuales.py"
```

El generador comprueba límites de contenido para evitar desbordamientos y ensambla los anexos al final. La revisión de entrega incluye renderizado de todas las páginas y controles de texto, integridad y paginación. El manifiesto registra páginas y SHA256 de cada PDF publicado.

Actualizar estos manuales cuando cambien pantallas, reglas, permisos o estados. Los ejemplos explican el funcionamiento del software; no sustituyen las decisiones fiscales, contables o de autorización de la empresa.
