from django.db import models
from django.urls import reverse


class Client(models.Model):
    name = models.CharField("Nombre completo", max_length=150)
    document = models.CharField("NIT / DPI", max_length=30, blank=True)
    phone = models.CharField("Teléfono", max_length=30, blank=True)
    email = models.EmailField("Correo", blank=True)
    address = models.CharField("Dirección", max_length=255, blank=True)
    is_active = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField("Registrado", auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("clients:client_detail", args=[self.pk])
