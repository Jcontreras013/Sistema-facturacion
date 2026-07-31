from .models import AuditLog


def log_action(user, action, obj, extra=""):
    model_name = obj._meta.verbose_name.title() if hasattr(obj, "_meta") else type(obj).__name__
    AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        model_name=model_name,
        object_repr=str(obj)[:255],
        object_id=str(getattr(obj, "pk", "") or ""),
        extra=extra[:255],
    )
