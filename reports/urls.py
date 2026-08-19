from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("ventas/", views.sales_report, name="sales_report"),
    path("productos-top/", views.top_products_report, name="top_products"),
    path("ganancias/", views.profit_report, name="profit_report"),
    path("stock-bajo/", views.low_stock_report, name="low_stock_report"),
    path("por-vencer/", views.expiring_products_report, name="expiring_products_report"),
    path("impuestos/", views.tax_report, name="tax_report"),
    path("flujo-caja/", views.cash_flow_report, name="cash_flow_report"),
    path("cuentas-por-cobrar/", views.accounts_receivable_report, name="accounts_receivable_report"),
]
