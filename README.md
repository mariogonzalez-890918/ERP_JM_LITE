# ERP JM Lite

Base comercial independiente de ERP JM Lite.

Incluye SKU, requisiciones, compras, almacenes y Kárdex, pedidos institucionales, TPV, CRM, Calidad y CXP/CXC. Es un paquete piloto para pruebas; todavía no es una edición comercial certificada.

Consulta ORIGEN.md para el alcance, procedencia y trabajo pendiente. No hay datos ni credenciales de producción. La evaluación de capacidad y cualquier migración se decidirán antes de modificar el servidor existente.

El paquete piloto Windows x64 se distribuye en [Releases](https://github.com/mariogonzalez-890918/ERP_JM_LITE/releases). Descargar y extraer el ZIP completo. En PowerShell como administrador, ejecutar `powershell -NoProfile -ExecutionPolicy Bypass -File .\install_windows.ps1 -OpenFirewall`. Puerto fijo 8098; avisa si está ocupado. Incluye arranque automático y accesos **Detener servicio**, **Iniciar servicio** y **Abrir ERP JM Lite** en la carpeta de instalación y en Inicio.

En **Respaldos → Restaurar respaldo general**, Sistemas puede revisar un ZIP completo y confirmar con contraseña y el texto RESTAURAR TODO. Guarda una copia previa, recupera todos los módulos e invalida las sesiones. Después se ingresa con las credenciales del respaldo. El límite del ZIP es 128 MB y el contenido expandido 1 GB. No utilizar este ZIP en la restauración JSON por módulo.

Windows 11 y Windows 10 tienen prioridad de pruebas; Server 2012 R2 requiere una distribución Legacy aún pendiente. Consulta [instalación, compatibilidad y pruebas](docs/COMERCIALIZACION.md). Producción y la ampliación documental a remisiones/facturas siguen pendientes; el PAC se deja al final y no se simulan timbrados.

## Desarrollo

Instalar requirements-dev.txt. Regenerar interfaz con `node sku/build-server.mjs`. Inicializar únicamente una instalación vacía con `python tools/inicializar.py` y seguir sus instrucciones. No utilizar la carpeta data del servidor productivo.
