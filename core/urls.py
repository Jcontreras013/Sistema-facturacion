from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("configuracion/", views.company_settings, name="company_settings"),
]
