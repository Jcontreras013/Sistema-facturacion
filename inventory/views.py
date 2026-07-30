from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CategoryForm, ProductForm, ProviderForm, StockMovementForm
from .models import Category, Product, Provider, StockMovement


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


@login_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Producto '{product.name}' creado correctamente.")
            return redirect("inventory:product_list")
    else:
        form = ProductForm()
    return render(request, "inventory/product_form.html", {"form": form, "title": "Nuevo producto"})


@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Producto '{product.name}' actualizado.")
            return redirect("inventory:product_list")
    else:
        form = ProductForm(instance=product)
    return render(
        request, "inventory/product_form.html", {"form": form, "title": f"Editar producto: {product.name}"}
    )


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        name = product.name
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
def category_list(request):
    categories = Category.objects.all()
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría creada.")
            return redirect("inventory:category_list")
    else:
        form = CategoryForm()
    return render(request, "inventory/category_list.html", {"categories": categories, "form": form})


@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        category.delete()
        messages.success(request, "Categoría eliminada.")
    return redirect("inventory:category_list")


@login_required
def provider_list(request):
    providers = Provider.objects.all()
    return render(request, "inventory/provider_list.html", {"providers": providers})


@login_required
def provider_create(request):
    if request.method == "POST":
        form = ProviderForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor creado correctamente.")
            return redirect("inventory:provider_list")
    else:
        form = ProviderForm()
    return render(request, "inventory/provider_form.html", {"form": form, "title": "Nuevo proveedor"})


@login_required
def provider_update(request, pk):
    provider = get_object_or_404(Provider, pk=pk)
    if request.method == "POST":
        form = ProviderForm(request.POST, instance=provider)
        if form.is_valid():
            form.save()
            messages.success(request, "Proveedor actualizado.")
            return redirect("inventory:provider_list")
    else:
        form = ProviderForm(instance=provider)
    return render(
        request, "inventory/provider_form.html", {"form": form, "title": f"Editar proveedor: {provider.name}"}
    )


@login_required
def provider_delete(request, pk):
    provider = get_object_or_404(Provider, pk=pk)
    if request.method == "POST":
        provider.delete()
        messages.success(request, "Proveedor eliminado.")
        return redirect("inventory:provider_list")
    return render(request, "inventory/provider_confirm_delete.html", {"provider": provider})
