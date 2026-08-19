import datetime
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render

from clients.models import Client
from core.permissions import admin_required
from inventory.models import Product
from sales.models import CashSession, CreditNoteItem, Sale, SaleItem

from .exports import xlsx_response


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

    if request.GET.get("export") == "xlsx":
        rows = [(day["day"].strftime("%d/%m/%Y"), float(day["total"])) for day in daily]
        rows.append(("TOTAL", float(totals["total_ventas"] or 0)))
        return xlsx_response(
            f"ventas_{date_from}_{date_to}.xlsx", ["Fecha", "Total (L)"], rows, "Ventas por período"
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

    if request.GET.get("export") == "xlsx":
        rows = [
            (p["product__code"], p["product__name"], float(p["total_quantity"]), float(p["total_revenue"]))
            for p in top
        ]
        return xlsx_response(
            f"productos_top_{date_from}_{date_to}.xlsx",
            ["Código", "Producto", "Cantidad vendida", "Ingresos (L)"],
            rows,
            "Productos más vendidos",
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

    if request.GET.get("export") == "xlsx":
        rows = [
            ("Ingresos", float(total_revenue)),
            ("Costo", float(total_cost)),
            ("Ganancia", float(total_profit)),
        ]
        return xlsx_response(
            f"ganancias_{date_from}_{date_to}.xlsx", ["Concepto", "Monto (L)"], rows, "Ganancias"
        )

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

    if request.GET.get("export") == "xlsx":
        rows = [(p.code, p.name, float(p.stock), float(p.min_stock)) for p in low_stock]
        return xlsx_response(
            "stock_bajo.xlsx", ["Código", "Producto", "Stock", "Mínimo"], rows, "Stock bajo"
        )

    return render(request, "reports/low_stock_report.html", {"products": low_stock})


@admin_required
def expiring_products_report(request):
    products = Product.objects.filter(is_active=True, expiration_date__isnull=False).order_by("expiration_date")
    expiring = [p for p in products if p.is_expiring_soon or p.is_expired]

    if request.GET.get("export") == "xlsx":
        rows = [
            (
                p.code,
                p.name,
                p.expiration_date.strftime("%d/%m/%Y"),
                "Vencido" if p.is_expired else "Por vencer",
            )
            for p in expiring
        ]
        return xlsx_response(
            "productos_por_vencer.xlsx",
            ["Código", "Producto", "Fecha de vencimiento", "Estado"],
            rows,
            "Por vencer",
        )

    return render(request, "reports/expiring_products_report.html", {"products": expiring})


@admin_required
def tax_report(request):
    """Resumen de ISV (débito fiscal neto de devoluciones) por tasa, para la declaración mensual ante el SAR."""
    date_from, date_to = _parse_range(request)
    line_total = ExpressionWrapper(
        F("quantity") * F("unit_price"), output_field=DecimalField(max_digits=12, decimal_places=2)
    )

    sales_by_rate = {
        row["tax_rate"]: row["subtotal"] or Decimal("0")
        for row in (
            SaleItem.objects.filter(
                sale__created_at__date__gte=date_from,
                sale__created_at__date__lte=date_to,
                sale__status="completada",
            )
            .values("tax_rate")
            .annotate(subtotal=Sum(line_total))
        )
    }
    # Las notas de crédito descuentan del período en que se emiten (no del de la venta original).
    credit_notes_by_rate = {
        row["tax_rate"]: row["subtotal"] or Decimal("0")
        for row in (
            CreditNoteItem.objects.filter(
                credit_note__created_at__date__gte=date_from,
                credit_note__created_at__date__lte=date_to,
            )
            .values("tax_rate")
            .annotate(subtotal=Sum(line_total))
        )
    }

    rows = []
    total_sales_base = total_credit_base = total_net_base = total_tax = Decimal("0")
    for rate in sorted(set(sales_by_rate) | set(credit_notes_by_rate)):
        sales_base = sales_by_rate.get(rate, Decimal("0"))
        credit_base = credit_notes_by_rate.get(rate, Decimal("0"))
        net_base = sales_base - credit_base
        tax_amount = (net_base * rate / Decimal("100")).quantize(Decimal("0.01"))
        total_sales_base += sales_base
        total_credit_base += credit_base
        total_net_base += net_base
        total_tax += tax_amount
        rows.append(
            {
                "tax_rate": rate,
                "sales_base": sales_base,
                "credit_base": credit_base,
                "net_base": net_base,
                "tax_amount": tax_amount,
            }
        )

    if request.GET.get("export") == "xlsx":
        xlsx_rows = [
            (
                f"{row['tax_rate']:.0f}%",
                float(row["sales_base"]),
                float(row["credit_base"]),
                float(row["net_base"]),
                float(row["tax_amount"]),
            )
            for row in rows
        ]
        xlsx_rows.append(
            (
                "TOTAL",
                float(total_sales_base),
                float(total_credit_base),
                float(total_net_base),
                float(total_tax),
            )
        )
        return xlsx_response(
            f"isv_{date_from}_{date_to}.xlsx",
            ["Tasa ISV", "Ventas gravadas (L)", "Notas de crédito (L)", "Base neta (L)", "ISV a declarar (L)"],
            xlsx_rows,
            "ISV",
        )

    return render(
        request,
        "reports/tax_report.html",
        {
            "date_from": date_from,
            "date_to": date_to,
            "rows": rows,
            "total_sales_base": total_sales_base,
            "total_credit_base": total_credit_base,
            "total_net_base": total_net_base,
            "total_tax": total_tax,
        },
    )


@admin_required
def cash_flow_report(request):
    date_from, date_to = _parse_range(request)
    sessions = CashSession.objects.filter(
        opened_at__date__gte=date_from, opened_at__date__lte=date_to
    ).select_related("opened_by", "closed_by")

    if request.GET.get("export") == "xlsx":
        rows = [
            (
                session.pk,
                str(session.opened_by) if session.opened_by else "",
                session.opened_at.strftime("%d/%m/%Y %H:%M"),
                str(session.closed_by) if session.closed_by else "",
                session.closed_at.strftime("%d/%m/%Y %H:%M") if session.closed_at else "",
                float(session.opening_amount),
                float(session.cash_sales_total()),
                float(session.expected_amount) if session.expected_amount is not None else "",
                float(session.counted_amount) if session.counted_amount is not None else "",
                float(session.difference) if session.difference is not None else "",
            )
            for session in sessions
        ]
        return xlsx_response(
            f"flujo_caja_{date_from}_{date_to}.xlsx",
            ["Sesión", "Abierta por", "Apertura", "Cerrada por", "Cierre", "Monto inicial (L)", "Ventas efectivo (L)", "Esperado (L)", "Contado (L)", "Diferencia (L)"],
            rows,
            "Flujo de caja",
        )

    return render(
        request,
        "reports/cash_flow_report.html",
        {"date_from": date_from, "date_to": date_to, "sessions": sessions},
    )


@admin_required
def accounts_receivable_report(request):
    """Clientes con saldo pendiente por ventas al crédito (fiado)."""
    rows = []
    total_receivable = Decimal("0")
    for client in Client.objects.filter(credit_limit__gt=0).order_by("name"):
        balance = client.credit_balance()
        if balance > 0:
            total_receivable += balance
            rows.append(
                {
                    "client": client,
                    "balance": balance,
                    "limit": client.credit_limit,
                    "available": client.credit_limit - balance,
                }
            )
    rows.sort(key=lambda r: r["balance"], reverse=True)

    if request.GET.get("export") == "xlsx":
        xlsx_rows = [
            (row["client"].name, float(row["balance"]), float(row["limit"]), float(row["available"]))
            for row in rows
        ]
        xlsx_rows.append(("TOTAL", float(total_receivable), "", ""))
        return xlsx_response(
            "cuentas_por_cobrar.xlsx",
            ["Cliente", "Debe (L)", "Límite (L)", "Disponible (L)"],
            xlsx_rows,
            "Cuentas por cobrar",
        )

    return render(
        request,
        "reports/accounts_receivable_report.html",
        {"rows": rows, "total_receivable": total_receivable},
    )
