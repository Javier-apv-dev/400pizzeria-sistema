from django.db import models
from apps.pedidos.models import Pedido


class Pago(models.Model):

    class MetodoPago(models.TextChoices):
        EFECTIVO = 'efectivo', 'Efectivo'
        DEBITO = 'debito', 'Débito'
        CREDITO = 'credito', 'Crédito'
        TRANSFERENCIA = 'transferencia', 'Transferencia'

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        COMPLETADO = 'completado', 'Completado'
        ANULADO = 'anulado', 'Anulado'

    metodo_pago = models.CharField(
        max_length=50,
        choices=MetodoPago.choices
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.PROTECT,
        related_name='pago'
    )

    class Meta:
        db_table = 'pago'
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'

    def __str__(self):
        return f'Pago #{self.id} — {self.metodo_pago} — {self.estado}'