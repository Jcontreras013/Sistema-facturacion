from django.core.management.base import BaseCommand

from core.permissions import ADMIN_GROUP, CASHIER_GROUP


class Command(BaseCommand):
    help = "Crea los grupos de roles (Administrador, Cajero) si no existen."

    def handle(self, *args, **options):
        from django.contrib.auth.models import Group

        for name in (ADMIN_GROUP, CASHIER_GROUP):
            _, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Grupo '{name}' creado."))
            else:
                self.stdout.write(f"Grupo '{name}' ya existía.")
