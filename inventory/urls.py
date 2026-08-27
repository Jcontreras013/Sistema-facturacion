from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("productos/", views.product_list, name="product_list"),
    path("productos/nuevo/", views.product_create, name="product_create"),
    path("productos/importar/", views.product_import, name="product_import"),
    path("productos/importar/mapear/", views.product_import_map, name="product_import_map"),
    path("productos/<int:pk>/", views.product_detail, name="product_detail"),
    path("productos/<int:pk>/editar/", views.product_update, name="product_update"),
    path("productos/<int:pk>/eliminar/", views.product_delete, name="product_delete"),
    path("categorias/", views.category_list, name="category_list"),
    path("categorias/<int:pk>/eliminar/", views.category_delete, name="category_delete"),
    path("proveedores/", views.provider_list, name="provider_list"),
    path("proveedores/nuevo/", views.provider_create, name="provider_create"),
    path("proveedores/<int:pk>/editar/", views.provider_update, name="provider_update"),
    path("proveedores/<int:pk>/eliminar/", views.provider_delete, name="provider_delete"),
    path("promociones/", views.promotion_list, name="promotion_list"),
    path("promociones/nueva/", views.promotion_create, name="promotion_create"),
    path("promociones/<int:pk>/editar/", views.promotion_update, name="promotion_update"),
    path("promociones/<int:pk>/eliminar/", views.promotion_delete, name="promotion_delete"),
]
