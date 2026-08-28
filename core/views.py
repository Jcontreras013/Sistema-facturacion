import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.http import HttpResponse

from inventory.models import Product
from sales.models import CashSession, Sale

from .audit import log_action
from .forms import CompanyForm, UserCreateForm, UserUpdateForm
from .models import AuditLog, Company
from .permissions import ADMIN_GROUP, CASHIER_GROUP, admin_required, is_admin, is_protected_admin


def service_worker(request):
    content = render_to_string("sw.js", request=request)
    return HttpResponse(content, content_type="application/javascript")


@login_required
def dashboard(request):
    today = datetime.date.today()
    today_sales = Sale.objects.filter(created_at__date=today, status="completada")
    today_total = today_sales.aggregate(total=Sum("total"))["total"] or 0

    month_start = today.replace(day=1)
    month_sales = Sale.objects.filter(
        created_at__date__gte=month_start, created_at__date__lte=today, status="completada"
    )
    month_total = month_sales.aggregate(total=Sum("total"))["total"] or 0

    products = Product.objects.filter(is_active=True)
    low_stock_products = [p for p in products if p.is_low_stock][:10]
    expiring_products = [p for p in products if p.is_expiring_soon or p.is_expired][:10]
    recent_sales = Sale.objects.select_related("client", "user").all()[:8]
    open_session = CashSession.objects.filter(closed_at__isnull=True).first()

    return render(
        request,
        "core/dashboard.html",
        {
            "today_sales_count": today_sales.count(),
            "today_total": today_total,
            "month_total": month_total,
            "low_stock_products": low_stock_products,
            "low_stock_count": len(low_stock_products),
            "expiring_products": expiring_products,
            "expiring_count": len(expiring_products),
            "recent_sales": recent_sales,
            "total_products": products.count(),
            "open_session": open_session,
        },
    )


@admin_required
def company_settings(request):
    company = Company.load()
    if request.method == "POST":
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            log_action(request.user, "updated", company)
            messages.success(request, "Configuración del negocio actualizada.")
            return redirect("core:company_settings")
    else:
        form = CompanyForm(instance=company)
    return render(request, "core/company_settings.html", {"form": form, "company": company})


@admin_required
def user_list(request):
    users = User.objects.all().order_by("username")
    return render(request, "core/user_list.html", {"users": users})


@admin_required
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_action(request.user, "created", user, extra=f"Rol: {form.cleaned_data['role']}")
            messages.success(request, f"Usuario '{user.username}' creado correctamente.")
            return redirect("core:user_list")
    else:
        form = UserCreateForm()
    return render(request, "core/user_form.html", {"form": form, "title": "Nuevo usuario"})


@admin_required
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if is_protected_admin(user) and user.pk != request.user.pk:
        messages.error(request, "La cuenta del Admin (creador del sistema) no puede ser modificada por otro usuario.")
        return redirect("core:user_list")
    lock_role = is_protected_admin(user)
    current_role = ADMIN_GROUP if is_admin(user) else CASHIER_GROUP
    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=user, lock_role=lock_role)
        if form.is_valid():
            form.save()
            extra = "Admin del sistema" if lock_role else f"Rol: {form.cleaned_data['role']}"
            log_action(request.user, "updated", user, extra=extra)
            messages.success(request, f"Usuario '{user.username}' actualizado.")
            return redirect("core:user_list")
    else:
        form = UserUpdateForm(instance=user, initial={"role": current_role}, lock_role=lock_role)
    return render(
        request,
        "core/user_form.html",
        {"form": form, "title": f"Editar usuario: {user.username}", "is_protected_admin": lock_role},
    )


@admin_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if is_protected_admin(user):
        messages.error(request, "La cuenta del Admin (creador del sistema) no se puede eliminar.")
        return redirect("core:user_list")
    if request.method == "POST":
        if user.pk == request.user.pk:
            messages.error(request, "No puedes eliminar tu propio usuario.")
            return redirect("core:user_list")
        remaining_admins = (
            User.objects.exclude(pk=user.pk)
            .filter(Q(is_superuser=True) | Q(groups__name=ADMIN_GROUP))
            .distinct()
            .count()
        )
        if is_admin(user) and remaining_admins == 0:
            messages.error(request, "No puedes eliminar al único administrador del sistema.")
            return redirect("core:user_list")
        username = user.username
        log_action(request.user, "deleted", user)
        user.delete()
        messages.success(request, f"Usuario '{username}' eliminado.")
        return redirect("core:user_list")
    return render(request, "core/user_confirm_delete.html", {"user_obj": user})


@admin_required
def audit_log_list(request):
    logs = AuditLog.objects.select_related("user").all()

    action = request.GET.get("action", "")
    model_name = request.GET.get("model", "")
    if action:
        logs = logs.filter(action=action)
    if model_name:
        logs = logs.filter(model_name=model_name)

    model_choices = (
        AuditLog.objects.order_by("model_name").values_list("model_name", flat=True).distinct()
    )

    logs = logs[:300]

    return render(
        request,
        "core/audit_log_list.html",
        {
            "logs": logs,
            "action": action,
            "model_name": model_name,
            "model_choices": model_choices,
            "action_choices": AuditLog.ACTION_CHOICES,
        },
    )
