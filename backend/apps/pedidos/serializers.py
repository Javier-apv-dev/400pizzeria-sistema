from rest_framework import serializers
from apps.pedidos.models import Pedido, DetallePedido, HistorialEstadoPedido
from apps.productos.serializers import ProductoSerializer
from apps.mesas.serializers import MesaSerializer

NOTA_MAX = DetallePedido._meta.get_field('nota').max_length


class DetallePedidoSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)
    producto_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = DetallePedido
        fields = [
            'id',
            'producto',
            'producto_id',
            'cantidad',
            'precio_unitario',
            'subtotal',
            'nota'
        ]
        read_only_fields = ['precio_unitario', 'subtotal']


class HistorialEstadoPedidoSerializer(serializers.ModelSerializer):
    usuario = serializers.SerializerMethodField()

    class Meta:
        model = HistorialEstadoPedido
        fields = ['estado', 'fecha', 'usuario']

    def get_usuario(self, obj):
        # None cuando el cambio lo hizo el cliente desde la carta
        if not obj.usuario:
            return None
        return f'{obj.usuario.nombre} {obj.usuario.apellido}'


class PedidoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    historial = HistorialEstadoPedidoSerializer(many=True, read_only=True)
    mesa = MesaSerializer(read_only=True)
    mesa_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Pedido
        fields = [
            'id',
            'estado',
            'fecha_creacion',
            'total',
            'mesa',
            'mesa_id',
            'usuario',
            'detalles',
            'historial'
        ]
        read_only_fields = ['total', 'fecha_creacion', 'usuario']


class CrearPedidoSerializer(serializers.Serializer):
    mesa_id = serializers.IntegerField()
    productos = serializers.ListField(
        child=serializers.DictField()
    )

    def validate_mesa_id(self, value):
        from apps.mesas.models import Mesa
        try:
            Mesa.objects.get(pk=value)
        except Mesa.DoesNotExist:
            raise serializers.ValidationError('La mesa no existe')
        return value

    def validate_productos(self, value):
        from apps.productos.models import Producto
        if not value:
            raise serializers.ValidationError(
                'El pedido debe tener al menos un producto'
            )
        for item in value:
            if 'producto_id' not in item:
                raise serializers.ValidationError(
                    'Cada producto debe tener producto_id'
                )
            if 'cantidad' not in item:
                raise serializers.ValidationError(
                    'Cada producto debe tener cantidad'
                )
            if int(item['cantidad']) <= 0:
                raise serializers.ValidationError(
                    'La cantidad debe ser mayor a 0'
                )
            nota = item.get('nota', '')
            if not isinstance(nota, str):
                raise serializers.ValidationError(
                    'La nota debe ser texto'
                )
            if len(nota.strip()) > NOTA_MAX:
                raise serializers.ValidationError(
                    f'La nota no puede superar los {NOTA_MAX} caracteres'
                )
            try:
                Producto.objects.get(pk=item['producto_id'], disponible=True)
            except Producto.DoesNotExist:
                raise serializers.ValidationError(
                    f'El producto {item["producto_id"]} no existe o no está disponible'
                )
        return value