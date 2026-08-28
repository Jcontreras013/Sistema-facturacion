from django.db import migrations


def rename_groups_forward(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Administrador").update(name="Supervisor")
    Group.objects.filter(name="Cajero").update(name="Caja")


def rename_groups_backward(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Supervisor").update(name="Administrador")
    Group.objects.filter(name="Caja").update(name="Cajero")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_company_auto_print_on_sale_company_receipt_format"),
    ]

    operations = [
        migrations.RunPython(rename_groups_forward, rename_groups_backward),
    ]
