from rest_framework import status
from rest_framework.test import APITestCase

from apps.mesas.models import Mesa
from apps.pedidos.models import DetallePedido
from apps.productos.models import Categoria, Producto
from apps.usuarios.models import Rol, Usuario


class PedidoTestBase(APITestCase):
    """Datos mínimos para crear pedidos desde la carta (sin autenticación)."""

    def setUp(self):
        self.mesa = Mesa.objects.create(numero=1, capacidad=4)
        categoria = Categoria.objects.create(nombre='Pizzas')
        self.margherita = Producto.objects.create(
            nombre='Margherita', precio=9990, categoria=categoria
        )

    def crear_pedido(self, **item_extra):
        item = {'producto_id': self.margherita.id, 'cantidad': 2, **item_extra}
        return self.client.post(
            '/api/pedidos/',
            {'mesa_id': self.mesa.id, 'productos': [item]},
            format='json'
        )


class NotaDetallePedidoTests(PedidoTestBase):
    """Indicaciones del cliente por línea de pedido ("sin cebolla")."""

    def test_guarda_la_nota_sin_espacios_sobrantes(self):
        respuesta = self.crear_pedido(nota='  sin albahaca  ')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data['detalles'][0]['nota'], 'sin albahaca')
        self.assertEqual(DetallePedido.objects.get().nota, 'sin albahaca')

    def test_la_nota_es_opcional(self):
        respuesta = self.crear_pedido()

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DetallePedido.objects.get().nota, '')

    def test_rechaza_nota_de_mas_de_140_caracteres(self):
        respuesta = self.crear_pedido(nota='x' * 141)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('140', str(respuesta.data['productos']))
        self.assertFalse(DetallePedido.objects.exists())

    def test_rechaza_nota_que_no_es_texto(self):
        respuesta = self.crear_pedido(nota=123)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_mismo_producto_con_distinta_nota_queda_en_lineas_separadas(self):
        respuesta = self.client.post('/api/pedidos/', {
            'mesa_id': self.mesa.id,
            'productos': [
                {'producto_id': self.margherita.id, 'cantidad': 1},
                {'producto_id': self.margherita.id, 'cantidad': 1, 'nota': 'sin albahaca'},
            ]
        }, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            sorted(d['nota'] for d in respuesta.data['detalles']),
            ['', 'sin albahaca']
        )
        self.assertEqual(respuesta.data['total'], '19980.00')

    def test_la_cocina_ve_la_nota_en_la_lista_de_pedidos(self):
        self.crear_pedido(nota='bien cocida')
        cocina = Usuario.objects.create_user(
            'cocina@test.cl', 'Carla', 'Cocina', 'clave-prueba',
            rol=Rol.objects.create(nombre='Cocina')
        )
        self.client.force_authenticate(cocina)

        respuesta = self.client.get('/api/pedidos/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data[0]['detalles'][0]['nota'], 'bien cocida')
