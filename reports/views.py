import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils.dateparse import parse_date

from inventory.models import Product
from sales.models import Sale, SaleItem


def _parse_range(request):
    today = datetime.date.today()
    date_from = parse_date(request.GET.get("from", "")) or today.replace(day=1)
    date_to = parse_date(request.GET.get("to", "")) or today
    return date_from, date_to


@login_required
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


@login_required
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


@login_required
def profit_report(request):
    date_from, date_to = _parse_range(request)
    items = SaleItem.objects.filter(
        sale__created_at__date__gte=date_from,
        sale__created_at__date__lte=date_to,
        sale__status="completada",
    ).select_related("product")

    rows = []
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


@login_required
def low_stock_report(request):
    products = Product.objects.filter(is_active=True).order_by("stock")
    low_stock = [p for p in products if p.is_low_stock]
    return render(request, "reports/low_stock_report.html", {"products": low_stock})
