import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from clients.models import Client
from inventory.models import Product, StockMovement

from .models import Sale, SaleItem


@login_required
def pos(request):
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
                )
                for entry in cart:
                    product = get_object_or_404(Product, pk=entry["id"])
                    quantity = Decimal(str(entry["quantity"]))
                    if quantity <= 0:
                        raise ValueError(f"Cantidad inválida para {product.name}.")
                    if quantity > product.stock:
                        raise ValueError(f"Stock insuficiente para '{product.name}' (disponible: {product.stock}).")
                    SaleItem.objects.create(
                        sale=sale, product=product, quantity=quantity, unit_price=product.sale_price
                    )
                    StockMovement.objects.create(
                        product=product,
                        movement_type="out",
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
            "name": p.name,
            "price": str(p.sale_price),
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


@login_required
def sale_cancel(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == "POST" and sale.status == "completada":
        with transaction.atomic():
            for item in sale.items.all():
                StockMovement.objects.create(
                    product=item.product,
                    movement_type="in",
                    quantity=item.quantity,
                    reason=f"Anulación venta {sale.number}",
                    user=request.user,
                )
            sale.status = "anulada"
            sale.save(update_fields=["status"])
        messages.success(request, f"Venta {sale.number} anulada. El stock fue restituido.")
    return redirect("sales:sale_detail", pk=sale.pk)
