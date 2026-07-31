from .permissions import is_admin


def role_flags(request):
    return {"is_admin": is_admin(request.user) if request.user.is_authenticated else False}
