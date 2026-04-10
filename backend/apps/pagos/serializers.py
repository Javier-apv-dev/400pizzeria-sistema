from rest_framework import serializers
from apps.pagos.models import Pago
from apps.pedidos.serializers import PedidoSerializer


class PagoSerializer(serializers.ModelSerializer):
    pedido = PedidoSerializer(read_only=True)
    pedido_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Pago
        fields = [
            'id',
            'metodo_pago',
            'monto',
            'fecha',
            'estado',
            'pedido',
            'pedido_id'
        ]
        read_only_fields = ['fecha']

    def validate_pedido_id(self, value):
        from apps.pedidos.models import Pedido
        try:
            pedido = Pedido.objects.get(pk=value)
        except Pedido.DoesNotExist:
            raise serializers.ValidationError('El pedido no existe')

        if hasattr(pedido, 'pago'):
            raise serializers.ValidationError(
                'Este pedido ya tiene un pago registrado'
            )
        return value

    def validate_monto(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'El monto debe ser mayor a 0'
            )
        return value