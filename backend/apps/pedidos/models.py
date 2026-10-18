from django.db import models, transaction
from django.utils import timezone
from apps.mesas.models import Mesa
from apps.usuarios.models import Usuario
from apps.productos.models import Producto


class Pedido(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        EN_PREPARACION = 'en_preparacion', 'En Preparación'
        LISTO = 'listo', 'Listo'
        ENTREGADO = 'entregado', 'Entregado'

    estado = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mesa = models.ForeignKey(
        Mesa,
        on_delete=models.PROTECT,
        related_name='pedidos'
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='pedidos',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'pedido'
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

    def __str__(self):
        return f'Pedido #{self.id} — Mesa {self.mesa.numero} — {self.estado}'

    def registrar_estado(self, nuevo_estado, usuario=None):
        """Cambia el estado, lo deja en el historial y libera la mesa al entregar.

        Devuelve False, sin cambiar nada, si otro usuario cambió el estado del pedido
        después de que este se leyó (dos avances simultáneos del mismo pedido).
        """
        with transaction.atomic():
            # Actualización condicional: solo cambia si el pedido sigue en el estado leído
            cambiados = Pedido.objects.filter(
                pk=self.pk, estado=self.estado
            ).update(estado=nuevo_estado)
            if not cambiados:
                self.refresh_from_db(fields=['estado'])
                return False

            self.estado = nuevo_estado
            HistorialEstadoPedido.objects.create(
                pedido=self,
                estado=nuevo_estado,
                usuario=usuario
            )

            # Si era el último pedido activo de la mesa, la mesa queda libre
            if nuevo_estado == self.Estado.ENTREGADO:
                quedan_activos = Pedido.objects.filter(
                    mesa=self.mesa
                ).exclude(estado=self.Estado.ENTREGADO).exists()
                if not quedan_activos:
                    self.mesa.estado = Mesa.Estado.LIBRE
                    self.mesa.save(update_fields=['estado'])
        return True


class HistorialEstadoPedido(models.Model):
    """Cada cambio de estado de un pedido: cuándo y quién lo hizo."""
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    estado = models.CharField(max_length=30, choices=Pedido.Estado.choices)
    # default y no auto_now_add, para poder reconstruir el historial de pedidos antiguos
    fecha = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        related_name='cambios_estado',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'historial_estado_pedido'
        verbose_name = 'Historial de estado de pedido'
        verbose_name_plural = 'Historial de estados de pedido'
        ordering = ['fecha', 'id']

    def __str__(self):
        return f'Pedido #{self.pedido_id} → {self.estado} ({self.fecha:%d-%m %H:%M})'


class DetallePedido(models.Model):
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    # Indicaciones del cliente para cocina ("sin cebolla", "bien cocida")
    nota = models.CharField(max_length=140, blank=True, default='')
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='detalles'
    )

    class Meta:
        db_table = 'detalle_pedido'
        verbose_name = 'Detalle de Pedido'
        verbose_name_plural = 'Detalles de Pedido'

    def __str__(self):
        return f'{self.cantidad}x {self.producto.nombre} — Pedido #{self.pedido.id}'