from django.contrib import admin

from .models import Category, Product, Promotion, PurchaseOrder, PurchaseOrderItem, Provider, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_name", "phone", "email", "is_active")
    search_fields = ("name", "contact_name")
    list_filter = ("is_active",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "code", "barcode", "name", "category", "provider", "sale_price", "tax_rate",
        "stock", "min_stock", "expiration_date", "is_active",
    )
    search_fields = ("code", "barcode", "name")
    list_filter = ("category", "provider", "is_active")


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("name", "product", "category", "discount_percent", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "provider", "status", "created_by", "created_at")
    list_filter = ("status",)
    search_fields = ("number",)
    inlines = [PurchaseOrderItemInline]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "movement_type", "reason_category", "quantity", "user", "created_at")
    list_filter = ("movement_type", "reason_category")
    date_hierarchy = "created_at"
