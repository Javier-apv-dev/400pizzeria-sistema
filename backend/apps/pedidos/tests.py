from rest_framework import status
from rest_framework.test import APITestCase

from apps.mesas.models import Mesa
from apps.pedidos.models import DetallePedido, Pedido
from apps.productos.models import Categoria, Producto
from apps.usuarios.models import Rol, Usuario


def crear_usuario(rol):
    return Usuario.objects.create_user(
        f'{rol.lower()}@test.cl', rol, 'Prueba', 'clave-prueba',
        rol=Rol.objects.get_or_create(nombre=rol)[0]
    )


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


class HistorialYTransicionesTests(PedidoTestBase):
    """Cada cambio de estado queda registrado y solo avanza en orden, según el rol."""

    def setUp(self):
        super().setUp()
        self.garzon = crear_usuario('Garzon')
        self.cocina = crear_usuario('Cocina')
        self.pedido_id = self.crear_pedido().data['id']

    def avanzar(self, usuario, estado, pedido_id=None):
        self.client.force_authenticate(usuario)
        return self.client.patch(
            f'/api/pedidos/{pedido_id or self.pedido_id}/estado/',
            {'estado': estado},
            format='json'
        )

    def historial(self, pedido_id=None):
        return list(Pedido.objects.get(pk=pedido_id or self.pedido_id)
                    .historial.values_list('estado', 'usuario__nombre'))

    def test_crear_pedido_desde_la_carta_registra_pendiente_sin_usuario(self):
        self.assertEqual(self.historial(), [('pendiente', None)])

    def test_la_cocina_puede_empezar_un_pedido_pendiente(self):
        respuesta = self.avanzar(self.cocina, 'en_preparacion')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(self.historial()[-1], ('en_preparacion', 'Cocina'))

    def test_el_garzon_tambien_puede_empezar_un_pedido_pendiente(self):
        respuesta = self.avanzar(self.garzon, 'en_preparacion')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_ciclo_completo_queda_en_el_historial_con_quien_lo_hizo(self):
        self.avanzar(self.cocina, 'en_preparacion')
        self.avanzar(self.cocina, 'listo')
        respuesta = self.avanzar(self.garzon, 'entregado')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(self.historial(), [
            ('pendiente', None),
            ('en_preparacion', 'Cocina'),
            ('listo', 'Cocina'),
            ('entregado', 'Garzon'),
        ])
        self.assertEqual(
            [h['estado'] for h in respuesta.data['historial']],
            ['pendiente', 'en_preparacion', 'listo', 'entregado']
        )

    def test_no_se_puede_saltar_un_estado(self):
        respuesta = self.avanzar(self.cocina, 'listo')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Pedido.objects.get(pk=self.pedido_id).estado, 'pendiente')

    def test_no_se_puede_retroceder_un_pedido_entregado(self):
        self.avanzar(self.cocina, 'en_preparacion')
        self.avanzar(self.cocina, 'listo')
        self.avanzar(self.garzon, 'entregado')

        respuesta = self.avanzar(self.garzon, 'pendiente')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_garzon_no_puede_marcar_listo(self):
        self.avanzar(self.cocina, 'en_preparacion')

        respuesta = self.avanzar(self.garzon, 'listo')

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_la_cocina_no_puede_entregar(self):
        self.avanzar(self.cocina, 'en_preparacion')
        self.avanzar(self.cocina, 'listo')

        respuesta = self.avanzar(self.cocina, 'entregado')

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_entregar_libera_la_mesa_solo_si_no_quedan_pedidos_activos(self):
        otro_id = self.crear_pedido().data['id']
        for pedido_id in (self.pedido_id, otro_id):
            self.avanzar(self.cocina, 'en_preparacion', pedido_id)
            self.avanzar(self.cocina, 'listo', pedido_id)

        self.avanzar(self.garzon, 'entregado', self.pedido_id)
        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.estado, 'ocupada')

        self.avanzar(self.garzon, 'entregado', otro_id)
        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.estado, 'libre')

    def test_cobrar_un_pedido_listo_lo_entrega_y_lo_registra(self):
        self.avanzar(self.cocina, 'en_preparacion')
        self.avanzar(self.cocina, 'listo')
        self.client.force_authenticate(self.garzon)

        respuesta = self.client.post('/api/pagos/', {
            'pedido_id': self.pedido_id, 'metodo_pago': 'efectivo', 'monto': '19980.00'
        }, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.historial()[-1], ('entregado', 'Garzon'))
        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.estado, 'libre')
