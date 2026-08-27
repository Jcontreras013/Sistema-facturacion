from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from clients.models import Client
from core.models import Company
from inventory.models import Product


class CashSession(models.Model):
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Abierta por", on_delete=models.SET_NULL, null=True,
        related_name="cash_sessions_opened",
    )
    opened_at = models.DateTimeField("Apertura", auto_now_add=True)
    opening_amount = models.DecimalField("Monto inicial", max_digits=12, decimal_places=2, default=0)

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Cerrada por", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cash_sessions_closed",
    )
    closed_at = models.DateTimeField("Cierre", null=True, blank=True)
    counted_amount = models.DecimalField("Monto contado al cierre", max_digits=12, decimal_places=2, null=True, blank=True)
    expected_amount = models.DecimalField("Monto esperado", max_digits=12, decimal_places=2, null=True, blank=True)
    difference = models.DecimalField("Diferencia", max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.CharField("Notas", max_length=255, blank=True)

    class Meta:
        verbose_name = "Sesión de caja"
        verbose_name_plural = "Sesiones de caja"
        ordering = ["-opened_at"]

    def __str__(self):
        return f"Caja #{self.pk} ({'abierta' if self.is_open else 'cerrada'})"

    @property
    def is_open(self):
        return self.closed_at is None

    def cash_sales_total(self):
        cash_total = self.sales.filter(status="completada", payment_method="efectivo").aggregate(
            total=models.Sum("total")
        )["total"] or Decimal("0")
        mixed_cash_total = self.sales.filter(status="completada", payment_method="mixto").aggregate(
            total=models.Sum("mixed_cash_amount")
        )["total"] or Decimal("0")
        return cash_total + mixed_cash_total

    def close(self, counted_amount, closed_by, notes=""):
        import django.utils.timezone as timezone

        self.expected_amount = self.opening_amount + self.cash_sales_total()
        self.counted_amount = counted_amount
        self.difference = counted_amount - self.expected_amount
        self.closed_by = closed_by
        self.closed_at = timezone.now()
        self.notes = notes
        self.save()


class Sale(models.Model):
    PAYMENT_METHODS = [
        ("efectivo", "Efectivo"),
        ("tarjeta", "Tarjeta"),
        ("transferencia", "Transferencia"),
        ("credito", "Crédito (fiado)"),
        ("mixto", "Mixto (efectivo + otro)"),
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
    cash_session = models.ForeignKey(
        CashSession, verbose_name="Sesión de caja", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sales",
    )
    payment_method = models.CharField("Forma de pago", max_length=20, choices=PAYMENT_METHODS, default="efectivo")
    status = models.CharField("Estado", max_length=15, choices=STATUS_CHOICES, default="completada")
    subtotal = models.DecimalField("Subtotal", max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField("Impuesto", max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField("Total", max_digits=12, decimal_places=2, default=0)
    notes = models.CharField("Notas", max_length=255, blank=True)
    mixed_cash_amount = models.DecimalField(
        "Monto en efectivo (pago mixto)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    mixed_other_amount = models.DecimalField(
        "Monto en otro método (pago mixto)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    discount_percent = models.DecimalField("Descuento (%)", max_digits=5, decimal_places=2, default=0)
    discount_authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Descuento autorizado por", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="authorized_discounts",
    )
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
            company = Company.load()
            self.number = company.reserve_next_invoice_number()
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        items = list(self.items.all())
        subtotal = sum((item.subtotal for item in items), Decimal("0"))
        tax = sum((item.tax_amount for item in items), Decimal("0")).quantize(Decimal("0.01"))
        gross_total = subtotal + tax
        discount = (gross_total * self.discount_percent / Decimal("100")).quantize(Decimal("0.01"))
        self.subtotal = subtotal
        self.tax = tax
        self.total = gross_total - discount
        self.save(update_fields=["subtotal", "tax", "total"])

    @property
    def discount_amount(self):
        return (self.subtotal + self.tax) - self.total


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.DecimalField("Cantidad", max_digits=10, decimal_places=2)
    unit_price = models.DecimalField("Precio unitario", max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField("Tasa de ISV (%)", max_digits=5, decimal_places=2, default=Decimal("15.00"))

    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    @property
    def tax_amount(self):
        return self.subtotal * (self.tax_rate / Decimal("100"))

    @property
    def returned_quantity(self):
        return sum(
            (ci.quantity for ci in self.credit_note_items.all()), Decimal("0")
        )

    @property
    def returnable_quantity(self):
        return self.quantity - self.returned_quantity


class CreditNote(models.Model):
    number = models.CharField("No. de nota de crédito", max_length=20, unique=True, blank=True)
    sale = models.ForeignKey(Sale, verbose_name="Venta original", on_delete=models.PROTECT, related_name="credit_notes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Registrada por", on_delete=models.SET_NULL, null=True
    )
    reason = models.CharField("Motivo", max_length=255)
    subtotal = models.DecimalField("Subtotal", max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField("Impuesto", max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField("Total", max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField("Fecha", auto_now_add=True)

    class Meta:
        verbose_name = "Nota de crédito"
        verbose_name_plural = "Notas de crédito"
        ordering = ["-created_at"]

    def __str__(self):
        return self.number or f"NC-{self.pk}"

    def save(self, *args, **kwargs):
        if not self.number:
            last = CreditNote.objects.order_by("-id").first()
            next_id = (last.id + 1) if last else 1
            self.number = f"NC-{next_id:06d}"
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        items = list(self.items.all())
        subtotal = sum((item.subtotal for item in items), Decimal("0"))
        tax = sum((item.tax_amount for item in items), Decimal("0")).quantize(Decimal("0.01"))
        self.subtotal = subtotal
        self.tax = tax
        self.total = subtotal + tax
        self.save(update_fields=["subtotal", "tax", "total"])


class HeldSale(models.Model):
    """Una venta que el cajero dejó en espera (suspendida) para atender a otro cliente."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Cajero", on_delete=models.CASCADE, related_name="held_sales"
    )
    client_id = models.CharField("ID de cliente (crudo)", max_length=20, blank=True)
    client_name = models.CharField("Cliente", max_length=150, blank=True)
    client_rtn = models.CharField("RTN del cliente", max_length=30, blank=True)
    new_client_name = models.CharField("Nombre de cliente nuevo", max_length=150, blank=True)
    payment_method = models.CharField("Forma de pago", max_length=20, blank=True)
    notes = models.CharField("Notas", max_length=255, blank=True)
    cart_json = models.TextField("Carrito (JSON)")
    created_at = models.DateTimeField("Puesta en espera", auto_now_add=True)

    class Meta:
        verbose_name = "Venta en espera"
        verbose_name_plural = "Ventas en espera"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Venta en espera #{self.pk} ({self.client_name or 'Consumidor final'})"


class CreditNoteItem(models.Model):
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE, related_name="items")
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT, related_name="credit_note_items")
    quantity = models.DecimalField("Cantidad devuelta", max_digits=10, decimal_places=2)
    unit_price = models.DecimalField("Precio unitario", max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField("Tasa de ISV (%)", max_digits=5, decimal_places=2, default=Decimal("15.00"))

    class Meta:
        verbose_name = "Detalle de nota de crédito"
        verbose_name_plural = "Detalles de nota de crédito"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    @property
    def tax_amount(self):
        return self.subtotal * (self.tax_rate / Decimal("100"))
