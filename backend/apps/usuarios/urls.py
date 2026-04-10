from django.urls import path
from apps.usuarios.views import (
    LoginView,
    LogoutView,
    PerfilView,
    UsuarioListView,
    UsuarioEstadoView,
    RolListView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('usuarios/', UsuarioListView.as_view(), name='usuarios'),
    path('usuarios/<int:pk>/estado/', UsuarioEstadoView.as_view(), name='usuario-estado'),
    path('roles/', RolListView.as_view(), name='roles'),
]