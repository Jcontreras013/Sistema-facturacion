from django.contrib import admin

from .models import AuditLog, Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("trade_name", "rtn", "invoice_regime", "next_correlative", "range_end")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "model_name", "object_repr")
    list_filter = ("action", "model_name")
    date_hierarchy = "created_at"
