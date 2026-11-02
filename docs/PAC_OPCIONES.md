# Opciones de integración fiscal: estudio preliminar

Consulta: 1 de noviembre de 2026. Por instrucción del propietario, el PAC se
integra al final. Este estudio no contrata servicios, no envía certificados y
no habilita ni simula timbrados.

| Opción | Información publicada por el proveedor | Qué validar para este ERP |
| --- | --- | --- |
| Facturama API Multiemisor | REST, múltiples RFC, sandbox, consulta/cancelación y descarga XML/PDF. Publica una suscripción anual de $1,650 MXN con 100 folios incluidos; confirmar impuestos y tarifa vigente al contratar. | Licencia de distribución comercial, manejo de CSD por empresa, volumen de timbres y costo adicional. [Información oficial](https://api.facturama.mx/), [colecciones oficiales](https://github.com/Facturama/facturama-api-collections). |
| SW | Documentación de timbrado, cancelaciones, retenciones, ejemplos CFDI y ambiente de pruebas. | Cotización por volumen, número de emisores, custodia de CSD, autenticación y soporte. [Centro oficial de integración](https://developers.sw.com.mx/). |
| Finkok | Web services que reciben XML y devuelven el XML procesado; ofrece modalidad de cobro por documentos emitidos. | Cotización, cuenta de pruebas, alta de RFC, sellado local, cancelaciones y recuperación de solicitudes. [Sitio oficial](https://www.finkok.com/). |

La autorización vigente se verifica por razón social del certificador en el
[directorio del SAT](https://wwwmat.sat.gob.mx/aplicacion/30796/proveedor-de-certificacion-de-factura-electronica-).
No equiparar automáticamente una marca comercial o intermediario con la razón
social autorizada. Los precios y condiciones no constituyen una cotización.

Antes de elegir: probar con emisores de ejemplo, comprobantes de ingreso y egreso,
complementos de pago, cancelación con motivos y sustitución, consulta de estado,
recuperación después de timeout, acuses y descarga posterior. Confirmar que el
mismo envío no genere dos UUID. La selección debe considerar timbres, renovaciones,
cancelaciones, soporte y la licencia para operar varias empresas.

El ERP conservará un estado comercial separado del fiscal. Un documento pendiente
no debe presentar UUID, sello o XML como si estuviera certificado. Certificados y
credenciales se configuran por emisor, fuera del código y de Git; el proveedor
no debe exigir cambiar el Kárdex ni duplicar catálogos o documentos comerciales.

Las tasas negativas de retención son una convención interna solicitada para
restar importes. La futura serialización fiscal deberá separar traslados y
retenciones y validar sus importes conforme al estándar, sin copiar el signo de
pantalla directamente al XML. [Guía publicada por el SAT](https://www.sat.gob.mx/cs/Satellite?blobcol=urldata&blobkey=id&blobtable=MungoBlobs&blobwhere=1461175754221&ssbinary=true).
