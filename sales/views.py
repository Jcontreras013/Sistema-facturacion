import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date

from clients.models import Client
from core.audit import log_action
from core.models import Company
from core.permissions import admin_required
from inventory.models import Product, StockMovement

from .models import CashSession, CreditNote, CreditNoteItem, HeldSale, Sale, SaleItem


def _get_open_session():
    return CashSession.objects.filter(closed_at__isnull=True).order_by("-opened_at").first()


def _create_sale(
    user, open_session, cart, client_id, client_rtn, new_client_name, payment_method, notes,
    mixed_cash_amount=None, mixed_other_amount=None,
):
    """Crea una venta a partir de un carrito ya validado. Lanza ValueError/InvalidOperation/KeyError/Http404 en caso de error."""
    with transaction.atomic():
        if client_id == "__new__":
            if new_client_name:
                new_client = Client.objects.create(name=new_client_name, document=client_rtn)
                log_action(user, "created", new_client, extra="Creado desde el POS")
                client_id = new_client.pk
            else:
                client_id = None
        elif client_id and client_rtn:
            Client.objects.filter(pk=client_id, document="").update(document=client_rtn)

        credit_client = None
        credit_available = None
        if payment_method == "credito":
            if not client_id:
                raise ValueError("Selecciona un cliente para vender al crédito (fiado).")
            credit_client = get_object_or_404(Client, pk=client_id)
            if not credit_client.has_credit_enabled:
                raise ValueError(
                    f"'{credit_client.name}' no tiene crédito habilitado. Configura su límite de crédito en Clientes."
                )
            credit_available = credit_client.credit_available()

        sale = Sale.objects.create(
            client_id=client_id,
            user=user,
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
                unit_price=product.price_for_quantity(quantity),
                tax_rate=product.tax_rate,
            )
            StockMovement.objects.create(
                product=product,
                movement_type="out",
                reason_category="venta",
                quantity=quantity,
                reason=f"Venta {sale.number if sale.number else sale.pk}",
                user=user,
            )
        sale.recalculate_totals()

        if payment_method == "credito" and sale.total > credit_available:
            raise ValueError(
                f"'{credit_client.name}' no tiene suficiente crédito disponible "
                f"(disponible: L {credit_available:.2f}, venta: L {sale.total:.2f})."
            )

        if payment_method == "mixto":
            if mixed_cash_amount is None or mixed_other_amount is None:
                raise ValueError("Ingresa el monto en efectivo y el monto del otro método para un pago mixto.")
            combined = mixed_cash_amount + mixed_other_amount
            if abs(combined - sale.total) > Decimal("0.01"):
                raise ValueError(
                    f"La suma de los montos (L {combined:.2f}) no coincide con el total de la venta (L {sale.total:.2f})."
                )
            sale.mixed_cash_amount = mixed_cash_amount
            sale.mixed_other_amount = mixed_other_amount
            sale.save(update_fields=["mixed_cash_amount", "mixed_other_amount"])
    log_action(user, "created", sale)
    return sale


def _sale_redirect_url(sale):
    sale_url = reverse("sales:sale_detail", args=[sale.pk])
    if Company.load().auto_print_on_sale:
        sale_url += "?autoprint=1"
    return sale_url


@login_required
def pos(request):
    open_session = _get_open_session()
    if not open_session:
        messages.warning(request, "No hay una caja abierta. Abre la caja antes de registrar ventas.")
        return redirect("sales:cash_session_open")

    if request.method == "POST":
        cart_raw = request.POST.get("cart_data", "[]")
        client_id = request.POST.get("client_id") or None
        client_rtn = request.POST.get("client_rtn", "").strip()
        new_client_name = request.POST.get("new_client_name", "").strip()
        payment_method = request.POST.get("payment_method", "efectivo")
        notes = request.POST.get("notes", "")
        mixed_cash_amount = request.POST.get("mixed_cash_amount") or None
        mixed_other_amount = request.POST.get("mixed_other_amount") or None

        try:
            cart = json.loads(cart_raw)
        except json.JSONDecodeError:
            cart = []

        if not cart:
            messages.error(request, "Agrega al menos un producto a la venta.")
            return redirect("sales:pos")

        try:
            sale = _create_sale(
                request.user, open_session, cart, client_id, client_rtn, new_client_name, payment_method, notes,
                mixed_cash_amount=Decimal(mixed_cash_amount) if mixed_cash_amount else None,
                mixed_other_amount=Decimal(mixed_other_amount) if mixed_other_amount else None,
            )
        except (ValueError, InvalidOperation, KeyError) as exc:
            messages.error(request, str(exc) or "No se pudo completar la venta.")
            return redirect("sales:pos")

        request.session["last_sale_id"] = sale.pk
        messages.success(request, f"Venta {sale.number} registrada correctamente.")
        return redirect(_sale_redirect_url(sale))

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
            "unit_code": p.unit,
            "wholesale_price": str(p.wholesale_price) if p.wholesale_price else "",
            "wholesale_min_qty": str(p.wholesale_min_qty) if p.wholesale_min_qty else "",
        }
        for p in products
    ]
    clients = Client.objects.filter(is_active=True).order_by("name")
    clients_data = [
        {
            "id": c.id,
            "name": c.name,
            "document": c.document or "",
            "credit_limit": str(c.credit_limit),
            "credit_available": str(c.credit_available()),
        }
        for c in clients
    ]
    return render(
        request,
        "sales/pos.html",
        {
            "products_json": json.dumps(products_data),
            "clients_json": json.dumps(clients_data),
            "payment_methods": Sale.PAYMENT_METHODS,
            "open_session": open_session,
        },
    )


