from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.mesas.models import Mesa
from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.productos.models import Categoria, Producto
from apps.usuarios.models import Rol, Usuario

AVANCE = ['en_preparacion', 'listo', 'entregado']
TOTAL = '19980.00'  # 2 × Margherita de $9.990


def crear_usuario(rol):
    return Usuario.objects.create_user(
        f'{rol.lower()}@test.cl', rol, 'Prueba', 'clave-prueba',
        rol=Rol.objects.get_or_create(nombre=rol)[0]
    )


class PagosTests(APITestCase):
    """RF25 a RF28 y RF39: registrar, consultar, anular y eliminar pagos.

    Vía API se puede cobrar un pedido que aún no se entrega (limitación L3): RF25 lo
    define como regla, «cobrar cierra el pedido», y así se prueba.
    """

    def setUp(self):
        self.admin = crear_usuario('Administrador')
        self.garzon = crear_usuario('Garzon')
        self.mesa = Mesa.objects.create(numero=1, capacidad=4)
        self.producto = Producto.objects.create(
            nombre='Margherita', precio=9990, categoria=Categoria.objects.create(nombre='Pizzas')
        )

    def nuevo_pedido(self, hasta=None):
        """Crea un pedido desde la carta y lo avanza hasta el estado indicado."""
        pedido_id = self.client.post(
            '/api/pedidos/',
            {'mesa_id': self.mesa.id, 'productos': [{'producto_id': self.producto.id, 'cantidad': 2}]},
            format='json'
        ).data['id']
        pedido = Pedido.objects.get(pk=pedido_id)
        for estado in AVANCE[:AVANCE.index(hasta) + 1] if hasta else []:
            pedido.registrar_estado(estado, self.garzon)
        return pedido

    def cobrar(self, pedido, monto=TOTAL, metodo='efectivo', usuario=None):
        self.client.force_authenticate(usuario or self.garzon)
        return self.client.post(
            '/api/pagos/',
            {'pedido_id': pedido.id, 'metodo_pago': metodo, 'monto': monto},
            format='json'
        )

    def anular(self, pago_id, usuario=None):
        self.client.force_authenticate(usuario or self.garzon)
        return self.client.patch(f'/api/pagos/{pago_id}/anular/')

    def test_el_garzon_registra_el_pago_de_un_pedido_entregado(self):
        pedido = self.nuevo_pedido(hasta='entregado')

        respuesta = self.cobrar(pedido)

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data['estado'], 'completado')
        self.assertEqual(respuesta.data['monto'], TOTAL)
        self.assertEqual(respuesta.data['pedido']['id'], pedido.id)
        self.assertEqual(respuesta.data['registrado_por']['email'], 'garzon@test.cl')
        self.assertIsNotNone(respuesta.data['fecha'])

    def test_acepta_efectivo_debito_credito_y_transferencia(self):
        for metodo in ('efectivo', 'debito', 'credito', 'transferencia'):
            with self.subTest(metodo=metodo):
                respuesta = self.cobrar(self.nuevo_pedido(hasta='entregado'), metodo=metodo)
                self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

    def test_un_metodo_de_pago_desconocido_se_rechaza(self):
        respuesta = self.cobrar(self.nuevo_pedido(hasta='entregado'), metodo='cheque')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('metodo_pago', respuesta.data)

    def test_un_monto_distinto_del_total_se_rechaza(self):
        respuesta = self.cobrar(self.nuevo_pedido(hasta='entregado'), monto='10000.00')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no coincide con el total', respuesta.data['error'])
        self.assertFalse(Pago.objects.exists())

    def test_un_monto_cero_o_negativo_se_rechaza(self):
        pedido = self.nuevo_pedido(hasta='entregado')

        for monto in ('0', '-19980'):
            with self.subTest(monto=monto):
                respuesta = self.cobrar(pedido, monto=monto)
                self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('monto', respuesta.data)

    def test_un_pedido_inexistente_se_rechaza(self):
        self.client.force_authenticate(self.garzon)

        respuesta = self.client.post(
            '/api/pagos/', {'pedido_id': 999, 'metodo_pago': 'efectivo', 'monto': TOTAL}, format='json'
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pedido_id', respuesta.data)

    def test_un_pedido_admite_un_solo_pago_vigente(self):
        pedido = self.nuevo_pedido(hasta='entregado')
        self.cobrar(pedido)

        segundo = self.cobrar(pedido, metodo='debito')

        self.assertEqual(segundo.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pedido_id', segundo.data)
        self.assertEqual(pedido.pagos.count(), 1)

    def test_anular_un_pago_permite_volver_a_cobrar_el_pedido(self):
        pedido = self.nuevo_pedido(hasta='entregado')
        pago_id = self.cobrar(pedido).data['id']

        anulado = self.anular(pago_id)
        nuevo = self.cobrar(pedido, metodo='credito')

        self.assertEqual(anulado.status_code, status.HTTP_200_OK)
        self.assertEqual(anulado.data['estado'], 'anulado')
        self.assertEqual(anulado.data['anulado_por']['email'], 'garzon@test.cl')
        self.assertEqual(nuevo.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            sorted(pedido.pagos.values_list('estado', flat=True)), ['anulado', 'completado']
        )

    def test_un_pago_no_se_anula_dos_veces(self):
        pago_id = self.cobrar(self.nuevo_pedido(hasta='entregado')).data['id']
        self.anular(pago_id)

        respuesta = self.anular(pago_id)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cobrar_un_pedido_listo_lo_entrega_y_libera_la_mesa(self):
        pedido = self.nuevo_pedido(hasta='listo')

        respuesta = self.cobrar(pedido)

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        pedido.refresh_from_db()
        self.mesa.refresh_from_db()
        self.assertEqual(pedido.estado, 'entregado')
        ultimo = pedido.historial.last()
        self.assertEqual((ultimo.estado, ultimo.usuario), ('entregado', self.garzon))
        self.assertEqual(self.mesa.estado, 'libre')

    def test_cobrar_no_libera_la_mesa_si_quedan_pedidos_activos(self):
        cobrado = self.nuevo_pedido(hasta='listo')
        self.nuevo_pedido()  # otro pedido de la misma mesa, todavía pendiente

        self.cobrar(cobrado)

        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.estado, 'ocupada')

    def test_el_historial_se_filtra_por_estado_y_sale_del_mas_reciente(self):
        antiguo = self.cobrar(self.nuevo_pedido(hasta='entregado')).data['id']
        reciente = self.cobrar(self.nuevo_pedido(hasta='entregado')).data['id']
        Pago.objects.filter(pk=antiguo).update(fecha=timezone.now() - timedelta(hours=1))
        self.anular(antiguo)

        todos = self.client.get('/api/pagos/')
        anulados = self.client.get('/api/pagos/?estado=anulado')
        completados = self.client.get('/api/pagos/?estado=completado')

        self.assertEqual([p['id'] for p in todos.data], [reciente, antiguo])
        self.assertEqual([p['id'] for p in anulados.data], [antiguo])
        self.assertEqual([p['id'] for p in completados.data], [reciente])

    def test_el_detalle_muestra_el_pedido_y_quien_lo_registro(self):
        pago_id = self.cobrar(self.nuevo_pedido(hasta='entregado')).data['id']
        self.client.force_authenticate(self.admin)

        respuesta = self.client.get(f'/api/pagos/{pago_id}/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['pedido']['detalles'][0]['cantidad'], 2)
        self.assertEqual(respuesta.data['registrado_por']['email'], 'garzon@test.cl')

    def test_solo_el_administrador_elimina_y_solo_pagos_anulados(self):
        completado = self.cobrar(self.nuevo_pedido(hasta='entregado')).data['id']
        anulado = self.cobrar(self.nuevo_pedido(hasta='entregado')).data['id']
        self.anular(anulado)

        garzon = self.client.delete(f'/api/pagos/{anulado}/eliminar/')
        self.client.force_authenticate(self.admin)
        no_anulado = self.client.delete(f'/api/pagos/{completado}/eliminar/')
        eliminado = self.client.delete(f'/api/pagos/{anulado}/eliminar/')

        self.assertEqual(garzon.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(no_anulado.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(eliminado.status_code, status.HTTP_200_OK)
        self.assertEqual(list(Pago.objects.values_list('id', flat=True)), [completado])

    def test_un_pago_inexistente_responde_404(self):
        self.client.force_authenticate(self.admin)

        for respuesta in (
            self.client.get('/api/pagos/999/'),
            self.client.patch('/api/pagos/999/anular/'),
            self.client.delete('/api/pagos/999/eliminar/'),
        ):
            self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_la_cocina_no_lista_registra_ni_anula_pagos(self):
        pedido = self.nuevo_pedido(hasta='entregado')
        pago_id = self.cobrar(pedido).data['id']
        cocina = crear_usuario('Cocina')

        self.client.force_authenticate(cocina)
        listar = self.client.get('/api/pagos/')
        registrar = self.cobrar(self.nuevo_pedido(hasta='entregado'), usuario=cocina)
        anular = self.anular(pago_id, usuario=cocina)

        self.assertEqual(listar.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(registrar.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(anular.status_code, status.HTTP_403_FORBIDDEN)

    def test_sin_sesion_no_se_accede_a_los_pagos(self):
        pedido = self.nuevo_pedido(hasta='entregado')

        listar = self.client.get('/api/pagos/')
        registrar = self.client.post(
            '/api/pagos/', {'pedido_id': pedido.id, 'metodo_pago': 'efectivo', 'monto': TOTAL}, format='json'
        )

        self.assertEqual(listar.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(registrar.status_code, status.HTTP_401_UNAUTHORIZED)
