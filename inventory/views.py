import os
import tempfile
import uuid
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.audit import log_action
from core.models import AuditLog
from core.permissions import admin_required

from django.db import transaction

from .forms import CategoryForm, ProductForm, PromotionForm, PurchaseOrderForm, ProviderForm, StockMovementForm
from .importers import (
    PRODUCT_FIELDS,
    detect_column_mapping,
    generate_code,
    normalize_unit,
    parse_date_flexible,
    parse_decimal,
    parse_tax_rate,
    parse_uploaded_file,
)
from .models import (
    Category,
    InventoryCount,
    InventoryCountItem,
    Product,
    Promotion,
    Provider,
    PurchaseOrder,
    PurchaseOrderItem,
    StockMovement,
)

IMPORT_SESSION_PATH = "product_import_path"
IMPORT_SESSION_NAME = "product_import_name"


@login_required
def product_list(request):
    query = request.GET.get("q", "").strip()
    products = Product.objects.select_related("category", "provider").all()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(code__icontains=query))
    low_stock_only = request.GET.get("low_stock") == "1"
    if low_stock_only:
        products = [p for p in products if p.is_low_stock]
    return render(
        request,
        "inventory/product_list.html",
        {"products": products, "query": query, "low_stock_only": low_stock_only},
    )


@admin_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            log_action(request.user, "created", product)
            messages.success(request, f"Producto '{product.name}' creado correctamente.")
            return redirect("inventory:product_list")
    else:
        form = ProductForm()
    return render(request, "inventory/product_form.html", {"form": form, "title": "Nuevo producto"})


@admin_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            log_action(request.user, "updated", product)
            messages.success(request, f"Producto '{product.name}' actualizado.")
            return redirect("inventory:product_list")
    else:
        form = ProductForm(instance=product)
    return render(
        request, "inventory/product_form.html", {"form": form, "title": f"Editar producto: {product.name}"}
    )


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        name = product.name
        log_action(request.user, "deleted", product)
        product.delete()
        messages.success(request, f"Producto '{name}' eliminado.")
        return redirect("inventory:product_list")
    return render(request, "inventory/product_confirm_delete.html", {"product": product})


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    movements = product.movements.all()[:20]
    if request.method == "POST":
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.product = product
            movement.user = request.user
            movement.save()
            log_action(request.user, "created", movement, extra=f"Producto: {product.name}")
            messages.success(request, "Movimiento de inventario registrado.")
            return redirect("inventory:product_detail", pk=product.pk)
    else:
        form = StockMovementForm()
    return render(
        request,
        "inventory/product_detail.html",
        {"product": product, "movements": movements, "form": form},
    )


@login_required
def product_check_barcode(request):
    """Verificación en vivo desde el formulario de productos: avisa si el código de barras
    ya está registrado en otro producto, sin bloquear el guardado (algunos proveedores repiten
    el código de barras entre variantes de empaque del mismo artículo)."""
    barcode = (request.GET.get("barcode") or "").strip()
    exclude_pk = request.GET.get("exclude")
    if not barcode:
        return JsonResponse({"exists": False})
    matches = Product.objects.filter(barcode=barcode)
    if exclude_pk:
        matches = matches.exclude(pk=exclude_pk)
    match = matches.first()
    if match:
        return JsonResponse({"exists": True, "name": match.name, "code": match.code, "pk": match.pk})
    return JsonResponse({"exists": False})


@admin_required
def category_list(request):
    categories = Category.objects.all()
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            log_action(request.user, "created", category)
            messages.success(request, "Categoría creada.")
            return redirect("inventory:category_list")
    else:
        form = CategoryForm()
    return render(request, "inventory/category_list.html", {"categories": categories, "form": form})


@admin_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        log_action(request.user, "deleted", category)
        category.delete()
        messages.success(request, "Categoría eliminada.")
    return redirect("inventory:category_list")


@admin_required
def provider_list(request):
    providers = Provider.objects.all()
    return render(request, "inventory/provider_list.html", {"providers": providers})


@admin_required
def provider_create(request):
    if request.method == "POST":
        form = ProviderForm(request.POST)
        if form.is_valid():
            provider = form.save()
            log_action(request.user, "created", provider)
            messages.success(request, "Proveedor creado correctamente.")
            return redirect("inventory:provider_list")
    else:
        form = ProviderForm()
    return render(request, "inventory/provider_form.html", {"form": form, "title": "Nuevo proveedor"})


