# Sistema de Facturación para Mini Markets

Aplicación web construida con Django para administrar un mini market: punto de venta (POS), inventario, clientes/proveedores y reportes.

## Funcionalidades

- **Punto de venta (POS):** búsqueda rápida de productos, carrito interactivo, cálculo automático de impuesto (12%) y total, generación de factura.
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

## Estructura del proyecto

- `config/` – configuración del proyecto Django (settings, urls).
- `core/` – panel principal (dashboard) y comando `seed_demo`.
- `inventory/` – categorías, proveedores, productos y movimientos de inventario.
- `clients/` – clientes.
- `sales/` – punto de venta, facturas y detalle de ventas.
- `reports/` – reportes de ventas, productos top, ganancias y stock bajo.

## Notas

- La tasa de impuesto (12%, IVA de Guatemala) se define en `sales/models.py` (`TAX_RATE`).
- La base de datos por defecto es SQLite (`db.sqlite3`), ideal para un solo punto de venta. Para producción se recomienda migrar a PostgreSQL y ajustar `DEBUG`, `ALLOWED_HOSTS` y `SECRET_KEY`.
