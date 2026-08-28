from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("productos/", views.product_list, name="product_list"),
    path("productos/nuevo/", views.product_create, name="product_create"),
    path("productos/importar/", views.product_import, name="product_import"),
    path("productos/importar/mapear/", views.product_import_map, name="product_import_map"),
    path("productos/verificar-codigo-barras/", views.product_check_barcode, name="product_check_barcode"),
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
    path("ordenes-compra/", views.purchase_order_list, name="purchase_order_list"),
    path("ordenes-compra/nueva/", views.purchase_order_create, name="purchase_order_create"),
    path("ordenes-compra/<int:pk>/", views.purchase_order_detail, name="purchase_order_detail"),
    path("ordenes-compra/<int:pk>/agregar-producto/", views.purchase_order_add_item, name="purchase_order_add_item"),
    path(
        "ordenes-compra/<int:pk>/quitar-producto/<int:item_pk>/",
        views.purchase_order_remove_item,
        name="purchase_order_remove_item",
    ),
    path("ordenes-compra/<int:pk>/enviar/", views.purchase_order_send, name="purchase_order_send"),
    path("ordenes-compra/<int:pk>/recibir/", views.purchase_order_receive, name="purchase_order_receive"),
    path("ordenes-compra/<int:pk>/cancelar/", views.purchase_order_cancel, name="purchase_order_cancel"),
    path("ordenes-compra/<int:pk>/eliminar/", views.purchase_order_delete, name="purchase_order_delete"),
    path("conteos/", views.inventory_count_list, name="inventory_count_list"),
    path("conteos/nuevo/", views.inventory_count_create, name="inventory_count_create"),
    path("conteos/<int:pk>/", views.inventory_count_detail, name="inventory_count_detail"),
    path("conteos/<int:pk>/hoja/", views.inventory_count_print, name="inventory_count_print"),
    path("conteos/<int:pk>/guardar/", views.inventory_count_save, name="inventory_count_save"),
    path("conteos/<int:pk>/cerrar/", views.inventory_count_close, name="inventory_count_close"),
    path("conteos/<int:pk>/eliminar/", views.inventory_count_delete, name="inventory_count_delete"),
]
