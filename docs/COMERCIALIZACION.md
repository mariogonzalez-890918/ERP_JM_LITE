# ERP JM Lite: base comercial instalable

Estado: paquete piloto 0.1.0-dev. Producto independiente de GMP ERP. No se han conectado ni copiado sus bases, credenciales o maestros.

## Arquitectura y acceso

Servidor web Python x64 con SQLite en disco local del servidor. El ejecutable incorpora Python, SQLite, ReportLab, Pillow y las bibliotecas nativas recogidas por PyInstaller. El paquete agrega Microsoft Visual C++ x64; no se requiere un compilador C++. Los clientes usan un navegador moderno y se conectan a `http://SERVIDOR:PUERTO`. No requieren instalar Python, Office, SQLite ni C++.

La instalación pide un puerto entre 1 y 65535. Debe reservarse un puerto fijo para que los usuarios conserven su dirección al reiniciar. Para pruebas, `--port 0` permite al sistema operativo elegir uno libre; el servidor informa el puerto real. Las direcciones de la interfaz son relativas y siguen el puerto usado para abrir la aplicación.

## Instalación y arranque automático

Extraer todo `ERP_JM_Lite_Windows_Piloto.zip` y ejecutar PowerShell como administrador:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_windows.ps1 -Port 8090 -OpenFirewall
```

Se verifica el manifiesto SHA256 y la firma Microsoft del redistribuible. El programa se instala en `Program Files\ERP JM Lite`; la configuración, las bases y los registros quedan en `ProgramData\ERP JM Lite`, con acceso a SYSTEM y Administradores. La tarea `ERP-JM-Lite` ejecuta el servidor al iniciar Windows con la cuenta SYSTEM y sin sesión de usuario. Ante fallos intenta reiniciar hasta cinco veces, cada minuto. Evita instancias duplicadas. El navegador puede minimizarse o cerrarse: no controla la vida del servidor.

La regla opcional de firewall acepta el puerto solamente en perfiles Privado/Dominio y desde la subred local. Redes adicionales requieren ampliar expresamente ese alcance. La instalación comprueba HTTP antes de informar éxito. Los registros de la ejecución actual y anterior quedan en `ProgramData\ERP JM Lite\logs`.

## Administrador

La cuenta permanente es **Mario González**, `mario.gonzalez@jad-ayt.com`, con perfil superadministrador. No puede desactivarse ni degradarse; AUXTI no puede modificarla. La inicialización solicita la contraseña oculta. Solo se guarda un hash PBKDF2-SHA256 con sal aleatoria; reinstalar no cambia la contraseña existente. No existe una contraseña comercial universal dentro del código, del EXE o del ZIP.

Para automatización de instalaciones nuevas, `--initialize --admin-seed ARCHIVO` admite exclusivamente sal/hash válidos. El archivo es privado, queda fuera de la distribución y debe retirarse tras provisionar. No sustituye contraseñas de usuarios existentes. La clave solicitada por Mario se preparó únicamente en los datos locales excluidos de Git.

## Matriz de sistemas

| Plataforma x64 | Objetivo | Estado |
|---|---|---|
| Windows 11 | Primera VM de pruebas | Ver registros del laboratorio; no inferir aprobación por crear el disco |
| Windows 10 | Segunda VM de pruebas | Pendiente |
| Server 2016, 2019, 2022, 2025 | Paquete moderno | Pendiente de pruebas por sistema |
| Server 2012 R2 | Paquete Legacy independiente | Pendiente de definir runtime, bibliotecas y certificación; el instalador moderno lo rechaza |

Microsoft limita el runtime v14 actual a Windows 10/11 y Server 2016/2019/2022/2025. No basta con agregar un redistribuible antiguo a este EXE para certificar Server 2012 R2. Fuente: [sistemas del redistribuible C++](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/).

## Pruebas de Windows

`verify_windows.ps1 -BeforeReboot` verifica tarea y web y registra el arranque actual. Después de reiniciar, `verify_windows.ps1` exige una fecha nueva de arranque de Windows y una ejecución posterior de la tarea. No declara éxito si solamente se reinició el proceso.

`create_windows_lab.ps1` requiere privilegios de administrador y una ISO oficial Enterprise de evaluación. Crea un VHDX nuevo, aplica Windows únicamente al disco virtual verificado y monta una VM de generación 2 con TPM virtual, 2 CPU y memoria dinámica (4 GB iniciales). Usa una red interna sin puente, NAT o acceso a servidores empresariales. No modifica VMs existentes ni reinicia el anfitrión. Las credenciales del sistema invitado son aleatorias y se guardan cifradas por Windows para el usuario del laboratorio.

La automatización instala el paquete en la VM, registra una comprobación inicial, reinicia exclusivamente la VM y comprueba el arranque automático y el acceso web desde el anfitrión. Solo `result.txt` con PASS confirma el recorrido completo. `lab-error.txt` y los registros conservan fallos. Una descarga o compilación terminada no acredita compatibilidad.

## Interfaz

Identidad JM propia: navegación azul, formularios y tablas compactos, cabeceras de documentos y logotipo vectorial. No incorpora vistas ni código de Odoo, SAP, Oracle o Aspel. Se conserva la lógica y las rutas de los módulos existentes. Los identificadores internos heredados no son la marca del producto.

## Pendientes antes de vender

Probar cada sistema de la matriz, instalación/actualización/desinstalación, recuperación desde respaldo, navegadores y flujos completos; generalizar sucursales y parámetros heredados; configurar cada empresa; integrar HTTPS y licenciamiento; firmar el paquete propio y revisar las licencias de redistribución; ejecutar carga de 40–50 usuarios y decidir con evidencia si SQLite es suficiente. No se han certificado esos puntos ni migrado bases.

## Compilación

En Python Windows x64, instalar `requirements-dev.txt`, disponer de Node y obtener el redistribuible oficial Microsoft. Ejecutar:

```powershell
python tools/build_public.py --vc-redist RUTA\VC_redist.x64.exe
```

La compilación genera semillas vacías nuevas en una carpeta temporal y excluye la semilla del administrador. No incorpora la carpeta local `data`, configuraciones privadas ni maestros operativos. El manifiesto registra las versiones y los hashes de los componentes distribuidos.
