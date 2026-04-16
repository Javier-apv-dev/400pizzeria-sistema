from django.urls import path
from apps.productos.views import (
    CategoriaListView,
    CategoriaDetailView,
    CategoriaEstadoView,
    ProductoListView,
    ProductoDetailView
)

urlpatterns = [
    path('categorias/', CategoriaListView.as_view(), name='categorias'),
    path('categorias/<int:pk>/', CategoriaDetailView.as_view(), name='categoria-detail'),
    path('categorias/<int:pk>/estado/', CategoriaEstadoView.as_view(), name='categoria-estado'),
    path('productos/', ProductoListView.as_view(), name='productos'),
    path('productos/<int:pk>/', ProductoDetailView.as_view(), name='producto-detail'),
]