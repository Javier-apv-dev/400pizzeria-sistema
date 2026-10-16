from django.urls import path
from apps.mesas.views import (
    MesaListView,
    MesaDetailView,
    MesaEstadoView,
    MesaQRView,
    SolicitudCrearView,
    SolicitudListView,
    SolicitudAtenderView
)

urlpatterns = [
    path('mesas/', MesaListView.as_view(), name='mesas'),
    path('mesas/<int:pk>/', MesaDetailView.as_view(), name='mesa-detail'),
    path('mesas/<int:pk>/estado/', MesaEstadoView.as_view(), name='mesa-estado'),
    path('mesas/<int:pk>/qr/', MesaQRView.as_view(), name='mesa-qr'),
    path('mesas/<int:pk>/solicitudes/', SolicitudCrearView.as_view(), name='mesa-solicitudes'),
    path('solicitudes/', SolicitudListView.as_view(), name='solicitudes'),
    path('solicitudes/<int:pk>/atender/', SolicitudAtenderView.as_view(), name='solicitud-atender'),
]
