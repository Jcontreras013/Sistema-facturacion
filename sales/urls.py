from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("pos/", views.pos, name="pos"),
    path("", views.sale_list, name="sale_list"),
    path("<int:pk>/", views.sale_detail, name="sale_detail"),
    path("<int:pk>/anular/", views.sale_cancel, name="sale_cancel"),
]
