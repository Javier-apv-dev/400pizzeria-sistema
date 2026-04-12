from django.urls import path
from apps.pagos.views import (
    PagoListView,
    PagoDetailView,
    PagoAnularView,
    PagoDeleteView
)

urlpatterns = [
    path('pagos/', PagoListView.as_view(), name='pagos'),
    path('pagos/<int:pk>/', PagoDetailView.as_view(), name='pago-detail'),
    path('pagos/<int:pk>/anular/', PagoAnularView.as_view(), name='pago-anular'),
    path('pagos/<int:pk>/eliminar/', PagoDeleteView.as_view(), name='pago-delete'),
]