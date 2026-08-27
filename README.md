# Sistema de Facturación para Mini Markets (Honduras)

Aplicación web construida con Django para administrar un mini market: punto de venta (POS), inventario, clientes/proveedores, caja y reportes, adaptada al régimen fiscal de Honduras (SAR).

## Funcionalidades

- **Configuración fiscal del negocio:** RTN, régimen de facturación (CAI impreso o CFE electrónico), rango de facturas autorizado, fecha límite de emisión, tasa de ISV por defecto.
- **Numeración de factura formato Honduras:** `000-001-01-00000001`, con control automático del rango autorizado por el CAI.
- **Punto de venta (POS), pensado para cobrar rápido con mucha afluencia de clientes:** búsqueda o escaneo de código de barras (Enter agrega el producto), navegación completa por teclado (flechas + Enter, sin necesidad del mouse), carrito interactivo, ISV diferenciado por producto (15% o 18% para alcohol/tabaco), forma de pago, y selección de cliente con buscador (escribe el nombre para filtrar en vez de desplazarte por un listado largo). Al elegir un cliente ya registrado, su RTN se autocompleta (y queda de solo lectura si ya lo tiene guardado); si no lo tiene, puedes escribirlo ahí mismo y se guarda al cobrar. También puedes crear un cliente nuevo (nombre y RTN opcional) sin salir del POS. Al pagar en efectivo, una calculadora de cambio integrada muestra cuánto devolver apenas escribes el monto recibido, y tras cobrar aparece un botón grande de "Nueva venta" que regresa directo al punto de venta para el siguiente cliente, sin pasar por el historial. En la parte inferior hay una barra de teclas de función al estilo de las cajas registradoras clásicas (Microsoft RMS y similares) — F1 Ayuda, F2 Producto, F3 Cliente, F4 Pago, F5 Efectivo, F6 Notas, F7 Nueva venta, F8 Quitar producto, F9 Historial y F12 Cobrar — pensada para que un cajero acostumbrado a ese tipo de sistema se sienta cómodo desde el primer día; los botones también se pueden pulsar con el mouse o el dedo en pantallas táctiles. Además: un botón "Reimprimir última" para reimprimir la factura recién cobrada sin ir al historial; productos que se venden por libra/kilo/litro aceptan cantidades decimales en el carrito (0.5, 2.75, etc.); y "Suspender venta" guarda el carrito actual en espera (con cliente, forma de pago y notas) para atender a otro cliente y recuperarlo después desde "Ventas en espera", sin perder nada. También se puede cobrar con "Mixto" (parte en efectivo, parte en tarjeta/transferencia): el sistema valida en vivo que la suma de ambos montos coincida con el total antes de habilitar el botón de cobrar, y solo la parte en efectivo cuenta para el arqueo de caja. También se puede aplicar un descuento porcentual sobre toda la venta, pero requiere autorización: el cajero indica el porcentaje y un administrador debe ingresar su usuario y contraseña para aprobarlo (el sistema nunca deja que el propio cajero se autorice a sí mismo), y la factura queda con el descuento y el nombre de quién lo autorizó. Si tienes activada la impresión automática (Admin → Configuración del negocio), al terminar de imprimir aparece automáticamente una pantalla de "¡Gracias por su compra!" — con solo presionar Enter (o tocar el botón) vuelve al punto de venta listo para el siguiente cliente, sin que el cajero tenga que hacer nada más entre una venta y otra.
- **Caja:** apertura y cierre con arqueo (monto esperado vs. contado, diferencia), historial de sesiones.
- **Notas de crédito:** devoluciones parciales o totales sobre una factura, con restitución automática de stock.
- **Inventario:** productos con código, código de barras, categoría, proveedor, precios de compra/venta, ISV, stock, fecha de vencimiento; alertas de stock bajo y de productos por vencer; movimientos de inventario con motivo (compra, venta, merma, daño, robo, devolución, otro). Cada producto puede tener un precio de mayoreo opcional (precio + cantidad mínima); en el POS se aplica automáticamente en cuanto la cantidad de esa línea alcanza el mínimo, con una etiqueta "Mayoreo" para que quede claro por qué cambió el precio.
- **Clientes y proveedores:** administración (CRUD) de ambos, historial de compras por cliente, RTN/identidad del cliente.
- **Ventas:** historial con filtros por fecha y cliente, detalle de factura imprimible, anulación de ventas (solo administradores).
- **Roles:** Administrador (todo) y Cajero (POS, ventas, clientes, consulta de productos) — los reportes, configuración del negocio, categorías, proveedores y edición de productos son solo para administradores.
- **Gestión de usuarios (solo administradores):** crear, editar rol/contraseña y eliminar usuarios desde el panel (Admin → Usuarios).
- **Eliminación de registros (solo administradores):** además del CRUD normal de productos/categorías/proveedores/clientes, el admin puede eliminar ventas/facturas, notas de crédito y sesiones de caja, con las restauraciones de stock correspondientes (eliminar una venta completada restituye el stock; eliminar una nota de crédito revierte la devolución). No se puede eliminar una venta que ya tiene notas de crédito asociadas sin borrar esas notas primero.
- **Bitácora de auditoría (solo administradores):** registro de quién creó, modificó o eliminó cada producto, cliente, venta, nota de crédito, sesión de caja o usuario, con fecha y hora (Admin → Bitácora de auditoría).
- **Reportes (solo administradores):** ventas por período, productos más vendidos, ganancias, stock bajo, productos por vencer, flujo de caja, cuentas por cobrar, e ISV por tasa (15%/18%) neto de notas de crédito del período — pensado como insumo directo para la declaración mensual de ISV ante el SAR (no incluye crédito fiscal de compras a proveedores, ya que el sistema no lleva ese detalle). Todos los reportes se pueden descargar como archivo Excel (.xlsx) con el botón "Descargar", respetando el rango de fechas filtrado.
- **Impresión de tickets:** formato configurable por negocio (Admin → Configuración del negocio) para térmica 80mm, térmica 58mm o matriz de puntos/carta — cada uno ajusta ancho, tipografía y columnas visibles (los formatos angostos ocultan detalle de ISV/precio unitario para que quepa en el rollo). También se puede activar impresión automática al cobrar una venta en el POS, para que abra el diálogo de impresión de una vez, como una caja registradora normal.
- **Importar inventario desde otro sistema (solo administradores):** en Productos → Importar, sube un archivo `.xlsx`, `.xls` o `.csv` exportado de otro sistema de cobro. El sistema detecta automáticamente qué columna es código, nombre, precio, existencias, categoría, etc. (en español o inglés, con sinónimos comunes), y siempre muestra una vista previa donde puedes corregir el mapeo a mano antes de confirmar — así no depende de que el archivo tenga un formato exacto. Tolera precios con coma o punto decimal, distintas codificaciones de texto y fechas en varios formatos. Permite crear productos nuevos o actualizar existentes por código, con un resumen de creados/actualizados/omitidos al final.
- **Modo sin conexión (PWA) en el punto de venta:** el sistema es instalable como app (ícono en el celular/tablet/escritorio) y funciona como PWA. Si se pierde el internet en plena venta, el POS sigue permitiendo cobrar: la venta se guarda en el dispositivo (IndexedDB) y se envía sola al servidor en cuanto vuelve la conexión, sin perder la venta ni bloquear al cajero. Un indicador en pantalla muestra si hay conexión y cuántas ventas están pendientes de sincronizar. **Limitaciones:** una venta hecha sin conexión no tiene número de factura oficial hasta que se sincroniza (el correlativo del CAI lo asigna el servidor); el catálogo de productos/stock que se ve sin conexión es el de la última vez que esa pantalla cargó con internet, así que el stock mostrado puede estar desactualizado; y está pensado para un solo dispositivo cobrando a la vez (si varios cajeros venden el mismo producto sin conexión simultáneamente, el control de stock se reconcilia hasta que todos sincronizan).
- **Crédito a clientes (fiado):** cada cliente puede tener un límite de crédito (0 = fiado deshabilitado, solo lo puede fijar un administrador). En el POS, "Crédito (fiado)" aparece como forma de pago, mostrando el saldo que debe el cliente y su disponible antes de cobrar; el sistema rechaza la venta si supera el límite o si el cliente no tiene crédito habilitado. Desde la ficha del cliente (o desde Reportes → Cuentas por cobrar) se puede ver el detalle de ventas al crédito y registrar abonos parciales o totales a la cuenta, que descuentan el saldo pendiente. Las notas de crédito sobre una venta al fiado también reducen automáticamente lo que debe el cliente.

