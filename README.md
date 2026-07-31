# Sistema de Facturación para Mini Markets

Aplicación web construida con Django para administrar un mini market: punto de venta (POS), inventario, clientes/proveedores y reportes.

## Funcionalidades

- **Punto de venta (POS):** búsqueda rápida de productos, carrito interactivo, cálculo automático de impuesto (15%) y total, generación de factura.
- **Inventario:** productos con código, categoría, proveedor, precios de compra/venta y stock; alertas de stock bajo; historial de movimientos (entradas, salidas, ajustes).
- **Clientes y proveedores:** administración (CRUD) de ambos, historial de compras por cliente.
- **Ventas:** historial con filtros por fecha y cliente, detalle de factura imprimible, anulación de ventas (restituye stock).
- **Reportes:** ventas por período, productos más vendidos, ganancias (ingresos - costo), stock bajo.

## Requisitos

- Python 3.11+

## Instalación

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo   # datos de ejemplo opcionales (categorías, proveedores, productos, clientes)

python manage.py runserver
```

Luego visita `http://localhost:8000/` e inicia sesión con el usuario creado.

## Despliegue en Render (gratis)

El repositorio incluye `render.yaml` (Blueprint), `build.sh` y soporte para PostgreSQL/whitenoise, listos para desplegar:

1. Crea una cuenta en [render.com](https://render.com) (no pide tarjeta) e inicia sesión con GitHub.
2. En el dashboard: **New +** → **Blueprint** → selecciona el repositorio `sistema-facturacion` y la rama `claude/mini-markets-system-fme1x5`.
3. Render detecta `render.yaml` y crea automáticamente el servicio web (Python/gunicorn) y una base de datos PostgreSQL gratuita, conectados entre sí.
4. Antes de aplicar, define estas variables de entorno del servicio web (para tu usuario administrador):
   - `DJANGO_SUPERUSER_USERNAME`
   - `DJANGO_SUPERUSER_PASSWORD`
   - `DJANGO_SUPERUSER_EMAIL`
5. Aplica el Blueprint. Render instalará dependencias, correrá migraciones, creará el superusuario y (si `SEED_DEMO=true`) cargará datos de ejemplo.
6. Cuando termine el build, Render te da una URL pública `https://<nombre>.onrender.com` — ya funcional.

Notas:
- El plan free "duerme" el servicio tras ~15 minutos sin tráfico (la primera petición tras dormir tarda unos segundos en responder).
- La base de datos free de Render expira a los 90 días; para uso real, actualiza a un plan pago cuando estés listo.
- Puedes desactivar los datos de ejemplo cambiando `SEED_DEMO` a `"false"` en el servicio.

## Estructura del proyecto

- `config/` – configuración del proyecto Django (settings, urls).
- `core/` – panel principal (dashboard) y comando `seed_demo`.
- `inventory/` – categorías, proveedores, productos y movimientos de inventario.
- `clients/` – clientes.
- `sales/` – punto de venta, facturas y detalle de ventas.
- `reports/` – reportes de ventas, productos top, ganancias y stock bajo.

## Notas

- La tasa de impuesto (15%, ISV de Honduras) se define en `sales/models.py` (`TAX_RATE`).
- La base de datos por defecto es SQLite (`db.sqlite3`), ideal para un solo punto de venta. Para producción se recomienda migrar a PostgreSQL y ajustar `DEBUG`, `ALLOWED_HOSTS` y `SECRET_KEY`.
