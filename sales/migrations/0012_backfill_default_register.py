from django.db import migrations


def create_default_register(apps, schema_editor):
    Register = apps.get_model("sales", "Register")
    CashSession = apps.get_model("sales", "CashSession")
    if CashSession.objects.filter(register__isnull=True).exists() or not Register.objects.exists():
        register, _ = Register.objects.get_or_create(name="Caja 1", defaults={"is_active": True})
        CashSession.objects.filter(register__isnull=True).update(register=register)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0011_register_cashsession_register_and_more"),
    ]

    operations = [
        migrations.RunPython(create_default_register, noop),
    ]
