from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("configuracion/", views.company_settings, name="company_settings"),
    path("usuarios/", views.user_list, name="user_list"),
    path("usuarios/nuevo/", views.user_create, name="user_create"),
    path("usuarios/<int:pk>/editar/", views.user_update, name="user_update"),
    path("usuarios/<int:pk>/eliminar/", views.user_delete, name="user_delete"),
    path("bitacora/", views.audit_log_list, name="audit_log_list"),
]
