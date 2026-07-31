import datetime
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render

from core.permissions import admin_required
from inventory.models import Product
from sales.models import CashSession, Sale, SaleItem


def _parse_range(request):
    from django.utils.dateparse import parse_date

    today = datetime.date.today()
    date_from = parse_date(request.GET.get("from", "")) or today.replace(day=1)
    date_to = parse_date(request.GET.get("to", "")) or today
    return date_from, date_to


@admin_required
def sales_report(request):
    date_from, date_to = _parse_range(request)
    sales = Sale.objects.filter(
        created_at__date__gte=date_from, created_at__date__lte=date_to, status="completada"
    )
    totals = sales.aggregate(
        total_ventas=Sum("total"), total_subtotal=Sum("subtotal"), total_tax=Sum("tax")
    )
    daily = (
        sales.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum("total"))
        .order_by("day")
    )
    return render(
        request,
        "reports/sales_report.html",
        {
            "date_from": date_from,
            "date_to": date_to,
            "sales_count": sales.count(),
            "totals": totals,
            "daily": daily,
        },
    )


@admin_required
def top_products_report(request):
    date_from, date_to = _parse_range(request)
    items = SaleItem.objects.filter(
        sale__created_at__date__gte=date_from,
        sale__created_at__date__lte=date_to,
        sale__status="completada",
    )
    line_total = ExpressionWrapper(F("quantity") * F("unit_price"), output_field=DecimalField(max_digits=12, decimal_places=2))
    top = (
        items.values("product__id", "product__name", "product__code")
        .annotate(total_quantity=Sum("quantity"), total_revenue=Sum(line_total))
        .order_by("-total_quantity")[:15]
    )
    return render(
        request,
        "reports/top_products.html",
        {"date_from": date_from, "date_to": date_to, "top": top},
    )


@admin_required
def profit_report(request):
    date_from, date_to = _parse_range(request)
    items = SaleItem.objects.filter(
        sale__created_at__date__gte=date_from,
        sale__created_at__date__lte=date_to,
        sale__status="completada",
    ).select_related("product")

    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    for item in items:
        revenue = item.quantity * item.unit_price
        cost = item.quantity * item.product.purchase_price
        total_revenue += revenue
        total_cost += cost
    total_profit = total_revenue - total_cost

    return render(
        request,
        "reports/profit_report.html",
        {
            "date_from": date_from,
            "date_to": date_to,
            "total_revenue": total_revenue,
            "total_cost": total_cost,
            "total_profit": total_profit,
        },
    )


@admin_required
def low_stock_report(request):
    products = Product.objects.filter(is_active=True).order_by("stock")
    low_stock = [p for p in products if p.is_low_stock]
    return render(request, "reports/low_stock_report.html", {"products": low_stock})


@admin_required
def expiring_products_report(request):
    products = Product.objects.filter(is_active=True, expiration_date__isnull=False).order_by("expiration_date")
    expiring = [p for p in products if p.is_expiring_soon or p.is_expired]
    return render(request, "reports/expiring_products_report.html", {"products": expiring})


@admin_required
def tax_report(request):
    """Resumen de ISV cobrado por tasa, útil para la declaración ante el SAR."""
    date_from, date_to = _parse_range(request)
    items = SaleItem.objects.filter(
        sale__created_at__date__gte=date_from,
        sale__created_at__date__lte=date_to,
        sale__status="completada",
    )
    by_rate = (
        items.values("tax_rate")
        .annotate(
            subtotal=Sum(
                ExpressionWrapper(F("quantity") * F("unit_price"), output_field=DecimalField(max_digits=12, decimal_places=2))
            ),
        )
        .order_by("tax_rate")
    )
    rows = []
    total_tax = Decimal("0")
    for row in by_rate:
        rate = row["tax_rate"]
        subtotal = row["subtotal"] or Decimal("0")
        tax_amount = (subtotal * rate / Decimal("100")).quantize(Decimal("0.01"))
        total_tax += tax_amount
        rows.append({"tax_rate": rate, "subtotal": subtotal, "tax_amount": tax_amount})

    return render(
        request,
        "reports/tax_report.html",
        {"date_from": date_from, "date_to": date_to, "rows": rows, "total_tax": total_tax},
    )


@admin_required
def cash_flow_report(request):
    date_from, date_to = _parse_range(request)
    sessions = CashSession.objects.filter(
        opened_at__date__gte=date_from, opened_at__date__lte=date_to
    ).select_related("opened_by", "closed_by")
    return render(
        request,
        "reports/cash_flow_report.html",
        {"date_from": date_from, "date_to": date_to, "sessions": sessions},
    )
