# Sistema de Facturación para Mini Markets (Honduras)

Aplicación web construida con Django para administrar un mini market: punto de venta (POS), inventario, clientes/proveedores, caja y reportes, adaptada al régimen fiscal de Honduras (SAR).

## Funcionalidades

- **Configuración fiscal del negocio:** RTN, régimen de facturación (CAI impreso o CFE electrónico), rango de facturas autorizado, fecha límite de emisión, tasa de ISV por defecto.
- **Numeración de factura formato Honduras:** `000-001-01-00000001`, con control automático del rango autorizado por el CAI.
- **Punto de venta (POS):** búsqueda o escaneo de código de barras (Enter agrega el producto), carrito interactivo, ISV diferenciado por producto (15% o 18% para alcohol/tabaco), forma de pago, y selección de cliente con buscador (escribe el nombre para filtrar en vez de desplazarte por un listado largo). Al elegir un cliente ya registrado, su RTN se autocompleta (y queda de solo lectura si ya lo tiene guardado); si no lo tiene, puedes escribirlo ahí mismo y se guarda al cobrar. También puedes crear un cliente nuevo (nombre y RTN opcional) sin salir del POS.
- **Caja:** apertura y cierre con arqueo (monto esperado vs. contado, diferencia), historial de sesiones.
- **Notas de crédito:** devoluciones parciales o totales sobre una factura, con restitución automática de stock.
- **Inventario:** productos con código, código de barras, categoría, proveedor, precios de compra/venta, ISV, stock, fecha de vencimiento; alertas de stock bajo y de productos por vencer; movimientos de inventario con motivo (compra, venta, merma, daño, robo, devolución, otro).
- **Clientes y proveedores:** administración (CRUD) de ambos, historial de compras por cliente, RTN/identidad del cliente.
- **Ventas:** historial con filtros por fecha y cliente, detalle de factura imprimible, anulación de ventas (solo administradores).
- **Roles:** Administrador (todo) y Cajero (POS, ventas, clientes, consulta de productos) — los reportes, configuración del negocio, categorías, proveedores y edición de productos son solo para administradores.
- **Gestión de usuarios (solo administradores):** crear, editar rol/contraseña y eliminar usuarios desde el panel (Admin → Usuarios).
- **Eliminación de registros (solo administradores):** además del CRUD normal de productos/categorías/proveedores/clientes, el admin puede eliminar ventas/facturas, notas de crédito y sesiones de caja, con las restauraciones de stock correspondientes (eliminar una venta completada restituye el stock; eliminar una nota de crédito revierte la devolución). No se puede eliminar una venta que ya tiene notas de crédito asociadas sin borrar esas notas primero.
- **Bitácora de auditoría (solo administradores):** registro de quién creó, modificó o eliminó cada producto, cliente, venta, nota de crédito, sesión de caja o usuario, con fecha y hora (Admin → Bitácora de auditoría).
- **Reportes (solo administradores):** ventas por período, productos más vendidos, ganancias, stock bajo, productos por vencer, ISV cobrado por tasa (para la declaración ante el SAR), flujo de caja.
- **Impresión de tickets:** formato configurable por negocio (Admin → Configuración del negocio) para térmica 80mm, térmica 58mm o matriz de puntos/carta — cada uno ajusta ancho, tipografía y columnas visibles (los formatos angostos ocultan detalle de ISV/precio unitario para que quepa en el rollo). También se puede activar impresión automática al cobrar una venta en el POS, para que abra el diálogo de impresión de una vez, como una caja registradora normal.
- **Importar inventario desde otro sistema (solo administradores):** en Productos → Importar, sube un archivo `.xlsx`, `.xls` o `.csv` exportado de otro sistema de cobro. El sistema detecta automáticamente qué columna es código, nombre, precio, existencias, categoría, etc. (en español o inglés, con sinónimos comunes), y siempre muestra una vista previa donde puedes corregir el mapeo a mano antes de confirmar — así no depende de que el archivo tenga un formato exacto. Tolera precios con coma o punto decimal, distintas codificaciones de texto y fechas en varios formatos. Permite crear productos nuevos o actualizar existentes por código, con un resumen de creados/actualizados/omitidos al final.

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
- Pendiente para una próxima fase: órdenes de compra y cuentas por pagar a proveedores, crédito/fiado a clientes, modo offline con sincronización, e integración directa con hardware (impresión ESC/POS por USB, cajón de dinero, báscula).
