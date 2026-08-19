from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from core.audit import log_action
from core.permissions import is_admin

from .forms import ClientForm, CreditPaymentForm
from .models import Client


@login_required
def client_list(request):
    query = request.GET.get("q", "").strip()
    clients = Client.objects.all()
    if query:
        clients = clients.filter(Q(name__icontains=query) | Q(document__icontains=query))
    return render(request, "clients/client_list.html", {"clients": clients, "query": query})


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    sales = client.sales.all()[:20]
    credit_sales = client.sales.filter(payment_method="credito").order_by("-created_at")[:20]
    payments = client.credit_payments.select_related("user")[:20]
    return render(
        request,
        "clients/client_detail.html",
        {
            "client": client,
            "sales": sales,
            "credit_sales": credit_sales,
            "payments": payments,
            "credit_balance": client.credit_balance(),
            "credit_available": client.credit_available(),
        },
    )


@login_required
def client_create(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if not is_admin(request.user):
            form.fields.pop("credit_limit", None)
        if form.is_valid():
            client = form.save()
            log_action(request.user, "created", client)
            messages.success(request, f"Cliente '{client.name}' creado correctamente.")
            return redirect("clients:client_list")
    else:
        form = ClientForm()
        if not is_admin(request.user):
            form.fields.pop("credit_limit", None)
    return render(request, "clients/client_form.html", {"form": form, "title": "Nuevo cliente"})


@login_required
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if not is_admin(request.user):
            form.fields.pop("credit_limit", None)
        if form.is_valid():
            form.save()
            log_action(request.user, "updated", client)
            messages.success(request, "Cliente actualizado.")
            return redirect("clients:client_list")
    else:
        form = ClientForm(instance=client)
        if not is_admin(request.user):
            form.fields.pop("credit_limit", None)
    return render(request, "clients/client_form.html", {"form": form, "title": f"Editar cliente: {client.name}"})


@login_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        name = client.name
        log_action(request.user, "deleted", client)
        client.delete()
        messages.success(request, f"Cliente '{name}' eliminado.")
        return redirect("clients:client_list")
    return render(request, "clients/client_confirm_delete.html", {"client": client})


@login_required
def credit_payment_create(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        form = CreditPaymentForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            balance = client.credit_balance()
            if amount > balance:
                messages.error(
                    request,
                    f"El abono (L {amount:.2f}) es mayor que el saldo pendiente de '{client.name}' (L {balance:.2f}).",
                )
            else:
                payment = form.save(commit=False)
                payment.client = client
                payment.user = request.user
                payment.save()
                log_action(request.user, "created", payment)
                messages.success(request, f"Abono de L {amount:.2f} registrado para '{client.name}'.")
                return redirect("clients:client_detail", pk=client.pk)
    else:
        form = CreditPaymentForm()
    return render(
        request,
        "clients/credit_payment_form.html",
        {"form": form, "client": client, "balance": client.credit_balance()},
    )
