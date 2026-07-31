import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from clients.models import Client
from core.permissions import admin_required
from inventory.models import Product, StockMovement

from .models import CashSession, CreditNote, CreditNoteItem, Sale, SaleItem


def _get_open_session():
    return CashSession.objects.filter(closed_at__isnull=True).order_by("-opened_at").first()


@login_required
def pos(request):
    open_session = _get_open_session()
    if not open_session:
        messages.warning(request, "No hay una caja abierta. Abre la caja antes de registrar ventas.")
        return redirect("sales:cash_session_open")

    if request.method == "POST":
        cart_raw = request.POST.get("cart_data", "[]")
        client_id = request.POST.get("client_id") or None
        payment_method = request.POST.get("payment_method", "efectivo")
        notes = request.POST.get("notes", "")

        try:
            cart = json.loads(cart_raw)
        except json.JSONDecodeError:
            cart = []

        if not cart:
            messages.error(request, "Agrega al menos un producto a la venta.")
            return redirect("sales:pos")

        try:
            with transaction.atomic():
                sale = Sale.objects.create(
                    client_id=client_id,
                    user=request.user,
                    payment_method=payment_method,
                    notes=notes,
                    cash_session=open_session,
                )
                for entry in cart:
                    product = get_object_or_404(Product, pk=entry["id"])
                    quantity = Decimal(str(entry["quantity"]))
                    if quantity <= 0:
                        raise ValueError(f"Cantidad inválida para {product.name}.")
                    if quantity > product.stock:
                        raise ValueError(f"Stock insuficiente para '{product.name}' (disponible: {product.stock}).")
                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=quantity,
                        unit_price=product.sale_price,
                        tax_rate=product.tax_rate,
                    )
                    StockMovement.objects.create(
                        product=product,
                        movement_type="out",
                        reason_category="venta",
                        quantity=quantity,
                        reason=f"Venta {sale.number if sale.number else sale.pk}",
                        user=request.user,
                    )
                sale.recalculate_totals()
        except (ValueError, InvalidOperation, KeyError) as exc:
            messages.error(request, str(exc) or "No se pudo completar la venta.")
            return redirect("sales:pos")

        messages.success(request, f"Venta {sale.number} registrada correctamente.")
        return redirect("sales:sale_detail", pk=sale.pk)

    products = Product.objects.filter(is_active=True, stock__gt=0).order_by("name")
    products_data = [
        {
            "id": p.id,
            "code": p.code,
            "barcode": p.barcode or "",
            "name": p.name,
            "price": str(p.sale_price),
            "tax_rate": str(p.tax_rate),
            "stock": str(p.stock),
            "unit": p.get_unit_display(),
        }
        for p in products
    ]
    clients = Client.objects.filter(is_active=True).order_by("name")
    return render(
        request,
        "sales/pos.html",
        {
            "products_json": json.dumps(products_data),
            "clients": clients,
            "payment_methods": Sale.PAYMENT_METHODS,
            "open_session": open_session,
        },
    )


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.select_related("client", "user"), pk=pk)
    return render(request, "sales/sale_detail.html", {"sale": sale})


@login_required
def sale_list(request):
    sales = Sale.objects.select_related("client", "user").all()

    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    client_query = request.GET.get("q", "").strip()

    if date_from:
        parsed = parse_date(date_from)
        if parsed:
            sales = sales.filter(created_at__date__gte=parsed)
    if date_to:
        parsed = parse_date(date_to)
        if parsed:
            sales = sales.filter(created_at__date__lte=parsed)
    if client_query:
        sales = sales.filter(client__name__icontains=client_query)

    return render(
        request,
        "sales/sale_list.html",
        {"sales": sales, "date_from": date_from or "", "date_to": date_to or "", "query": client_query},
    )


