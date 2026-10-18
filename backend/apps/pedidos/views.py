from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from config.permissions import EsPersonal, EsAdminOGarzon, EsAdminOCocina
from config.permissions import EsAdministrador  # para el DELETE

from apps.pedidos.models import Pedido, DetallePedido, HistorialEstadoPedido
from apps.pedidos.serializers import (
    PedidoSerializer,
    CrearPedidoSerializer,
    DetallePedidoSerializer
)
from apps.productos.models import Producto
from apps.mesas.models import Mesa

# Avance permitido de un pedido: estado actual → (siguiente estado, roles que pueden hacerlo).
# No se puede saltar ni retroceder estados.
TRANSICIONES = {
    Pedido.Estado.PENDIENTE: (Pedido.Estado.EN_PREPARACION, ('Administrador', 'Garzon', 'Cocina')),
    Pedido.Estado.EN_PREPARACION: (Pedido.Estado.LISTO, ('Administrador', 'Cocina')),
    Pedido.Estado.LISTO: (Pedido.Estado.ENTREGADO, ('Administrador', 'Garzon')),
}


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
            'detalles__producto', 'historial__usuario'
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
        HistorialEstadoPedido.objects.create(
            pedido=pedido,
            estado=Pedido.Estado.PENDIENTE,
            usuario=usuario
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
                subtotal=subtotal,
                nota=item.get('nota', '').strip()
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
                'detalles__producto', 'historial__usuario'
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

        siguiente, roles = TRANSICIONES.get(pedido.estado, (None, ()))
        if nuevo_estado != siguiente:
            return Response(
                {'error': f'Un pedido en estado "{pedido.get_estado_display()}" '
                          f'no puede pasar a "{Pedido.Estado(nuevo_estado).label}"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user.rol.nombre not in roles:
            return Response(
                {'error': f'El rol {request.user.rol.nombre} no puede pasar un pedido '
                          f'a "{Pedido.Estado(nuevo_estado).label}"'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not pedido.registrar_estado(nuevo_estado, request.user):
            # Otro usuario avanzó el mismo pedido entre la lectura y la escritura
            return Response(
                {'error': f'El pedido ya cambió a "{pedido.get_estado_display()}". '
                          'Actualiza la lista de pedidos.'},
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            PedidoSerializer(pedido).data,
            status=status.HTTP_200_OK
        )