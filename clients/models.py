from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.urls import reverse


class Client(models.Model):
    name = models.CharField("Nombre completo", max_length=150)
    document = models.CharField("RTN / No. de Identidad", max_length=30, blank=True)
    phone = models.CharField("Teléfono", max_length=30, blank=True)
    email = models.EmailField("Correo", blank=True)
    address = models.CharField("Dirección", max_length=255, blank=True)
    credit_limit = models.DecimalField(
        "Límite de crédito (fiado)", max_digits=12, decimal_places=2, default=0,
        help_text="Monto máximo que este cliente puede deber. Déjalo en 0 para no permitirle comprar al crédito.",
    )
    is_active = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField("Registrado", auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("clients:client_detail", args=[self.pk])

    def credit_balance(self):
        """Cuánto debe actualmente este cliente por ventas al crédito (fiado)."""
        sales_total = self.sales.filter(status="completada", payment_method="credito").aggregate(
            t=Sum("total")
        )["t"] or Decimal("0")
        credit_notes_total = self.sales.filter(payment_method="credito").aggregate(
            t=Sum("credit_notes__total")
        )["t"] or Decimal("0")
        payments_total = self.credit_payments.aggregate(t=Sum("amount"))["t"] or Decimal("0")
        balance = sales_total - credit_notes_total - payments_total
        return balance if balance > 0 else Decimal("0")

    def credit_available(self):
        return self.credit_limit - self.credit_balance()

    @property
    def has_credit_enabled(self):
        return self.credit_limit > 0


class CreditPayment(models.Model):
    PAYMENT_METHODS = [
        ("efectivo", "Efectivo"),
        ("tarjeta", "Tarjeta"),
        ("transferencia", "Transferencia"),
    ]

    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.CASCADE, related_name="credit_payments")
    amount = models.DecimalField("Monto abonado", max_digits=12, decimal_places=2)
    payment_method = models.CharField("Forma de pago", max_length=20, choices=PAYMENT_METHODS, default="efectivo")
    notes = models.CharField("Notas", max_length=255, blank=True)
    user = models.ForeignKey(
        "auth.User", verbose_name="Registrado por", on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField("Fecha", auto_now_add=True)

    class Meta:
        verbose_name = "Abono a cuenta"
        verbose_name_plural = "Abonos a cuenta"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Abono de L {self.amount} — {self.client.name}"
