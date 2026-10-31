# ERP JM Lite

Base comercial independiente de ERP JM Lite.

Incluye SKU, requisiciones, compras, almacenes y Kárdex, pedidos institucionales y expendios. Esta primera copia mantiene la arquitectura y reglas de la aplicación de origen; aún no es una edición comercial terminada.

Consulta ORIGEN.md para el alcance, procedencia y trabajo pendiente. No hay datos ni credenciales de producción. La evaluación de capacidad y cualquier migración se decidirán antes de modificar el servidor existente.

Se está preparando un paquete piloto Windows x64 con instalación, puerto web configurable, arranque automático e interfaz comercial JM. Consulta [instalación, compatibilidad y pruebas](docs/COMERCIALIZACION.md). Windows 11 y Windows 10 tienen prioridad de pruebas; Server 2012 R2 requiere una distribución Legacy aún pendiente. El paquete no está certificado para venta.

## Desarrollo

Instalar requirements-dev.txt. Regenerar interfaz con `node sku/build-server.mjs`. Inicializar únicamente una instalación vacía con `python tools/inicializar.py` y seguir sus instrucciones. No utilizar la carpeta data del servidor productivo.
