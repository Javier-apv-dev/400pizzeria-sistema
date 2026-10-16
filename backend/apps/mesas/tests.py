from rest_framework import status
from rest_framework.test import APITestCase

from apps.mesas.models import Mesa, Solicitud
from apps.usuarios.models import Rol, Usuario


def crear_usuario(rol):
    return Usuario.objects.create_user(
        f'{rol.lower()}@test.cl', rol, 'Prueba', 'clave-prueba',
        rol=Rol.objects.get_or_create(nombre=rol)[0]
    )


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
