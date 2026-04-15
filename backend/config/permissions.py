from rest_framework.permissions import BasePermission


class EsAdministrador(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.rol and
            request.user.rol.nombre == 'Administrador'
        )


class EsGarzon(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.rol and
            request.user.rol.nombre == 'Garzon'
        )


class EsCocina(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.rol and
            request.user.rol.nombre == 'Cocina'
        )
    
class EsPersonal(BasePermission):
    """Cualquier usuario autenticado con rol asignado"""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.rol is not None
        )

class EsAdminOGarzon(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.rol and
            request.user.rol.nombre in ['Administrador', 'Garzon']
        )

class EsAdminOCocina(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.rol and
            request.user.rol.nombre in ['Administrador', 'Cocina']
        )