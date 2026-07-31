from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from core.audit import log_action

from .forms import ClientForm
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
    return render(request, "clients/client_detail.html", {"client": client, "sales": sales})


@login_required
def client_create(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            log_action(request.user, "created", client)
            messages.success(request, f"Cliente '{client.name}' creado correctamente.")
            return redirect("clients:client_list")
    else:
        form = ClientForm()
    return render(request, "clients/client_form.html", {"form": form, "title": "Nuevo cliente"})


@login_required
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            log_action(request.user, "updated", client)
            messages.success(request, "Cliente actualizado.")
            return redirect("clients:client_list")
    else:
        form = ClientForm(instance=client)
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
