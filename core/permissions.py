from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

ADMIN_GROUP = "Supervisor"
CASHIER_GROUP = "Caja"


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name=ADMIN_GROUP).exists())


def is_protected_admin(user):
    """El Admin (creador del sistema) es el/los superusuario(s): nadie más puede editarlos ni eliminarlos."""
    return bool(user and user.is_superuser)


def can_manage_user(actor, target):
    """Un usuario puede gestionar (editar/eliminar) a otro salvo que el objetivo sea el Admin del sistema
    y quien actúa no sea esa misma cuenta."""
    if is_protected_admin(target) and target.pk != actor.pk:
        return False
    return True


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, "Esta sección es solo para administradores.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper
