from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

ADMIN_GROUP = "Administrador"
CASHIER_GROUP = "Cajero"


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name=ADMIN_GROUP).exists())


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, "Esta sección es solo para administradores.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper
