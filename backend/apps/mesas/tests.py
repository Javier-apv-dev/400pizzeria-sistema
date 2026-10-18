import base64
from unittest import mock

import qrcode
from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.mesas.models import Mesa, Solicitud
from apps.productos.models import Categoria, Producto
from apps.usuarios.models import Rol, Usuario


def crear_usuario(rol):
    return Usuario.objects.create_user(
        f'{rol.lower()}@test.cl', rol, 'Prueba', 'clave-prueba',
        rol=Rol.objects.get_or_create(nombre=rol)[0]
    )


class MesasTests(APITestCase):
    """RF12 a RF15 y RF38: mesas, su código QR y su estado."""

    def setUp(self):
        self.admin = crear_usuario('Administrador')
        self.garzon = crear_usuario('Garzon')
        # Creadas en desorden para comprobar que la lista sale por número
        self.mesa2 = Mesa.objects.create(numero=2, capacidad=2)
        self.mesa1 = Mesa.objects.create(numero=1, capacidad=4)

    def crear_mesa(self, **datos):
        return self.client.post('/api/mesas/', {'numero': 7, 'capacidad': 4, **datos}, format='json')

    def test_cualquiera_ve_las_mesas_ordenadas_por_numero(self):
        respuesta = self.client.get('/api/mesas/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual([m['numero'] for m in respuesta.data], [1, 2])

    def test_la_carta_obtiene_el_numero_real_de_su_mesa(self):
        encontrada = self.client.get(f'/api/mesas/{self.mesa2.id}/')
        inexistente = self.client.get('/api/mesas/999/')

        self.assertEqual(encontrada.status_code, status.HTTP_200_OK)
        self.assertEqual(encontrada.data['numero'], 2)
        self.assertEqual(inexistente.status_code, status.HTTP_404_NOT_FOUND)

    def test_crear_una_mesa_genera_su_qr_con_la_url_de_la_carta(self):
        self.client.force_authenticate(self.admin)

        with mock.patch.object(qrcode.QRCode, 'add_data', autospec=True,
                               side_effect=qrcode.QRCode.add_data) as add_data:
            respuesta = self.crear_mesa()

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        prefijo = 'data:image/png;base64,'
        self.assertTrue(respuesta.data['qr_code'].startswith(prefijo))
        imagen = base64.b64decode(respuesta.data['qr_code'][len(prefijo):])
        self.assertTrue(imagen.startswith(b'\x89PNG'))
        url = add_data.call_args.args[1]
        self.assertEqual(url, f'{settings.FRONTEND_URL}/carta?mesa={respuesta.data["id"]}')

    def test_el_numero_de_mesa_no_se_repite(self):
        self.client.force_authenticate(self.admin)

        respuesta = self.crear_mesa(numero=1)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('numero', respuesta.data)

    def test_numero_y_capacidad_deben_ser_mayores_a_cero(self):
        self.client.force_authenticate(self.admin)

        sin_numero = self.crear_mesa(numero=0)
        sin_capacidad = self.crear_mesa(capacidad=0)

        self.assertIn('numero', sin_numero.data)
        self.assertIn('capacidad', sin_capacidad.data)
        self.assertEqual(sin_numero.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sin_capacidad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_editar_una_mesa_no_cambia_su_qr(self):
        self.mesa1.qr_code = 'data:image/png;base64,original'
        self.mesa1.save()
        self.client.force_authenticate(self.admin)

        respuesta = self.client.put(
            f'/api/mesas/{self.mesa1.id}/',
            {'numero': 10, 'capacidad': 6, 'qr_code': 'otro'},
            format='json'
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.mesa1.refresh_from_db()
        self.assertEqual((self.mesa1.numero, self.mesa1.capacidad), (10, 6))
        self.assertEqual(self.mesa1.qr_code, 'data:image/png;base64,original')

    def test_regenerar_el_qr_lo_reemplaza(self):
        self.mesa1.qr_code = 'viejo'
        self.mesa1.save()
        self.client.force_authenticate(self.admin)

        respuesta = self.client.post(f'/api/mesas/{self.mesa1.id}/qr/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertTrue(respuesta.data['qr_code'].startswith('data:image/png;base64,'))
        self.mesa1.refresh_from_db()
        self.assertEqual(self.mesa1.qr_code, respuesta.data['qr_code'])

    def test_el_garzon_cambia_el_estado_de_una_mesa(self):
        self.client.force_authenticate(self.garzon)

        respuesta = self.client.patch(f'/api/mesas/{self.mesa1.id}/estado/', {'estado': 'reservada'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.mesa1.refresh_from_db()
        self.assertEqual(self.mesa1.estado, 'reservada')

    def test_un_estado_invalido_o_vacio_responde_400(self):
        self.client.force_authenticate(self.garzon)
        url = f'/api/mesas/{self.mesa1.id}/estado/'

        invalido = self.client.patch(url, {'estado': 'sucia'}, format='json')
        vacio = self.client.patch(url, {}, format='json')

        self.assertEqual(invalido.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(vacio.status_code, status.HTTP_400_BAD_REQUEST)

    def test_la_cocina_y_los_visitantes_no_cambian_el_estado(self):
        url = f'/api/mesas/{self.mesa1.id}/estado/'

        sin_sesion = self.client.patch(url, {'estado': 'ocupada'}, format='json')
        self.client.force_authenticate(crear_usuario('Cocina'))
        cocina = self.client.patch(url, {'estado': 'ocupada'}, format='json')

        self.assertEqual(sin_sesion.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(cocina.status_code, status.HTTP_403_FORBIDDEN)

    def test_el_garzon_no_crea_edita_borra_ni_regenera_qr(self):
        self.client.force_authenticate(self.garzon)

        for respuesta in (
            self.crear_mesa(),
            self.client.put(f'/api/mesas/{self.mesa1.id}/', {'numero': 9, 'capacidad': 2}, format='json'),
            self.client.delete(f'/api/mesas/{self.mesa1.id}/'),
            self.client.post(f'/api/mesas/{self.mesa1.id}/qr/'),
        ):
            self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_borrar_una_mesa_sin_pedidos_la_elimina_junto_con_sus_avisos(self):
        Solicitud.objects.create(mesa=self.mesa2, tipo=Solicitud.Tipo.GARZON)
        self.client.force_authenticate(self.admin)

        respuesta = self.client.delete(f'/api/mesas/{self.mesa2.id}/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertFalse(Mesa.objects.filter(pk=self.mesa2.id).exists())
        self.assertFalse(Solicitud.objects.exists())

    def test_borrar_una_mesa_con_pedidos_responde_400_y_la_conserva(self):
        producto = Producto.objects.create(nombre='Margherita', precio=9990,
                                           categoria=Categoria.objects.create(nombre='Pizzas'))
        self.client.post(
            '/api/pedidos/',
            {'mesa_id': self.mesa1.id, 'productos': [{'producto_id': producto.id, 'cantidad': 1}]},
            format='json'
        )
        self.client.force_authenticate(self.admin)

        respuesta = self.client.delete(f'/api/mesas/{self.mesa1.id}/')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tiene pedidos registrados', respuesta.data['error'])
        self.assertTrue(Mesa.objects.filter(pk=self.mesa1.id).exists())

    def test_una_mesa_inexistente_responde_404(self):
        self.client.force_authenticate(self.admin)

        for respuesta in (
            self.client.put('/api/mesas/999/', {'numero': 9, 'capacidad': 2}, format='json'),
            self.client.delete('/api/mesas/999/'),
            self.client.patch('/api/mesas/999/estado/', {'estado': 'libre'}, format='json'),
            self.client.post('/api/mesas/999/qr/'),
        ):
            self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_sin_sesion_no_se_crean_mesas(self):
        respuesta = self.crear_mesa()

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)


class SolicitudesDeMesaTests(APITestCase):
    """El cliente llama al garzón o pide la cuenta desde la carta; el garzón lo atiende."""

    def setUp(self):
        self.mesa = Mesa.objects.create(numero=4, capacidad=4)
        self.garzon = crear_usuario('Garzon')

    def solicitar(self, tipo, mesa_id=None):
        return self.client.post(
            f'/api/mesas/{mesa_id or self.mesa.id}/solicitudes/',
            {'tipo': tipo},
            format='json'
        )

    def test_el_cliente_pide_la_cuenta_sin_iniciar_sesion(self):
        respuesta = self.solicitar('cuenta')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data['mesa_numero'], 4)
        self.assertEqual(respuesta.data['tipo_display'], 'Pedir la cuenta')
        self.assertEqual(respuesta.data['estado'], 'pendiente')

    def test_tocar_el_boton_varias_veces_no_duplica_el_aviso(self):
        primera = self.solicitar('garzon')
        segunda = self.solicitar('garzon')

        self.assertEqual(segunda.status_code, status.HTTP_200_OK)
        self.assertEqual(segunda.data['id'], primera.data['id'])
        self.assertEqual(Solicitud.objects.count(), 1)

    def test_llamar_al_garzon_y_pedir_la_cuenta_son_avisos_distintos(self):
        self.solicitar('garzon')
        self.solicitar('cuenta')

        self.assertEqual(Solicitud.objects.count(), 2)

    def test_rechaza_tipo_invalido(self):
        respuesta = self.solicitar('postre')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rechaza_mesa_inexistente(self):
        respuesta = self.solicitar('garzon', mesa_id=999)

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_el_garzon_ve_las_pendientes_y_las_atiende(self):
        solicitud_id = self.solicitar('cuenta').data['id']
        self.client.force_authenticate(self.garzon)

        pendientes = self.client.get('/api/solicitudes/?estado=pendiente')
        atendida = self.client.patch(f'/api/solicitudes/{solicitud_id}/atender/')

        self.assertEqual([s['id'] for s in pendientes.data], [solicitud_id])
        self.assertEqual(atendida.status_code, status.HTTP_200_OK)
        self.assertEqual(atendida.data['estado'], 'atendida')
        self.assertEqual(atendida.data['atendida_por'], 'Garzon Prueba')
        self.assertIsNotNone(atendida.data['atendida_en'])

    def test_despues_de_atendida_la_mesa_puede_volver_a_llamar(self):
        primera_id = self.solicitar('garzon').data['id']
        self.client.force_authenticate(self.garzon)
        self.client.patch(f'/api/solicitudes/{primera_id}/atender/')
        self.client.force_authenticate(None)

        respuesta = self.solicitar('garzon')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(respuesta.data['id'], primera_id)

    def test_no_se_atiende_dos_veces(self):
        solicitud_id = self.solicitar('garzon').data['id']
        self.client.force_authenticate(self.garzon)
        self.client.patch(f'/api/solicitudes/{solicitud_id}/atender/')

        respuesta = self.client.patch(f'/api/solicitudes/{solicitud_id}/atender/')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_la_cocina_no_ve_ni_atiende_solicitudes(self):
        solicitud_id = self.solicitar('garzon').data['id']
        self.client.force_authenticate(crear_usuario('Cocina'))

        self.assertEqual(self.client.get('/api/solicitudes/').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.patch(f'/api/solicitudes/{solicitud_id}/atender/').status_code,
            status.HTTP_403_FORBIDDEN
        )

    def test_sin_sesion_no_se_pueden_listar(self):
        self.solicitar('garzon')

        respuesta = self.client.get('/api/solicitudes/')

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)
