from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "document", "phone", "email", "is_active")
    search_fields = ("name", "document")
    list_filter = ("is_active",)