## Requisitos

- Python 3.11+

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_groups        # crea los grupos "Administrador" y "Cajero"
python manage.py createsuperuser    # tu usuario administrador
python manage.py seed_demo          # datos de ejemplo opcionales (empresa, categorías, productos, clientes)

python manage.py runserver
```

Luego visita `http://localhost:8000/`, inicia sesión con el usuario creado y entra a **Admin → Configuración del negocio** para poner el RTN, CAI y rango de facturas reales de tu comercio.

Para crear un usuario cajero (sin acceso a reportes/configuración):

```bash
python manage.py shell -c "
from django.contrib.auth.models import User, Group
u = User.objects.create_user('cajero1', password='una-contraseña-segura')
u.groups.add(Group.objects.get(name='Cajero'))
"
```

## Despliegue en Render (gratis)

El repositorio incluye `render.yaml` (Blueprint), `build.sh` y soporte para PostgreSQL/whitenoise, listos para desplegar:

1. Crea una cuenta en [render.com](https://render.com) (no pide tarjeta) e inicia sesión con GitHub.
2. En el dashboard: **New +** → **Blueprint** → selecciona el repositorio `sistema-facturacion` y la rama `claude/mini-markets-system-fme1x5`.
3. Render detecta `render.yaml` y crea automáticamente el servicio web (Python/gunicorn) y una base de datos PostgreSQL gratuita, conectados entre sí.
4. Antes de aplicar, define estas variables de entorno del servicio web (para tu usuario administrador):
   - `DJANGO_SUPERUSER_USERNAME`
   - `DJANGO_SUPERUSER_PASSWORD`
   - `DJANGO_SUPERUSER_EMAIL`
5. Aplica el Blueprint. Render instalará dependencias, correrá migraciones, creará los grupos de roles, el superusuario y (si `SEED_DEMO=true`) cargará datos de ejemplo.
6. Cuando termine el build, Render te da una URL pública `https://<nombre>.onrender.com` — ya funcional.
7. Entra a **Admin → Configuración del negocio** y reemplaza los datos de ejemplo con el RTN, CAI y rango de facturas reales del comercio antes de facturar en producción.

Notas:
- El plan free "duerme" el servicio tras ~15 minutos sin tráfico (la primera petición tras dormir tarda unos segundos en responder).
- La base de datos free de Render expira a los 90 días; para uso real, actualiza a un plan pago cuando estés listo.
- Puedes desactivar los datos de ejemplo cambiando `SEED_DEMO` a `"false"` en el servicio.

## Estructura del proyecto

- `config/` – configuración del proyecto Django (settings, urls).
- `core/` – panel principal (dashboard), configuración fiscal del negocio (`Company`), roles/permisos, comandos `seed_demo`/`seed_groups`/`ensure_admin`.
- `inventory/` – categorías, proveedores, productos y movimientos de inventario.
- `clients/` – clientes.
- `sales/` – punto de venta, caja, facturas, notas de crédito.
- `reports/` – reportes de ventas, productos top, ganancias, stock bajo, vencimientos, impuestos y flujo de caja.

## Notas

- **Eliminar una factura ya emitida rompe la secuencia correlativa autorizada por el CAI y normalmente no es válido ante el SAR** — lo correcto fiscalmente es anular (opción ya disponible), no eliminar. La opción de eliminar existe para corregir errores de captura reales, pero úsala con criterio.
- El régimen CFE (Factura Electrónica) usa por ahora una numeración interna simple; la integración real con el webservice del SAR para timbrado electrónico **no está implementada** — es un desarrollo aparte que requiere las especificaciones técnicas del SAR y el certificado/credenciales del comercio.
- La base de datos por defecto es SQLite (`db.sqlite3`), ideal para desarrollo. En producción (Render) se usa PostgreSQL automáticamente vía `DATABASE_URL`.
- La impresión funciona a través del diálogo de impresión del navegador hacia la impresora que tengas instalada en el sistema operativo (térmica o de matriz de puntos) — no requiere hardware especial ni drivers propios, pero sí que la impresora esté correctamente instalada en Windows/el sistema donde corra el navegador. No es una integración directa por USB/ESC-POS crudo.
- Pendiente para una próxima fase: órdenes de compra y cuentas por pagar a proveedores, e integración directa con hardware (impresión ESC/POS por USB, cajón de dinero, báscula).