@admin_required
def provider_update(request, pk):
    provider = get_object_or_404(Provider, pk=pk)
    if request.method == "POST":
        form = ProviderForm(request.POST, instance=provider)
        if form.is_valid():
            form.save()
            log_action(request.user, "updated", provider)
            messages.success(request, "Proveedor actualizado.")
            return redirect("inventory:provider_list")
    else:
        form = ProviderForm(instance=provider)
    return render(
        request, "inventory/provider_form.html", {"form": form, "title": f"Editar proveedor: {provider.name}"}
    )


@admin_required
def provider_delete(request, pk):
    provider = get_object_or_404(Provider, pk=pk)
    if request.method == "POST":
        log_action(request.user, "deleted", provider)
        provider.delete()
        messages.success(request, "Proveedor eliminado.")
        return redirect("inventory:provider_list")
    return render(request, "inventory/provider_confirm_delete.html", {"provider": provider})


@admin_required
def promotion_list(request):
    promotions = Promotion.objects.select_related("product", "category").all()
    return render(request, "inventory/promotion_list.html", {"promotions": promotions})


@admin_required
def promotion_create(request):
    if request.method == "POST":
        form = PromotionForm(request.POST)
        if form.is_valid():
            promotion = form.save()
            log_action(request.user, "created", promotion)
            messages.success(request, f"Promoción '{promotion.name}' creada correctamente.")
            return redirect("inventory:promotion_list")
    else:
        form = PromotionForm()
    return render(request, "inventory/promotion_form.html", {"form": form, "title": "Nueva promoción"})


@admin_required
def promotion_update(request, pk):
    promotion = get_object_or_404(Promotion, pk=pk)
    if request.method == "POST":
        form = PromotionForm(request.POST, instance=promotion)
        if form.is_valid():
            form.save()
            log_action(request.user, "updated", promotion)
            messages.success(request, "Promoción actualizada.")
            return redirect("inventory:promotion_list")
    else:
        form = PromotionForm(instance=promotion)
    return render(
        request, "inventory/promotion_form.html", {"form": form, "title": f"Editar promoción: {promotion.name}"}
    )


@admin_required
def promotion_delete(request, pk):
    promotion = get_object_or_404(Promotion, pk=pk)
    if request.method == "POST":
        log_action(request.user, "deleted", promotion)
        promotion.delete()
        messages.success(request, "Promoción eliminada.")
        return redirect("inventory:promotion_list")
    return render(request, "inventory/promotion_confirm_delete.html", {"promotion": promotion})


@admin_required
def purchase_order_list(request):
    orders = PurchaseOrder.objects.select_related("provider").all()
    return render(request, "inventory/purchase_order_list.html", {"orders": orders})


@admin_required
def purchase_order_create(request):
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            order.save()
            log_action(request.user, "created", order)
            messages.success(request, f"Orden {order.number} creada. Ahora agrega los productos.")
            return redirect("inventory:purchase_order_detail", pk=order.pk)
    else:
        form = PurchaseOrderForm()
    return render(request, "inventory/purchase_order_form.html", {"form": form, "title": "Nueva orden de compra"})


@admin_required
def purchase_order_detail(request, pk):
    order = get_object_or_404(PurchaseOrder.objects.select_related("provider", "created_by"), pk=pk)
    products = Product.objects.filter(is_active=True).order_by("name")
    return render(
        request,
        "inventory/purchase_order_detail.html",
        {"order": order, "products": products},
    )


