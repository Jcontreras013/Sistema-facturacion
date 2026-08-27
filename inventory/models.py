import datetime
from decimal import Decimal

from django.conf import settings
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

    def active_promotion(self):
        today = datetime.date.today()
        query = models.Q(product=self)
        if self.category_id:
            query |= models.Q(category_id=self.category_id)
        return (
            Promotion.objects.filter(query, is_active=True, start_date__lte=today, end_date__gte=today)
            .order_by("-discount_percent")
            .first()
        )

    def price_for_quantity(self, quantity):
        if self.has_wholesale_price and quantity >= self.wholesale_min_qty:
            return self.wholesale_price
        promo = self.active_promotion()
        if promo:
            discounted = self.sale_price * (Decimal("100") - promo.discount_percent) / Decimal("100")
            return discounted.quantize(Decimal("0.01"))
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


class Promotion(models.Model):
    name = models.CharField("Nombre de la promoción", max_length=150)
    product = models.ForeignKey(
        Product, verbose_name="Producto", on_delete=models.CASCADE, null=True, blank=True, related_name="promotions"
    )
    category = models.ForeignKey(
        Category, verbose_name="Categoría", on_delete=models.CASCADE, null=True, blank=True, related_name="promotions"
    )
    discount_percent = models.DecimalField("Descuento (%)", max_digits=5, decimal_places=2)
    start_date = models.DateField("Fecha de inicio")
    end_date = models.DateField("Fecha de fin")
    is_active = models.BooleanField("Activa", default=True)
    created_at = models.DateTimeField("Creada", auto_now_add=True)

    class Meta:
        verbose_name = "Promoción"
        verbose_name_plural = "Promociones"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.product_id and not self.category_id:
            raise ValidationError("Selecciona un producto o una categoría para la promoción.")
        if self.product_id and self.category_id:
            raise ValidationError("Elige solo un producto o una categoría, no ambos.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("La fecha de fin debe ser igual o posterior a la fecha de inicio.")

    @property
    def is_current(self):
        today = datetime.date.today()
        return self.is_active and self.start_date <= today <= self.end_date

    @property
    def applies_to(self):
        return self.product.name if self.product else f"Categoría: {self.category.name}"


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ("borrador", "Borrador"),
        ("enviada", "Enviada al proveedor"),
        ("recibida", "Recibida"),
        ("cancelada", "Cancelada"),
    ]

    number = models.CharField("No. de orden", max_length=20, unique=True, blank=True)
    provider = models.ForeignKey(
        Provider, verbose_name="Proveedor", on_delete=models.PROTECT, related_name="purchase_orders"
    )
    status = models.CharField("Estado", max_length=15, choices=STATUS_CHOICES, default="borrador")
    notes = models.CharField("Notas", max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Creada por", on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField("Creada", auto_now_add=True)
    received_at = models.DateTimeField("Recibida", null=True, blank=True)

    class Meta:
        verbose_name = "Orden de compra"
        verbose_name_plural = "Órdenes de compra"
        ordering = ["-created_at"]

    def __str__(self):
        return self.number or f"OC-{self.pk}"

    def save(self, *args, **kwargs):
        if not self.number:
            last = PurchaseOrder.objects.order_by("-id").first()
            next_id = (last.id + 1) if last else 1
            self.number = f"OC-{next_id:06d}"
        super().save(*args, **kwargs)

    @property
    def total_cost(self):
        return sum((item.subtotal for item in self.items.all()), Decimal("0"))

    @property
    def is_fully_received(self):
        items = list(self.items.all())
        return bool(items) and all(item.quantity_received >= item.quantity_ordered for item in items)


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, verbose_name="Producto", on_delete=models.PROTECT, related_name="purchase_order_items"
    )
    quantity_ordered = models.DecimalField("Cantidad pedida", max_digits=10, decimal_places=2)
    quantity_received = models.DecimalField("Cantidad recibida", max_digits=10, decimal_places=2, default=0)
    unit_cost = models.DecimalField("Costo unitario", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Detalle de orden de compra"
        verbose_name_plural = "Detalles de orden de compra"

    def __str__(self):
        return f"{self.product.name} x {self.quantity_ordered}"

    @property
    def subtotal(self):
        return self.quantity_ordered * self.unit_cost

    @property
    def pending_quantity(self):
        return self.quantity_ordered - self.quantity_received


class InventoryCount(models.Model):
    STATUS_CHOICES = [
        ("abierto", "Abierto"),
        ("cerrado", "Cerrado"),
    ]

    status = models.CharField("Estado", max_length=10, choices=STATUS_CHOICES, default="abierto")
    notes = models.CharField("Notas", max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Creado por", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inventory_counts",
    )
    created_at = models.DateTimeField("Creado", auto_now_add=True)
    closed_at = models.DateTimeField("Cerrado", null=True, blank=True)

    class Meta:
        verbose_name = "Conteo físico de inventario"
        verbose_name_plural = "Conteos físicos de inventario"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Conteo #{self.pk}"

    @property
    def items_with_difference(self):
        return [item for item in self.items.all() if item.difference not in (None, Decimal("0"))]


class InventoryCountItem(models.Model):
    inventory_count = models.ForeignKey(InventoryCount, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, verbose_name="Producto", on_delete=models.PROTECT, related_name="count_items")
    system_stock = models.DecimalField("Stock en sistema", max_digits=10, decimal_places=2)
    counted_stock = models.DecimalField("Stock contado", max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "Detalle de conteo"
        verbose_name_plural = "Detalles de conteo"
        ordering = ["product__name"]

    def __str__(self):
        return f"{self.product.name}: sistema {self.system_stock}, contado {self.counted_stock}"

    @property
    def difference(self):
        if self.counted_stock is None:
            return None
        return self.counted_stock - self.system_stock