@admin_required
def sale_cancel(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == "POST" and sale.status == "completada":
        with transaction.atomic():
            for item in sale.items.all():
                StockMovement.objects.create(
                    product=item.product,
                    movement_type="in",
                    reason_category="devolucion",
                    quantity=item.quantity,
                    reason=f"Anulación venta {sale.number}",
                    user=request.user,
                )
            sale.status = "anulada"
            sale.save(update_fields=["status"])
        messages.success(request, f"Venta {sale.number} anulada. El stock fue restituido.")
    return redirect("sales:sale_detail", pk=sale.pk)


@login_required
def cash_session_open(request):
    existing = _get_open_session()
    if existing:
        messages.info(request, "Ya hay una caja abierta.")
        return redirect("sales:pos")

    if request.method == "POST":
        try:
            opening_amount = Decimal(request.POST.get("opening_amount", "0"))
        except InvalidOperation:
            opening_amount = Decimal("0")
        CashSession.objects.create(opened_by=request.user, opening_amount=opening_amount)
        messages.success(request, "Caja abierta correctamente.")
        return redirect("sales:pos")

    return render(request, "sales/cash_session_open.html")


@login_required
def cash_session_close(request):
    session = _get_open_session()
    if not session:
        messages.info(request, "No hay ninguna caja abierta.")
        return redirect("sales:pos")

    expected = session.opening_amount + session.cash_sales_total()

    if request.method == "POST":
        try:
            counted_amount = Decimal(request.POST.get("counted_amount", "0"))
        except InvalidOperation:
            counted_amount = Decimal("0")
        notes = request.POST.get("notes", "")
        session.close(counted_amount=counted_amount, closed_by=request.user, notes=notes)
        messages.success(request, f"Caja cerrada. Diferencia: L {session.difference:.2f}")
        return redirect("sales:cash_session_list")

    return render(request, "sales/cash_session_close.html", {"session": session, "expected": expected})


@admin_required
def cash_session_list(request):
    sessions = CashSession.objects.select_related("opened_by", "closed_by").all()
    return render(request, "sales/cash_session_list.html", {"sessions": sessions})


@login_required
def credit_note_create(request, sale_pk):
    sale = get_object_or_404(Sale, pk=sale_pk)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        item_ids = request.POST.getlist("item_id")
        quantities = request.POST.getlist("quantity")

        if not reason:
            messages.error(request, "Indica el motivo de la devolución.")
            return redirect("sales:sale_detail", pk=sale.pk)

        try:
            with transaction.atomic():
                credit_note = CreditNote.objects.create(sale=sale, user=request.user, reason=reason)
                created_any = False
                for item_id, qty_raw in zip(item_ids, quantities):
                    qty_raw = (qty_raw or "").strip()
                    if not qty_raw:
                        continue
                    quantity = Decimal(qty_raw)
                    if quantity <= 0:
                        continue
                    sale_item = get_object_or_404(SaleItem, pk=item_id, sale=sale)
                    if quantity > sale_item.returnable_quantity:
                        raise ValueError(
                            f"No puedes devolver más de {sale_item.returnable_quantity} de '{sale_item.product.name}'."
                        )
                    CreditNoteItem.objects.create(
                        credit_note=credit_note,
                        sale_item=sale_item,
                        quantity=quantity,
                        unit_price=sale_item.unit_price,
                        tax_rate=sale_item.tax_rate,
                    )
                    StockMovement.objects.create(
                        product=sale_item.product,
                        movement_type="in",
                        reason_category="devolucion",
                        quantity=quantity,
                        reason=f"Nota de crédito {credit_note.number} (venta {sale.number})",
                        user=request.user,
                    )
                    created_any = True

                if not created_any:
                    raise ValueError("Indica al menos una cantidad a devolver.")

                credit_note.recalculate_totals()
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("sales:sale_detail", pk=sale.pk)

        messages.success(request, f"Nota de crédito {credit_note.number} generada correctamente.")
        return redirect("sales:credit_note_detail", pk=credit_note.pk)

    return redirect("sales:sale_detail", pk=sale.pk)


@login_required
def credit_note_detail(request, pk):
    credit_note = get_object_or_404(
        CreditNote.objects.select_related("sale", "user"), pk=pk
    )
    return render(request, "sales/credit_note_detail.html", {"credit_note": credit_note})
