# Create your views here.
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from config.permissions import EsAdministrador

from apps.productos.models import Categoria, Producto
from apps.productos.serializers import CategoriaSerializer, ProductoSerializer


# ─────────────────────────────────────────────
# Vistas de Categorías
# ─────────────────────────────────────────────

class CategoriaListView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [EsAdministrador()]

    def get(self, request):
    # Admin ve todas, cliente solo las activas
        if request.user.is_authenticated:
            categorias = Categoria.objects.all()
        else:
            categorias = Categoria.objects.filter(activo=True)
        
        serializer = CategoriaSerializer(categorias, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CategoriaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoriaDetailView(APIView):
    permission_classes = [EsAdministrador]

    def get_object(self, pk):
        try:
            return Categoria.objects.get(pk=pk)
        except Categoria.DoesNotExist:
            return None

    def get(self, request, pk):
        categoria = self.get_object(pk)
        if not categoria:
            return Response(
                {'error': 'Categoría no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = CategoriaSerializer(categoria)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        categoria = self.get_object(pk)
        if not categoria:
            return Response(
                {'error': 'Categoría no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = CategoriaSerializer(categoria, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        categoria = self.get_object(pk)
        if not categoria:
            return Response(
                {'error': 'Categoría no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        categoria.activo = False
        categoria.save()
        return Response(
            {'mensaje': 'Categoría desactivada correctamente'},
            status=status.HTTP_200_OK
        )


# ─────────────────────────────────────────────
# Vistas de Productos
# ─────────────────────────────────────────────

class ProductoListView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [EsAdministrador()]

    def get(self, request):
        categoria_id = request.query_params.get('categoria')

        if request.user.is_authenticated:
            productos = Producto.objects.select_related('categoria').filter(
                categoria__activo=True
            )
        else:
            productos = Producto.objects.select_related('categoria').filter(
                disponible=True,
                categoria__activo=True
            )

        if categoria_id:
            productos = productos.filter(categoria_id=categoria_id)
        serializer = ProductoSerializer(
            productos,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ProductoSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductoDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [EsAdministrador()]

    def get_object(self, pk):
        try:
            return Producto.objects.select_related('categoria').get(pk=pk)
        except Producto.DoesNotExist:
            return None

    def get(self, request, pk):
        producto = self.get_object(pk)
        if not producto:
            return Response(
                {'error': 'Producto no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProductoSerializer(
            producto,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        producto = self.get_object(pk)
        if not producto:
            return Response(
                {'error': 'Producto no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProductoSerializer(
            producto,
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        producto = self.get_object(pk)
        if not producto:
            return Response(
                {'error': 'Producto no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        producto.disponible = False
        producto.save()
        return Response(
            {'mensaje': 'Producto desactivado correctamente'},
            status=status.HTTP_200_OK
        )