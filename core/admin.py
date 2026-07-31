from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("trade_name", "rtn", "invoice_regime", "next_correlative", "range_end")
