from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from config.permissions import EsPersonal, EsAdminOGarzon, EsAdminOCocina
from config.permissions import EsAdministrador  # para el DELETE

from apps.pedidos.models import Pedido, DetallePedido
from apps.pedidos.serializers import (
    PedidoSerializer,
    CrearPedidoSerializer,
    DetallePedidoSerializer
)
from apps.productos.models import Producto
from apps.mesas.models import Mesa


class PedidoListView(APIView):

    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]  # público para carta QR
        return [EsPersonal()]   # GET → los 3 roles

    def get(self, request):
        estado = request.query_params.get('estado')
        mesa_id = request.query_params.get('mesa')

        pedidos = Pedido.objects.select_related(
            'mesa', 'usuario'
        ).prefetch_related(
            'detalles__producto'
        ).all().order_by('-fecha_creacion')

        if estado:
            pedidos = pedidos.filter(estado=estado)
        if mesa_id:
            pedidos = pedidos.filter(mesa_id=mesa_id)

        serializer = PedidoSerializer(pedidos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CrearPedidoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        mesa = Mesa.objects.get(pk=data['mesa_id'])

        # Crear el pedido
        usuario = request.user if request.user.is_authenticated else None
        pedido = Pedido.objects.create(
            mesa=mesa,
            usuario=usuario,
            estado=Pedido.Estado.PENDIENTE,
            total=0
        )

        # Crear los detalles y calcular total
        total = 0
        for item in data['productos']:
            producto = Producto.objects.get(pk=item['producto_id'])
            cantidad = int(item['cantidad'])
            precio_unitario = producto.precio
            subtotal = precio_unitario * cantidad

            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                subtotal=subtotal
            )
            total += subtotal

        # Actualizar total del pedido
        pedido.total = total
        pedido.save()

        # Actualizar estado de la mesa a ocupada
        mesa.estado = Mesa.Estado.OCUPADA
        mesa.save()

        return Response(
            PedidoSerializer(pedido).data,
            status=status.HTTP_201_CREATED
        )


class PedidoDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [EsAdminOCocina()]
        return [EsAdministrador()]  # DELETE → solo admin

    def get_object(self, pk):
        try:
            return Pedido.objects.select_related(
                'mesa', 'usuario'
            ).prefetch_related(
                'detalles__producto'
            ).get(pk=pk)
        except Pedido.DoesNotExist:
            return None

    def get(self, request, pk):
        pedido = self.get_object(pk)
        if not pedido:
            return Response(
                {'error': 'Pedido no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = PedidoSerializer(pedido)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        pedido = self.get_object(pk)
        if not pedido:
            return Response(
                {'error': 'Pedido no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        if pedido.estado != Pedido.Estado.PENDIENTE:
            return Response(
                {'error': 'Solo se pueden eliminar pedidos en estado pendiente'},
                status=status.HTTP_400_BAD_REQUEST
            )
        pedido.delete()
        return Response(
            {'mensaje': 'Pedido eliminado correctamente'},
            status=status.HTTP_200_OK
        )


class PedidoEstadoView(APIView):
    permission_classes = [EsPersonal]  # los 3 roles

    def get_object(self, pk):
        try:
            return Pedido.objects.select_related('mesa').get(pk=pk)
        except Pedido.DoesNotExist:
            return None

    def patch(self, request, pk):
        pedido = self.get_object(pk)
        if not pedido:
            return Response(
                {'error': 'Pedido no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        nuevo_estado = request.data.get('estado')
        estados_validos = [e.value for e in Pedido.Estado]

        if not nuevo_estado:
            return Response(
                {'error': 'El campo estado es obligatorio'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if nuevo_estado not in estados_validos:
            return Response(
                {'error': f'Estado inválido. Opciones: {estados_validos}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pedido.estado = nuevo_estado
        pedido.save()

        # Si el pedido fue entregado, liberar la mesa
        if nuevo_estado == Pedido.Estado.ENTREGADO:
            pedidos_activos = Pedido.objects.filter(
                mesa=pedido.mesa
            ).exclude(
                estado=Pedido.Estado.ENTREGADO
            ).exclude(pk=pedido.pk)

            if not pedidos_activos.exists():
                pedido.mesa.estado = Mesa.Estado.LIBRE
                pedido.mesa.save()

        return Response(
            PedidoSerializer(pedido).data,
            status=status.HTTP_200_OK
        )