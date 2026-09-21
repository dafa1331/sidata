from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test

def role_required(*allowed_roles):
    """
    Mengecek apakah user adalah superuser, atau memiliki salah satu group yang diizinkan,
    atau termasuk dalam role 'Operator' (yang memiliki akses luas kecuali manajemen user).
    """
    def check_role(user):
        if not user.is_authenticated:
            return False
        # Superuser dan Operator punya akses umum
        if user.is_superuser or user.groups.filter(name='Operator').exists():
            return True
        # Cek apakah user masuk ke salah satu role spesifik yang didaftarkan
        if user.groups.filter(name__in=allowed_roles).exists():
            return True
        raise PermissionDenied
    return user_passes_test(check_role)