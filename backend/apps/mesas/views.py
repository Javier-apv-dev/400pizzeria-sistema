from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings 
from config.permissions import EsAdministrador

from apps.mesas.models import Mesa
from apps.mesas.serializers import MesaSerializer
import qrcode
import base64
from io import BytesIO


def generar_qr(mesa_id):
    url = f'{settings.FRONTEND_URL}/carta?mesa={mesa_id}'

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{img_base64}'


class MesaListView(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [EsAdministrador()]

    def get(self, request):
        mesas = Mesa.objects.all().order_by('numero')
        serializer = MesaSerializer(mesas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MesaSerializer(data=request.data)
        if serializer.is_valid():
            mesa = serializer.save()
            mesa.qr_code = generar_qr(mesa.id)
            mesa.save()
            return Response(
                MesaSerializer(mesa).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MesaDetailView(APIView):

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [EsAdministrador()]

    def get_object(self, pk):
        try:
            return Mesa.objects.get(pk=pk)
        except Mesa.DoesNotExist:
            return None

    def get(self, request, pk):
        mesa = self.get_object(pk)
        if not mesa:
            return Response(
                {'error': 'Mesa no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = MesaSerializer(mesa)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        mesa = self.get_object(pk)
        if not mesa:
            return Response(
                {'error': 'Mesa no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = MesaSerializer(mesa, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        mesa = self.get_object(pk)
        if not mesa:
            return Response(
                {'error': 'Mesa no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        mesa.delete()
        return Response(
            {'mensaje': 'Mesa eliminada correctamente'},
            status=status.HTTP_200_OK
        )


class MesaEstadoView(APIView):
    permission_classes = [EsAdministrador]

    def get_object(self, pk):
        try:
            return Mesa.objects.get(pk=pk)
        except Mesa.DoesNotExist:
            return None

    def patch(self, request, pk):
        mesa = self.get_object(pk)
        if not mesa:
            return Response(
                {'error': 'Mesa no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

        nuevo_estado = request.data.get('estado')
        estados_validos = [e.value for e in Mesa.Estado]

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

        mesa.estado = nuevo_estado
        mesa.save()
        return Response(
            MesaSerializer(mesa).data,
            status=status.HTTP_200_OK
        )


class MesaQRView(APIView):
    permission_classes = [EsAdministrador]

    def get_object(self, pk):
        try:
            return Mesa.objects.get(pk=pk)
        except Mesa.DoesNotExist:
            return None

    def post(self, request, pk):
        mesa = self.get_object(pk)
        if not mesa:
            return Response(
                {'error': 'Mesa no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        mesa.qr_code = generar_qr(mesa.id)
        mesa.save()
        return Response(
            {'mensaje': 'QR regenerado correctamente', 'qr_code': mesa.qr_code},
            status=status.HTTP_200_OK
        )