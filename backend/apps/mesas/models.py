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