@login_required
def pos_checkout_api(request):
    """Endpoint JSON usado por el POS (en línea y para sincronizar ventas que quedaron pendientes sin conexión)."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    open_session = _get_open_session()
    if not open_session:
        return JsonResponse(
            {"ok": False, "error": "No hay una caja abierta.", "code": "no_session"}, status=409
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "Datos inválidos."}, status=400)

    cart = payload.get("cart") or []
    client_id = payload.get("client_id") or None
    client_rtn = (payload.get("client_rtn") or "").strip()
    new_client_name = (payload.get("new_client_name") or "").strip()
    payment_method = payload.get("payment_method") or "efectivo"
    notes = payload.get("notes") or ""
    mixed_cash_amount = payload.get("mixed_cash_amount")
    mixed_other_amount = payload.get("mixed_other_amount")

    if not cart:
        return JsonResponse({"ok": False, "error": "Agrega al menos un producto a la venta."}, status=400)

    try:
        sale = _create_sale(
            request.user, open_session, cart, client_id, client_rtn, new_client_name, payment_method, notes,
            mixed_cash_amount=Decimal(str(mixed_cash_amount)) if mixed_cash_amount not in (None, "") else None,
            mixed_other_amount=Decimal(str(mixed_other_amount)) if mixed_other_amount not in (None, "") else None,
        )
    except (ValueError, InvalidOperation, KeyError, Http404) as exc:
        return JsonResponse({"ok": False, "error": str(exc) or "No se pudo completar la venta."}, status=400)

    request.session["last_sale_id"] = sale.pk
    return JsonResponse({"ok": True, "sale_number": sale.number, "redirect_url": _sale_redirect_url(sale)})


@login_required
def pos_hold_api(request):
    """Guarda el carrito actual del cajero como una venta en espera, para atender a otro cliente."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "Datos inválidos."}, status=400)

    cart = payload.get("cart") or []
    if not cart:
        return JsonResponse({"ok": False, "error": "No hay productos en el carrito para suspender."}, status=400)

    held = HeldSale.objects.create(
        user=request.user,
        client_id=payload.get("client_id") or "",
        client_name=payload.get("client_name") or "",
        client_rtn=payload.get("client_rtn") or "",
        new_client_name=payload.get("new_client_name") or "",
        payment_method=payload.get("payment_method") or "efectivo",
        notes=payload.get("notes") or "",
        cart_json=json.dumps(cart),
    )
    return JsonResponse({"ok": True, "id": held.pk})


@login_required
def pos_held_list_api(request):
    held_sales = HeldSale.objects.filter(user=request.user).order_by("-created_at")
    data = []
    for h in held_sales:
        try:
            cart = json.loads(h.cart_json)
        except json.JSONDecodeError:
            cart = []
        data.append(
            {
                "id": h.pk,
                "client_name": h.client_name or "Consumidor final",
                "item_count": len(cart),
                "created_at": h.created_at.strftime("%d/%m/%Y %H:%M"),
            }
        )
    return JsonResponse({"ok": True, "held": data})


@login_required
def pos_held_recall_api(request, pk):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    held = get_object_or_404(HeldSale, pk=pk, user=request.user)
    try:
        cart = json.loads(held.cart_json)
    except json.JSONDecodeError:
        cart = []
    data = {
        "cart": cart,
        "client_id": held.client_id,
        "client_name": held.client_name,
        "client_rtn": held.client_rtn,
        "new_client_name": held.new_client_name,
        "payment_method": held.payment_method,
        "notes": held.notes,
    }
    held.delete()
    return JsonResponse({"ok": True, "sale": data})


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale.objects.select_related("client", "user"), pk=pk)
    company = Company.load()
    autoprint = request.GET.get("autoprint") == "1" and company.auto_print_on_sale
    reprint = request.GET.get("reprint") == "1"
    return render(
        request,
        "sales/sale_detail.html",
        {"sale": sale, "company": company, "autoprint": autoprint, "reprint": reprint},
    )


