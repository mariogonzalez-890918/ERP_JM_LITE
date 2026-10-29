# ERP JM Lite

Base independiente para la futura edición comercial del ERP, derivada de GMP ERP 3.1.8.

Incluye SKU, requisiciones, compras, almacenes y Kárdex, pedidos institucionales y expendios. Esta primera copia mantiene la arquitectura y reglas de la aplicación de origen; aún no es una edición comercial terminada.

Consulta ORIGEN.md para el alcance, procedencia y trabajo pendiente. No hay datos ni credenciales de producción. La evaluación de capacidad y cualquier migración se decidirán antes de modificar el servidor existente.

## Desarrollo

Instalar requirements-dev.txt. Regenerar interfaz con `node sku/build-server.mjs`. Inicializar únicamente una instalación vacía con `python tools/inicializar.py` y seguir sus instrucciones. No utilizar la carpeta data del servidor productivo.
