from django.contrib import admin

from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("number", "client", "user", "payment_method", "status", "total", "created_at")
    list_filter = ("status", "payment_method")
    search_fields = ("number",)
    date_hierarchy = "created_at"
    inlines = [SaleItemInline]
