from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Company(models.Model):
    REGIME_CAI = "cai"
    REGIME_CFE = "cfe"
    REGIME_CHOICES = [
        (REGIME_CAI, "Régimen por Imprenta (CAI)"),
        (REGIME_CFE, "Factura Electrónica (CFE)"),
    ]

    business_name = models.CharField("Razón social", max_length=200, blank=True)
    trade_name = models.CharField("Nombre comercial", max_length=200, blank=True)
    rtn = models.CharField("RTN del negocio", max_length=20, blank=True)
    address = models.CharField("Dirección", max_length=255, blank=True)
    phone = models.CharField("Teléfono", max_length=30, blank=True)
    email = models.EmailField("Correo", blank=True)

    invoice_regime = models.CharField(
        "Régimen de facturación", max_length=10, choices=REGIME_CHOICES, default=REGIME_CAI
    )

    # Datos del CAI (Régimen por Imprenta)
    cai_code = models.CharField("Código CAI", max_length=50, blank=True)
    establishment_code = models.CharField("Código de establecimiento", max_length=3, default="001")
    emission_point_code = models.CharField("Código de punto de emisión", max_length=3, default="001")
    document_type_code = models.CharField("Código de tipo de documento", max_length=2, default="01")
    range_start = models.PositiveIntegerField("Correlativo inicial autorizado", default=1)
    range_end = models.PositiveIntegerField("Correlativo final autorizado", default=10000)
    next_correlative = models.PositiveIntegerField("Próximo correlativo a emitir", default=1)
    emission_limit_date = models.DateField("Fecha límite de emisión", null=True, blank=True)

    default_isv_rate = models.DecimalField("Tasa de ISV por defecto (%)", max_digits=5, decimal_places=2, default=Decimal("15.00"))

    updated_at = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Configuración del negocio"
        verbose_name_plural = "Configuración del negocio"

    def __str__(self):
        return self.trade_name or self.business_name or "Configuración del negocio"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def range_remaining(self):
        return max(self.range_end - self.next_correlative + 1, 0)

    def reserve_next_invoice_number(self):
        """Devuelve el número formateado para la próxima factura y avanza el correlativo. No guarda el modelo."""
        if self.invoice_regime == self.REGIME_CAI:
            if self.next_correlative > self.range_end:
                raise ValidationError(
                    "El rango de facturas autorizado por el CAI se agotó. "
                    "Actualiza la configuración del negocio con un nuevo CAI antes de facturar."
                )
            import datetime

            if self.emission_limit_date and datetime.date.today() > self.emission_limit_date:
                raise ValidationError(
                    "La fecha límite de emisión del CAI actual ya pasó. "
                    "Actualiza la configuración del negocio con un nuevo CAI antes de facturar."
                )
            number = (
                f"{self.establishment_code}-{self.emission_point_code}-"
                f"{self.document_type_code}-{self.next_correlative:08d}"
            )
        else:
            number = f"CFE-{self.next_correlative:08d}"

        self.next_correlative += 1
        self.save(update_fields=["next_correlative"])
        return number


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("created", "Creó"),
        ("updated", "Modificó"),
        ("deleted", "Eliminó"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Usuario", on_delete=models.SET_NULL, null=True, related_name="audit_logs"
    )
    action = models.CharField("Acción", max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField("Tipo de registro", max_length=100)
    object_repr = models.CharField("Registro", max_length=255)
    object_id = models.CharField("ID", max_length=50, blank=True)
    extra = models.CharField("Detalle", max_length=255, blank=True)
    created_at = models.DateTimeField("Fecha y hora", auto_now_add=True)

    class Meta:
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Bitácora de auditoría"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.get_action_display()} {self.model_name} #{self.object_id}"
