from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.pagos.models import Pago
from apps.pagos.serializers import PagoSerializer
from apps.pedidos.models import Pedido


class PagoListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        estado = request.query_params.get('estado')
        pagos = Pago.objects.select_related(
            'pedido__mesa',
            'pedido__usuario'
        ).prefetch_related(
            'pedido__detalles__producto'
        ).all().order_by('-fecha')

        if estado:
            pagos = pagos.filter(estado=estado)

        serializer = PagoSerializer(pagos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PagoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        pedido = Pedido.objects.get(
            pk=serializer.validated_data['pedido_id']
        )

        # Verificar que el monto coincide con el total del pedido
        if serializer.validated_data['monto'] != pedido.total:
            return Response(
                {
                    'error': f'El monto ingresado ({serializer.validated_data["monto"]}) '
                             f'no coincide con el total del pedido ({pedido.total})'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        pago = serializer.save(estado=Pago.Estado.COMPLETADO)

        # Marcar el pedido como entregado al completar el pago
        pedido.estado = Pedido.Estado.ENTREGADO
        pedido.save()

        return Response(
            PagoSerializer(pago).data,
            status=status.HTTP_201_CREATED
        )


class PagoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Pago.objects.select_related(
                'pedido__mesa',
                'pedido__usuario'
            ).prefetch_related(
                'pedido__detalles__producto'
            ).get(pk=pk)
        except Pago.DoesNotExist:
            return None

    def get(self, request, pk):
        pago = self.get_object(pk)
        if not pago:
            return Response(
                {'error': 'Pago no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = PagoSerializer(pago)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PagoAnularView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Pago.objects.select_related('pedido').get(pk=pk)
        except Pago.DoesNotExist:
            return None

    def patch(self, request, pk):
        pago = self.get_object(pk)
        if not pago:
            return Response(
                {'error': 'Pago no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        if pago.estado == Pago.Estado.ANULADO:
            return Response(
                {'error': 'Este pago ya fue anulado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pago.estado = Pago.Estado.ANULADO
        pago.save()

        return Response(
            PagoSerializer(pago).data,
            status=status.HTTP_200_OK
        )