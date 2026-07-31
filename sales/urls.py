from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("pos/", views.pos, name="pos"),
    path("caja/abrir/", views.cash_session_open, name="cash_session_open"),
    path("caja/cerrar/", views.cash_session_close, name="cash_session_close"),
    path("caja/", views.cash_session_list, name="cash_session_list"),
    path("notas-credito/<int:sale_pk>/nueva/", views.credit_note_create, name="credit_note_create"),
    path("notas-credito/<int:pk>/", views.credit_note_detail, name="credit_note_detail"),
    path("", views.sale_list, name="sale_list"),
    path("<int:pk>/", views.sale_detail, name="sale_detail"),
    path("<int:pk>/anular/", views.sale_cancel, name="sale_cancel"),
]
