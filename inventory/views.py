import os
import tempfile
import uuid
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from core.audit import log_action
from core.models import AuditLog
from core.permissions import admin_required

from .forms import CategoryForm, ProductForm, PromotionForm, ProviderForm, StockMovementForm
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
from .models import Category, Product, Promotion, Provider, StockMovement

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