@login_required
def reprint_last_sale(request):
    """Atajo para el cajero: reimprimir la última factura que cobró, sin ir al historial."""
    last_sale_id = request.session.get("last_sale_id")
    if not last_sale_id or not Sale.objects.filter(pk=last_sale_id).exists():
        messages.info(request, "Todavía no has cobrado ninguna venta en esta sesión para reimprimir.")
        return redirect("sales:pos")
    return redirect(reverse("sales:sale_detail", args=[last_sale_id]) + "?reprint=1")


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
        log_action(request.user, "updated", sale, extra="Venta anulada")
        messages.success(request, f"Venta {sale.number} anulada. El stock fue restituido.")
    return redirect("sales:sale_detail", pk=sale.pk)


@admin_required
def sale_delete(request, pk):
    sale = get_object_or_404(Sale, pk=pk)

    if sale.credit_notes.exists():
        messages.error(
            request,
            "No puedes eliminar esta venta porque tiene notas de crédito asociadas. "
            "Elimina primero esas notas de crédito.",
        )
        return redirect("sales:sale_detail", pk=sale.pk)

    if request.method == "POST":
        number = sale.number
        with transaction.atomic():
            if sale.status == "completada":
                for item in sale.items.all():
                    StockMovement.objects.create(
                        product=item.product,
                        movement_type="in",
                        reason_category="otro",
                        quantity=item.quantity,
                        reason=f"Eliminación de venta {sale.number}",
                        user=request.user,
                    )
            log_action(request.user, "deleted", sale)
            sale.delete()
        messages.success(request, f"Venta {number} eliminada. El stock fue restituido si era necesario.")
        return redirect("sales:sale_list")

    return render(request, "sales/sale_confirm_delete.html", {"sale": sale})


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
        session = CashSession.objects.create(opened_by=request.user, opening_amount=opening_amount)
        log_action(request.user, "created", session)
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
        log_action(request.user, "updated", session, extra="Caja cerrada")
        messages.success(request, f"Caja cerrada. Diferencia: L {session.difference:.2f}")
        return redirect("sales:cash_session_list")

    return render(request, "sales/cash_session_close.html", {"session": session, "expected": expected})


@admin_required
def cash_session_list(request):
    sessions = CashSession.objects.select_related("opened_by", "closed_by").all()
    return render(request, "sales/cash_session_list.html", {"sessions": sessions})


@admin_required
def cash_session_delete(request, pk):
    session = get_object_or_404(CashSession, pk=pk)
    if request.method == "POST":
        log_action(request.user, "deleted", session)
        session.delete()
        messages.success(request, f"Sesión de caja #{pk} eliminada.")
        return redirect("sales:cash_session_list")
    return render(request, "sales/cash_session_confirm_delete.html", {"session": session})


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

        log_action(request.user, "created", credit_note, extra=reason)
        messages.success(request, f"Nota de crédito {credit_note.number} generada correctamente.")
        return redirect("sales:credit_note_detail", pk=credit_note.pk)

    return redirect("sales:sale_detail", pk=sale.pk)


@login_required
def credit_note_detail(request, pk):
    credit_note = get_object_or_404(
        CreditNote.objects.select_related("sale", "user"), pk=pk
    )
    return render(
        request, "sales/credit_note_detail.html", {"credit_note": credit_note, "company": Company.load()}
    )


@admin_required
def credit_note_delete(request, pk):
    credit_note = get_object_or_404(CreditNote, pk=pk)
    if request.method == "POST":
        number = credit_note.number
        sale = credit_note.sale
        with transaction.atomic():
            for item in credit_note.items.select_related("sale_item__product"):
                StockMovement.objects.create(
                    product=item.sale_item.product,
                    movement_type="out",
                    reason_category="otro",
                    quantity=item.quantity,
                    reason=f"Eliminación de nota de crédito {credit_note.number}",
                    user=request.user,
                )
            log_action(request.user, "deleted", credit_note)
            credit_note.delete()
        messages.success(request, f"Nota de crédito {number} eliminada. El stock devuelto fue revertido.")
        return redirect("sales:sale_detail", pk=sale.pk)
    return render(request, "sales/credit_note_confirm_delete.html", {"credit_note": credit_note})
