from django.conf import settings
from django.db import models


class Mesa(models.Model):

    class Estado(models.TextChoices):
        LIBRE = 'libre', 'Libre'
        OCUPADA = 'ocupada', 'Ocupada'
        RESERVADA = 'reservada', 'Reservada'

    numero = models.IntegerField(unique=True)
    capacidad = models.IntegerField()
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.LIBRE
    )
    qr_code = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'mesa'
        verbose_name = 'Mesa'
        verbose_name_plural = 'Mesas'

    def __str__(self):
        return f'Mesa {self.numero} — {self.estado}'


class Solicitud(models.Model):
    """Aviso que el cliente envía desde la carta: llamar al garzón o pedir la cuenta."""

    class Tipo(models.TextChoices):
        GARZON = 'garzon', 'Llamar al garzón'
        CUENTA = 'cuenta', 'Pedir la cuenta'

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        ATENDIDA = 'atendida', 'Atendida'

    mesa = models.ForeignKey(
        Mesa,
        on_delete=models.CASCADE,
        related_name='solicitudes'
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    atendida_en = models.DateTimeField(null=True, blank=True)
    atendida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_atendidas'
    )

    class Meta:
        db_table = 'solicitud'
        verbose_name = 'Solicitud de mesa'
        verbose_name_plural = 'Solicitudes de mesa'
        ordering = ['creada_en']

    def __str__(self):
        return f'Mesa {self.mesa.numero} — {self.get_tipo_display()} — {self.estado}'
