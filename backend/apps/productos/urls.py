from django.urls import path
from apps.productos.views import (
    CategoriaListView,
    CategoriaDetailView,
    ProductoListView,
    ProductoDetailView
)

urlpatterns = [
    path('categorias/', CategoriaListView.as_view(), name='categorias'),
    path('categorias/<int:pk>/', CategoriaDetailView.as_view(), name='categoria-detail'),
    path('productos/', ProductoListView.as_view(), name='productos'),
    path('productos/<int:pk>/', ProductoDetailView.as_view(), name='producto-detail'),
]