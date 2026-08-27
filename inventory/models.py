import datetime
from decimal import Decimal

from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField("Nombre", max_length=100, unique=True)
    description = models.CharField("Descripción", max_length=255, blank=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Provider(models.Model):
    name = models.CharField("Nombre / Razón social", max_length=150)
    contact_name = models.CharField("Persona de contacto", max_length=150, blank=True)
    phone = models.CharField("Teléfono", max_length=30, blank=True)
    email = models.EmailField("Correo", blank=True)
    address = models.CharField("Dirección", max_length=255, blank=True)
    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    UNIT_CHOICES = [
        ("unidad", "Unidad"),
        ("lb", "Libra"),
        ("kg", "Kilogramo"),
        ("caja", "Caja"),
        ("litro", "Litro"),
        ("paquete", "Paquete"),
    ]

    code = models.CharField("Código / SKU", max_length=50, unique=True)
    barcode = models.CharField("Código de barras", max_length=64, unique=True, null=True, blank=True)
    name = models.CharField("Nombre", max_length=150)
    category = models.ForeignKey(
        Category, verbose_name="Categoría", on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    provider = models.ForeignKey(
        Provider, verbose_name="Proveedor", on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    unit = models.CharField("Unidad de medida", max_length=20, choices=UNIT_CHOICES, default="unidad")
    purchase_price = models.DecimalField("Precio de compra", max_digits=10, decimal_places=2, default=0)
    sale_price = models.DecimalField("Precio de venta", max_digits=10, decimal_places=2, default=0)
    wholesale_price = models.DecimalField(
        "Precio de mayoreo", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Precio por unidad cuando se compra desde la cantidad mínima de mayoreo. Déjalo vacío para no ofrecer mayoreo.",
    )
    wholesale_min_qty = models.DecimalField(
        "Cantidad mínima de mayoreo", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="A partir de esta cantidad se aplica automáticamente el precio de mayoreo en el POS.",
    )
    tax_rate = models.DecimalField(
        "Tasa de ISV (%)", max_digits=5, decimal_places=2, default=Decimal("15.00"),
        help_text="15% para la mayoría de productos, 18% para bebidas alcohólicas y tabaco.",
    )
    stock = models.DecimalField("Existencias", max_digits=10, decimal_places=2, default=0)
    min_stock = models.DecimalField("Stock mínimo", max_digits=10, decimal_places=2, default=5)
    expiration_date = models.DateField("Fecha de vencimiento", null=True, blank=True)
    is_active = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_absolute_url(self):
        return reverse("inventory:product_detail", args=[self.pk])

    @property
    def is_low_stock(self):
        return self.stock <= self.min_stock

    @property
    def has_wholesale_price(self):
        return bool(self.wholesale_price and self.wholesale_min_qty)

    def price_for_quantity(self, quantity):
        if self.has_wholesale_price and quantity >= self.wholesale_min_qty:
            return self.wholesale_price
        return self.sale_price

    @property
    def profit_margin(self):
        if self.purchase_price:
            return ((self.sale_price - self.purchase_price) / self.purchase_price) * 100
        return 0

    @property
    def is_expired(self):
        return bool(self.expiration_date and self.expiration_date < datetime.date.today())

    @property
    def is_expiring_soon(self):
        if not self.expiration_date:
            return False
        delta = (self.expiration_date - datetime.date.today()).days
        return 0 <= delta <= 30


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ("in", "Entrada"),
        ("out", "Salida"),
        ("adjust", "Ajuste"),
    ]
    REASON_CATEGORIES = [
        ("compra", "Compra / reabastecimiento"),
        ("venta", "Venta"),
        ("merma", "Merma"),
        ("dano", "Producto dañado"),
        ("robo", "Robo / faltante"),
        ("devolucion", "Devolución de cliente"),
        ("otro", "Otro"),
    ]

    product = models.ForeignKey(Product, verbose_name="Producto", on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField("Tipo", max_length=10, choices=MOVEMENT_TYPES)
    reason_category = models.CharField(
        "Categoría de motivo", max_length=15, choices=REASON_CATEGORIES, default="otro"
    )
    quantity = models.DecimalField("Cantidad", max_digits=10, decimal_places=2)
    reason = models.CharField("Detalle del motivo", max_length=255, blank=True)
    user = models.ForeignKey(
        "auth.User", verbose_name="Usuario", on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField("Fecha", auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} ({self.quantity})"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            if self.movement_type == "in":
                self.product.stock += self.quantity
            elif self.movement_type == "out":
                self.product.stock -= self.quantity
            elif self.movement_type == "adjust":
                self.product.stock = self.quantity
            self.product.save(update_fields=["stock"])
