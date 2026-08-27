from django.contrib import admin

from .models import CashSession, CreditNote, CreditNoteItem, HeldSale, Sale, SaleItem


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


@admin.register(CashSession)
class CashSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "opened_by", "opened_at", "opening_amount", "closed_at", "counted_amount", "difference")
    list_filter = ("opened_at",)


class CreditNoteItemInline(admin.TabularInline):
    model = CreditNoteItem
    extra = 0


@admin.register(HeldSale)
class HeldSaleAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "client_name", "payment_method", "created_at")


@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    list_display = ("number", "sale", "user", "total", "created_at")
    search_fields = ("number",)
    date_hierarchy = "created_at"
    inlines = [CreditNoteItemInline]
