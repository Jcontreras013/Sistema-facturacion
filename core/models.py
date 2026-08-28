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

    # Rango de contingencia: bloque de correlativos reservado exclusivamente para facturar
    # sin internet (usa el mismo establecimiento/punto/tipo de documento de arriba).
    contingency_enabled = models.BooleanField("Usar rango de contingencia sin internet", default=False)
    contingency_range_start = models.PositiveIntegerField("Correlativo inicial de contingencia", null=True, blank=True)
    contingency_range_end = models.PositiveIntegerField("Correlativo final de contingencia", null=True, blank=True)
    contingency_next_correlative = models.PositiveIntegerField("Próximo correlativo de contingencia", null=True, blank=True)

    default_isv_rate = models.DecimalField("Tasa de ISV por defecto (%)", max_digits=5, decimal_places=2, default=Decimal("15.00"))

    RECEIPT_THERMAL_80 = "thermal_80"
    RECEIPT_THERMAL_58 = "thermal_58"
    RECEIPT_LETTER = "letter"
    RECEIPT_FORMAT_CHOICES = [
        (RECEIPT_THERMAL_80, "Térmica 80mm"),
        (RECEIPT_THERMAL_58, "Térmica 58mm"),
        (RECEIPT_LETTER, "Matriz de puntos / carta"),
    ]
    receipt_format = models.CharField(
        "Formato de impresión de ticket", max_length=15, choices=RECEIPT_FORMAT_CHOICES, default=RECEIPT_THERMAL_80
    )
    auto_print_on_sale = models.BooleanField("Imprimir automáticamente al cobrar una venta", default=True)

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

    @property
    def contingency_remaining(self):
        if not (self.contingency_enabled and self.contingency_range_end and self.contingency_next_correlative):
            return 0
        return max(self.contingency_range_end - self.contingency_next_correlative + 1, 0)

    def format_invoice_number(self, correlative):
        if self.invoice_regime == self.REGIME_CAI:
            return (
                f"{self.establishment_code}-{self.emission_point_code}-"
                f"{self.document_type_code}-{correlative:08d}"
            )
        return f"CFE-{correlative:08d}"

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

        number = self.format_invoice_number(self.next_correlative)
        self.next_correlative += 1
        self.save(update_fields=["next_correlative"])
        return number

    def contingency_config(self):
        """Datos públicos del rango de contingencia para exponer al POS (para facturar sin internet)."""
        if not (
            self.contingency_enabled
            and self.contingency_range_start
            and self.contingency_range_end
            and self.contingency_next_correlative
        ):
            return None
        return {
            "next": self.contingency_next_correlative,
            "range_end": self.contingency_range_end,
            "establishment_code": self.establishment_code,
            "emission_point_code": self.emission_point_code,
            "document_type_code": self.document_type_code,
            "regime": self.invoice_regime,
            "business_name": self.trade_name or self.business_name or "Mini Market",
            "rtn": self.rtn,
            "address": self.address,
            "receipt_format": self.receipt_format,
        }

    def reserve_contingency_correlative(self, correlative):
        """Valida un correlativo de contingencia asignado por el cliente sin conexión y devuelve el número
        de factura formateado. Lanza ValidationError si la contingencia no está activa, el número está fuera
        de rango o ya fue usado."""
        if not self.contingency_enabled:
            raise ValidationError("La facturación en contingencia sin internet no está activada en este negocio.")
        if not (self.contingency_range_start and self.contingency_range_end):
            raise ValidationError("El rango de contingencia no está configurado.")
        if not (self.contingency_range_start <= correlative <= self.contingency_range_end):
            raise ValidationError("El número de contingencia está fuera del rango autorizado.")
        return self.format_invoice_number(correlative)

    def register_contingency_use(self, correlative):
        """Avanza el próximo correlativo de contingencia si el usado fue mayor o igual al esperado. No falla si
        llegan sincronizaciones fuera de orden."""
        if self.contingency_next_correlative is not None and correlative >= self.contingency_next_correlative:
            self.contingency_next_correlative = correlative + 1
            self.save(update_fields=["contingency_next_correlative"])


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