@admin_required
def purchase_order_add_item(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == "POST" and order.status == "borrador":
        product = get_object_or_404(Product, pk=request.POST.get("product"))
        try:
            quantity = Decimal(request.POST.get("quantity_ordered", "0"))
            unit_cost = Decimal(request.POST.get("unit_cost", "0"))
        except Exception:
            messages.error(request, "Cantidad o costo inválido.")
            return redirect("inventory:purchase_order_detail", pk=order.pk)
        if quantity <= 0:
            messages.error(request, "La cantidad debe ser mayor a cero.")
            return redirect("inventory:purchase_order_detail", pk=order.pk)
        PurchaseOrderItem.objects.create(
            purchase_order=order, product=product, quantity_ordered=quantity, unit_cost=unit_cost
        )
        messages.success(request, f"'{product.name}' agregado a la orden.")
    return redirect("inventory:purchase_order_detail", pk=order.pk)


@admin_required
def purchase_order_remove_item(request, pk, item_pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, pk=item_pk, purchase_order=order)
    if request.method == "POST" and order.status == "borrador":
        item.delete()
        messages.success(request, "Producto quitado de la orden.")
    return redirect("inventory:purchase_order_detail", pk=order.pk)


@admin_required
def purchase_order_send(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == "POST" and order.status == "borrador":
        if not order.items.exists():
            messages.error(request, "Agrega al menos un producto antes de enviar la orden.")
        else:
            order.status = "enviada"
            order.save(update_fields=["status"])
            log_action(request.user, "updated", order, extra="Orden enviada al proveedor")
            messages.success(request, f"Orden {order.number} marcada como enviada.")
    return redirect("inventory:purchase_order_detail", pk=order.pk)


@admin_required
def purchase_order_receive(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == "POST" and order.status in ("enviada", "recibida"):
        item_ids = request.POST.getlist("item_id")
        received_quantities = request.POST.getlist("received_quantity")
        with transaction.atomic():
            for item_id, qty_raw in zip(item_ids, received_quantities):
                qty_raw = (qty_raw or "").strip()
                if not qty_raw:
                    continue
                try:
                    entered = Decimal(qty_raw)
                except Exception:
                    continue
                if entered <= 0:
                    continue
                item = get_object_or_404(PurchaseOrderItem, pk=item_id, purchase_order=order)
                new_amount = min(entered, item.pending_quantity)
                if new_amount <= 0:
                    continue
                StockMovement.objects.create(
                    product=item.product,
                    movement_type="in",
                    reason_category="compra",
                    quantity=new_amount,
                    reason=f"Recepción de orden de compra {order.number}",
                    user=request.user,
                )
                item.quantity_received += new_amount
                item.save(update_fields=["quantity_received"])

            order.refresh_from_db()
            if order.is_fully_received:
                import django.utils.timezone as timezone

                order.status = "recibida"
                order.received_at = timezone.now()
                order.save(update_fields=["status", "received_at"])
        log_action(request.user, "updated", order, extra="Mercancía recibida")
        messages.success(request, "Recepción de mercancía registrada. El stock ya fue actualizado.")
    return redirect("inventory:purchase_order_detail", pk=order.pk)


@admin_required
def purchase_order_cancel(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == "POST" and order.status in ("borrador", "enviada"):
        order.status = "cancelada"
        order.save(update_fields=["status"])
        log_action(request.user, "updated", order, extra="Orden cancelada")
        messages.success(request, f"Orden {order.number} cancelada.")
    return redirect("inventory:purchase_order_detail", pk=order.pk)


@admin_required
def purchase_order_delete(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if order.status != "borrador":
        messages.error(request, "Solo puedes eliminar órdenes que todavía están en borrador.")
        return redirect("inventory:purchase_order_detail", pk=order.pk)
    if request.method == "POST":
        number = order.number
        log_action(request.user, "deleted", order)
        order.delete()
        messages.success(request, f"Orden {number} eliminada.")
        return redirect("inventory:purchase_order_list")
    return render(request, "inventory/purchase_order_confirm_delete.html", {"order": order})


@admin_required
def inventory_count_list(request):
    counts = InventoryCount.objects.select_related("created_by").all()
    return render(request, "inventory/inventory_count_list.html", {"counts": counts})


@admin_required
def inventory_count_create(request):
    if request.method == "POST":
        count = InventoryCount.objects.create(created_by=request.user, notes=request.POST.get("notes", ""))
        products = Product.objects.filter(is_active=True)
        InventoryCountItem.objects.bulk_create(
            [InventoryCountItem(inventory_count=count, product=p, system_stock=p.stock) for p in products]
        )
        log_action(request.user, "created", count, extra=f"{products.count()} productos")
        messages.success(request, "Conteo iniciado. Ingresa las cantidades reales que encuentres en bodega.")
        return redirect("inventory:inventory_count_detail", pk=count.pk)
    return render(request, "inventory/inventory_count_form.html")


@admin_required
def inventory_count_detail(request, pk):
    count = get_object_or_404(InventoryCount, pk=pk)
    items = count.items.select_related("product").all()
    return render(request, "inventory/inventory_count_detail.html", {"count": count, "items": items})


@admin_required
def inventory_count_save(request, pk):
    count = get_object_or_404(InventoryCount, pk=pk)
    if request.method == "POST" and count.status == "abierto":
        for item in count.items.all():
            raw = request.POST.get(f"counted_{item.pk}", "").strip()
            if raw == "":
                continue
            try:
                item.counted_stock = Decimal(raw)
            except Exception:
                continue
            item.save(update_fields=["counted_stock"])
        messages.success(request, "Conteo guardado. Puedes seguir editándolo o cerrarlo cuando termines.")
    return redirect("inventory:inventory_count_detail", pk=count.pk)


@admin_required
def inventory_count_close(request, pk):
    count = get_object_or_404(InventoryCount, pk=pk)
    if request.method == "POST" and count.status == "abierto":
        import django.utils.timezone as timezone

        with transaction.atomic():
            for item in count.items.select_related("product").all():
                if item.counted_stock is None or item.counted_stock == item.system_stock:
                    continue
                StockMovement.objects.create(
                    product=item.product,
                    movement_type="adjust",
                    reason_category="otro",
                    quantity=item.counted_stock,
                    reason=f"Ajuste por conteo físico #{count.pk}",
                    user=request.user,
                )
            count.status = "cerrado"
            count.closed_at = timezone.now()
            count.save(update_fields=["status", "closed_at"])
        log_action(request.user, "updated", count, extra="Conteo cerrado y ajustes aplicados")
        messages.success(request, "Conteo cerrado. Los ajustes de inventario ya se aplicaron.")
    return redirect("inventory:inventory_count_detail", pk=count.pk)


@admin_required
def inventory_count_delete(request, pk):
    count = get_object_or_404(InventoryCount, pk=pk)
    if count.status != "abierto":
        messages.error(request, "Solo puedes eliminar conteos que sigan abiertos (los cerrados ya afectaron el inventario).")
        return redirect("inventory:inventory_count_detail", pk=count.pk)
    if request.method == "POST":
        log_action(request.user, "deleted", count)
        count.delete()
        messages.success(request, "Conteo eliminado.")
        return redirect("inventory:inventory_count_list")
    return render(request, "inventory/inventory_count_confirm_delete.html", {"count": count})


@admin_required
def product_import(request):
    if request.method == "POST":
        upload = request.FILES.get("file")
        if not upload:
            messages.error(request, "Selecciona un archivo para importar.")
            return redirect("inventory:product_import")

        tmp_dir = os.path.join(tempfile.gettempdir(), "product_imports")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}_{upload.name}")
        with open(tmp_path, "wb") as dest:
            for chunk in upload.chunks():
                dest.write(chunk)

        request.session[IMPORT_SESSION_PATH] = tmp_path
        request.session[IMPORT_SESSION_NAME] = upload.name
        return redirect("inventory:product_import_map")

    return render(request, "inventory/product_import.html")


@admin_required
def product_import_map(request):
    tmp_path = request.session.get(IMPORT_SESSION_PATH)
    original_name = request.session.get(IMPORT_SESSION_NAME, "")
    if not tmp_path or not os.path.exists(tmp_path):
        messages.error(request, "Sube un archivo primero.")
        return redirect("inventory:product_import")

    with open(tmp_path, "rb") as f:
        headers, rows = parse_uploaded_file(f, original_name)

    if not headers:
        messages.error(request, "No se pudo leer el archivo o está vacío.")
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        request.session.pop(IMPORT_SESSION_PATH, None)
        request.session.pop(IMPORT_SESSION_NAME, None)
        return redirect("inventory:product_import")

    if request.method == "POST":
        column_for_field = {}
        for idx in range(len(headers)):
            selected = request.POST.get(f"col_{idx}")
            if selected and selected != "ignore":
                column_for_field[selected] = idx

        update_existing = request.POST.get("update_existing") == "on"
        default_category_name = request.POST.get("default_category", "").strip()

        created, updated, skipped, errors = _import_product_rows(
            rows, column_for_field, update_existing, default_category_name
        )

        AuditLog.objects.create(
            user=request.user,
            action="created",
            model_name="Producto (importación)",
            object_repr=original_name,
            extra=f"{created} creados, {updated} actualizados, {skipped} omitidos",
        )

        try:
            os.remove(tmp_path)
        except OSError:
            pass
        request.session.pop(IMPORT_SESSION_PATH, None)
        request.session.pop(IMPORT_SESSION_NAME, None)

        return render(
            request,
            "inventory/product_import_result.html",
            {
                "created": created,
                "updated": updated,
                "skipped": skipped,
                "errors": errors[:50],
                "total_errors": len(errors),
            },
        )

    detected = detect_column_mapping(headers)
    col_to_field = {idx: field for field, idx in detected.items()}
    columns = [
        {"index": i, "header": h, "detected": col_to_field.get(i, "ignore")}
        for i, h in enumerate(headers)
    ]

    return render(
        request,
        "inventory/product_import_map.html",
        {
            "columns": columns,
            "preview_rows": rows[:8],
            "total_rows": len(rows),
            "field_choices": PRODUCT_FIELDS,
            "original_name": original_name,
        },
    )


def _import_product_rows(rows, column_for_field, update_existing, default_category_name):
    created = updated = skipped = 0
    errors = []

    default_category = None
    if default_category_name:
        default_category, _ = Category.objects.get_or_create(name=default_category_name)

    category_cache = {}
    provider_cache = {}

    def get(row, field):
        idx = column_for_field.get(field)
        if idx is None or idx >= len(row):
            return ""
        return (row[idx] or "").strip()

    for row_number, row in enumerate(rows, start=2):
        name = get(row, "name")
        if not name:
            skipped += 1
            errors.append(f"Fila {row_number}: sin nombre, se omitió.")
            continue

        code = get(row, "code") or generate_code()

        category = default_category
        cat_name = get(row, "category")
        if cat_name:
            if cat_name not in category_cache:
                category_cache[cat_name], _ = Category.objects.get_or_create(name=cat_name)
            category = category_cache[cat_name]

        provider = None
        prov_name = get(row, "provider")
        if prov_name:
            if prov_name not in provider_cache:
                provider_cache[prov_name], _ = Provider.objects.get_or_create(name=prov_name)
            provider = provider_cache[prov_name]

        unit = normalize_unit(get(row, "unit"))
        purchase_price = parse_decimal(get(row, "purchase_price"))
        sale_price = parse_decimal(get(row, "sale_price"))
        tax_rate = parse_tax_rate(get(row, "tax_rate"))
        stock = parse_decimal(get(row, "stock"))
        min_stock = parse_decimal(get(row, "min_stock")) or Decimal("5")
        expiration_date = parse_date_flexible(get(row, "expiration_date"))
        barcode = get(row, "barcode") or None

        try:
            existing = Product.objects.filter(code=code).first()
            if existing and not update_existing:
                skipped += 1
                errors.append(f"Fila {row_number}: el código '{code}' ya existe, se omitió.")
                continue

            if existing:
                existing.name = name
                existing.barcode = barcode or existing.barcode
                existing.category = category or existing.category
                existing.provider = provider or existing.provider
                existing.unit = unit
                existing.purchase_price = purchase_price
                existing.sale_price = sale_price
                existing.tax_rate = tax_rate
                existing.stock = stock
                existing.min_stock = min_stock
                existing.expiration_date = expiration_date
                existing.save()
                updated += 1
            else:
                Product.objects.create(
                    code=code,
                    barcode=barcode,
                    name=name,
                    category=category,
                    provider=provider,
                    unit=unit,
                    purchase_price=purchase_price,
                    sale_price=sale_price,
                    tax_rate=tax_rate,
                    stock=stock,
                    min_stock=min_stock,
                    expiration_date=expiration_date,
                )
                created += 1
        except Exception as exc:  # noqa: BLE001 - keep importing the rest of the rows
            skipped += 1
            errors.append(f"Fila {row_number}: error al guardar ({exc}).")

    return created, updated, skipped, errors
