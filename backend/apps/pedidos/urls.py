from django.urls import path
from apps.pedidos.views import (
    PedidoListView,
    PedidoDetailView,
    PedidoEstadoView
)

urlpatterns = [
    path('pedidos/', PedidoListView.as_view(), name='pedidos'),
    path('pedidos/<int:pk>/', PedidoDetailView.as_view(), name='pedido-detail'),
    path('pedidos/<int:pk>/estado/', PedidoEstadoView.as_view(), name='pedido-estado'),
]