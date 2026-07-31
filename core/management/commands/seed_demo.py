import datetime

from django.core.management import call_command
from django.core.management.base import BaseCommand

from clients.models import Client
from core.models import Company
from inventory.models import Category, Product, Provider


class Command(BaseCommand):
    help = "Carga datos de ejemplo para un mini market: empresa, categorías, proveedores, productos y clientes."

    def handle(self, *args, **options):
        call_command("seed_groups")

        company = Company.load()
        if not company.trade_name:
            company.business_name = "Mini Market Demo, S. de R.L."
            company.trade_name = "Mini Market Demo"
            company.rtn = "08019999123456"
            company.address = "Col. Centro, Tegucigalpa, Honduras"
            company.phone = "2222-0000"
            company.email = "contacto@minimarketdemo.hn"
            company.invoice_regime = Company.REGIME_CAI
            company.cai_code = "1A2B3C-4D5E6F-7A8B9C-0D1E2F-A1B2C3"
            company.establishment_code = "001"
            company.emission_point_code = "001"
            company.document_type_code = "01"
            company.range_start = 1
            company.range_end = 10000
            company.next_correlative = 1
            company.emission_limit_date = datetime.date.today() + datetime.timedelta(days=365)
            company.default_isv_rate = 15
            company.save()

        categories = {}
        for name in ["Abarrotes", "Bebidas", "Lácteos", "Limpieza", "Snacks", "Panadería", "Licores"]:
            category, _ = Category.objects.get_or_create(name=name)
            categories[name] = category

        provider1, _ = Provider.objects.get_or_create(
            name="Distribuidora La Central",
            defaults={"contact_name": "Carlos Pérez", "phone": "5555-1234", "email": "ventas@lacentral.com"},
        )
        provider2, _ = Provider.objects.get_or_create(
            name="Alimentos del Valle",
            defaults={"contact_name": "María López", "phone": "5555-5678", "email": "pedidos@delvalle.com"},
        )

        soon = datetime.date.today() + datetime.timedelta(days=10)

        products = [
            ("AB001", "7501234560014", "Arroz 1 lb", categories["Abarrotes"], provider1, "lb", 4.50, 6.50, 15, 40, None, None),
            ("AB002", "7501234560021", "Frijol negro 1 lb", categories["Abarrotes"], provider1, "lb", 5.00, 7.25, 15, 35, None, None),
            ("AB003", "7501234560038", "Azúcar 1 lb", categories["Abarrotes"], provider1, "lb", 3.80, 5.50, 15, 30, None, None),
            ("BB001", "7501234560045", "Agua pura 1 litro", categories["Bebidas"], provider2, "litro", 3.00, 5.00, 15, 60, None, None),
            ("BB002", "7501234560052", "Gaseosa 600ml", categories["Bebidas"], provider2, "unidad", 5.50, 8.50, 15, 50, None, None),
            ("LA001", "7501234560069", "Leche entera 1 litro", categories["Lácteos"], provider2, "litro", 7.00, 10.00, 15, 25, None, soon),
            ("LA002", "7501234560076", "Queso fresco 1 lb", categories["Lácteos"], provider2, "lb", 15.00, 20.00, 15, 10, None, soon),
            ("LI001", "7501234560083", "Jabón de lavar", categories["Limpieza"], provider1, "unidad", 4.00, 6.50, 15, 20, None, None),
            ("LI002", "7501234560090", "Cloro 1 litro", categories["Limpieza"], provider1, "litro", 6.00, 9.00, 15, 15, None, None),
            ("SN001", "7501234560106", "Papas fritas", categories["Snacks"], provider2, "unidad", 3.50, 5.50, 15, 45, None, None),
            ("SN002", "7501234560113", "Galletas dulces", categories["Snacks"], provider2, "paquete", 4.20, 6.75, 15, 40, None, None),
            ("PN001", "7501234560120", "Pan francés (unidad)", categories["Panadería"], provider1, "unidad", 0.50, 1.00, 15, 100, None, None),
            ("LC001", "7501234560137", "Cerveza 355ml", categories["Licores"], provider2, "unidad", 12.00, 18.00, 18, 24, None, None),
        ]

        for code, barcode, name, category, provider, unit, purchase_price, sale_price, tax_rate, stock, _unused, expiration_date in products:
            Product.objects.get_or_create(
                code=code,
                defaults={
                    "barcode": barcode,
                    "name": name,
                    "category": category,
                    "provider": provider,
                    "unit": unit,
                    "purchase_price": purchase_price,
                    "sale_price": sale_price,
                    "tax_rate": tax_rate,
                    "stock": stock,
                    "min_stock": 10,
                    "expiration_date": expiration_date,
                },
            )

        clients = [
            ("Consumidor Final", "", "", ""),
            ("Juan Gómez", "08019876543210", "5555-1111", "juan.gomez@example.com"),
            ("Ana Martínez", "08011234567890", "5555-2222", "ana.martinez@example.com"),
        ]
        for name, document, phone, email in clients:
            Client.objects.get_or_create(name=name, defaults={"document": document, "phone": phone, "email": email})

        self.stdout.write(self.style.SUCCESS("Datos de ejemplo cargados correctamente."))
