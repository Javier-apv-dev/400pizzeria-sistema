from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Módulo de usuarios y autenticación
    path('api/auth/', include('apps.usuarios.urls')),

    # Módulo de productos y categorías
    path('api/', include('apps.productos.urls')),

    # Módulo de mesas
    path('api/', include('apps.mesas.urls')),

    # Módulo de pedidos
    path('api/', include('apps.pedidos.urls')),

    # Módulo de pagos
    path('api/', include('apps.pagos.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)