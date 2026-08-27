from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("pos/", views.pos, name="pos"),
    path("pos/api/checkout/", views.pos_checkout_api, name="pos_checkout_api"),
    path("pos/reimprimir-ultima/", views.reprint_last_sale, name="reprint_last_sale"),
    path("pos/api/suspender/", views.pos_hold_api, name="pos_hold_api"),
    path("pos/api/en-espera/", views.pos_held_list_api, name="pos_held_list_api"),
    path("pos/api/en-espera/<int:pk>/recuperar/", views.pos_held_recall_api, name="pos_held_recall_api"),
    path("pos/api/autorizar-descuento/", views.pos_authorize_discount_api, name="pos_authorize_discount_api"),
    path("caja/abrir/", views.cash_session_open, name="cash_session_open"),
    path("caja/cerrar/", views.cash_session_close, name="cash_session_close"),
    path("caja/<int:pk>/eliminar/", views.cash_session_delete, name="cash_session_delete"),
    path("caja/", views.cash_session_list, name="cash_session_list"),
    path("notas-credito/<int:sale_pk>/nueva/", views.credit_note_create, name="credit_note_create"),
    path("notas-credito/<int:pk>/eliminar/", views.credit_note_delete, name="credit_note_delete"),
    path("notas-credito/<int:pk>/", views.credit_note_detail, name="credit_note_detail"),
    path("", views.sale_list, name="sale_list"),
    path("<int:pk>/", views.sale_detail, name="sale_detail"),
    path("<int:pk>/anular/", views.sale_cancel, name="sale_cancel"),
    path("<int:pk>/eliminar/", views.sale_delete, name="sale_delete"),
]
