from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from clients.models import Client
from inventory.models import Product

TAX_RATE = Decimal("0.15")


class Sale(models.Model):
    PAYMENT_METHODS = [
        ("efectivo", "Efectivo"),
        ("tarjeta", "Tarjeta"),
        ("transferencia", "Transferencia"),
    ]
    STATUS_CHOICES = [
        ("completada", "Completada"),
        ("anulada", "Anulada"),
    ]

    number = models.CharField("No. de factura", max_length=20, unique=True, blank=True)
    client = models.ForeignKey(
        Client, verbose_name="Cliente", on_delete=models.SET_NULL, null=True, blank=True, related_name="sales"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Cajero", on_delete=models.SET_NULL, null=True, related_name="sales"
    )
    payment_method = models.CharField("Forma de pago", max_length=20, choices=PAYMENT_METHODS, default="efectivo")
    status = models.CharField("Estado", max_length=15, choices=STATUS_CHOICES, default="completada")
    subtotal = models.DecimalField("Subtotal", max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField("Impuesto", max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField("Total", max_digits=12, decimal_places=2, default=0)
    notes = models.CharField("Notas", max_length=255, blank=True)
    created_at = models.DateTimeField("Fecha", auto_now_add=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ["-created_at"]

    def __str__(self):
        return self.number or f"Venta #{self.pk}"

    def get_absolute_url(self):
        return reverse("sales:sale_detail", args=[self.pk])

    def save(self, *args, **kwargs):
        if not self.number:
            last = Sale.objects.order_by("-id").first()
            next_id = (last.id + 1) if last else 1
            self.number = f"F-{next_id:06d}"
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        subtotal = sum((item.subtotal for item in self.items.all()), Decimal("0"))
        tax = (subtotal * TAX_RATE).quantize(Decimal("0.01"))
        self.subtotal = subtotal
        self.tax = tax
        self.total = subtotal + tax
        self.save(update_fields=["subtotal", "tax", "total"])


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.DecimalField("Cantidad", max_digits=10, decimal_places=2)
    unit_price = models.DecimalField("Precio unitario", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price
