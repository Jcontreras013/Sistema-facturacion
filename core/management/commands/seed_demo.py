from django.core.management.base import BaseCommand

from clients.models import Client
from inventory.models import Category, Product, Provider


class Command(BaseCommand):
    help = "Carga datos de ejemplo para un mini market: categorías, proveedores, productos y clientes."

    def handle(self, *args, **options):
        categories = {}
        for name in ["Abarrotes", "Bebidas", "Lácteos", "Limpieza", "Snacks", "Panadería"]:
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

        products = [
            ("AB001", "Arroz 1 lb", categories["Abarrotes"], provider1, "lb", 4.50, 6.50, 40),
            ("AB002", "Frijol negro 1 lb", categories["Abarrotes"], provider1, "lb", 5.00, 7.25, 35),
            ("AB003", "Azúcar 1 lb", categories["Abarrotes"], provider1, "lb", 3.80, 5.50, 30),
            ("BB001", "Agua pura 1 litro", categories["Bebidas"], provider2, "litro", 3.00, 5.00, 60),
            ("BB002", "Gaseosa 600ml", categories["Bebidas"], provider2, "unidad", 5.50, 8.50, 50),
            ("LA001", "Leche entera 1 litro", categories["Lácteos"], provider2, "litro", 7.00, 10.00, 25),
            ("LA002", "Queso fresco 1 lb", categories["Lácteos"], provider2, "lb", 15.00, 20.00, 10),
            ("LI001", "Jabón de lavar", categories["Limpieza"], provider1, "unidad", 4.00, 6.50, 20),
            ("LI002", "Cloro 1 litro", categories["Limpieza"], provider1, "litro", 6.00, 9.00, 15),
            ("SN001", "Papas fritas", categories["Snacks"], provider2, "unidad", 3.50, 5.50, 45),
            ("SN002", "Galletas dulces", categories["Snacks"], provider2, "paquete", 4.20, 6.75, 40),
            ("PN001", "Pan francés (unidad)", categories["Panadería"], provider1, "unidad", 0.50, 1.00, 100),
        ]

        for code, name, category, provider, unit, purchase_price, sale_price, stock in products:
            Product.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "category": category,
                    "provider": provider,
                    "unit": unit,
                    "purchase_price": purchase_price,
                    "sale_price": sale_price,
                    "stock": stock,
                    "min_stock": 10,
                },
            )

        clients = [
            ("Consumidor Final", "", "", ""),
            ("Juan Gómez", "1234567890101", "5555-1111", "juan.gomez@example.com"),
            ("Ana Martínez", "0987654321012", "5555-2222", "ana.martinez@example.com"),
        ]
        for name, document, phone, email in clients:
            Client.objects.get_or_create(name=name, defaults={"document": document, "phone": phone, "email": email})

        self.stdout.write(self.style.SUCCESS("Datos de ejemplo cargados correctamente."))
