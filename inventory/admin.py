from django.contrib import admin

from .models import Category, Product, Provider, StockMovement


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
    list_display = ("code", "name", "category", "provider", "sale_price", "stock", "min_stock", "is_active")
    search_fields = ("code", "name")
    list_filter = ("category", "provider", "is_active")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "movement_type", "quantity", "user", "created_at")
    list_filter = ("movement_type",)
    date_hierarchy = "created_at"
