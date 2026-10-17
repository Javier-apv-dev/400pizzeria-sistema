from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.usuarios.models import Rol, Usuario

CLAVE = 'clave-prueba'


def crear_usuario(rol, email=None):
    return Usuario.objects.create_user(
        email or f'{rol.lower()}@test.cl', rol, 'Prueba', CLAVE,
        rol=Rol.objects.get_or_create(nombre=rol)[0]
    )


class AutenticacionTestBase(APITestCase):

    def login(self, email, password=CLAVE):
        return self.client.post(
            '/api/auth/login/',
            {'email': email, 'password': password},
            format='json'
        )


class LoginTests(AutenticacionTestBase):
    """RF01 y RF02: inicio de sesión con correo y contraseña, y vigencia de los tokens."""

    def setUp(self):
        self.garzon = crear_usuario('Garzon')

    def test_credenciales_validas_entregan_los_tokens_y_el_usuario_con_su_rol(self):
        respuesta = self.login('garzon@test.cl')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIn('access', respuesta.data)
        self.assertIn('refresh', respuesta.data)
        self.assertEqual(respuesta.data['usuario']['rol']['nombre'], 'Garzon')

    def test_clave_incorrecta_responde_401_sin_tokens(self):
        respuesta = self.login('garzon@test.cl', 'otra-clave')

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', respuesta.data)

    def test_correo_no_registrado_responde_401(self):
        respuesta = self.login('nadie@test.cl')

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_sin_correo_o_sin_clave_responde_400(self):
        sin_clave = self.client.post('/api/auth/login/', {'email': 'garzon@test.cl'}, format='json')
        sin_correo = self.client.post('/api/auth/login/', {'password': CLAVE}, format='json')

        self.assertEqual(sin_clave.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sin_correo.status_code, status.HTTP_400_BAD_REQUEST)

    def test_un_usuario_desactivado_no_puede_entrar(self):
        self.garzon.activo = False
        self.garzon.is_active = False
        self.garzon.save()

        respuesta = self.login('garzon@test.cl')

        # Responde 401 con «Credenciales incorrectas»: el mensaje «Usuario inactivo»
        # nunca se alcanza (issue #14), pero el usuario no recibe tokens
        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', respuesta.data)

    def test_el_token_de_acceso_dura_8_horas_y_el_de_refresco_24(self):
        respuesta = self.login('garzon@test.cl')
        acceso = AccessToken(respuesta.data['access'])
        refresco = RefreshToken(respuesta.data['refresh'])

        self.assertEqual(acceso['exp'] - acceso['iat'], 8 * 3600)
        self.assertEqual(refresco['exp'] - refresco['iat'], 24 * 3600)
        self.assertEqual(str(acceso['user_id']), str(self.garzon.id))


class SesionTests(AutenticacionTestBase):
    """RF03 y RF04: perfil, renovación con rotación del refresco y cierre de sesión."""

    def setUp(self):
        self.cocina = crear_usuario('Cocina')
        tokens = self.login('cocina@test.cl').data
        self.acceso, self.refresco = tokens['access'], tokens['refresh']

    def renovar(self, refresco):
        return self.client.post('/api/auth/token/refresh/', {'refresh': refresco}, format='json')

    def test_el_perfil_devuelve_al_usuario_del_token_con_su_rol(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.acceso}')

        respuesta = self.client.get('/api/auth/perfil/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data['email'], 'cocina@test.cl')
        self.assertEqual(respuesta.data['rol']['nombre'], 'Cocina')

    def test_el_perfil_sin_token_responde_401(self):
        respuesta = self.client.get('/api/auth/perfil/')

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_renovar_entrega_un_acceso_y_un_refresco_nuevos(self):
        respuesta = self.renovar(self.refresco)

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIn('access', respuesta.data)
        self.assertNotEqual(respuesta.data['refresh'], self.refresco)

    def test_un_refresco_ya_usado_no_sirve_otra_vez(self):
        self.renovar(self.refresco)

        respuesta = self.renovar(self.refresco)

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cerrar_sesion_invalida_el_refresco(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.acceso}')

        cierre = self.client.post('/api/auth/logout/', {'refresh': self.refresco}, format='json')
        renovacion = self.renovar(self.refresco)

        self.assertEqual(cierre.status_code, status.HTTP_200_OK)
        self.assertEqual(renovacion.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cerrar_sesion_con_un_refresco_invalido_responde_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.acceso}')

        respuesta = self.client.post('/api/auth/logout/', {'refresh': 'no-es-un-token'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cerrar_sesion_exige_estar_autenticado(self):
        respuesta = self.client.post('/api/auth/logout/', {'refresh': self.refresco}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)


class GestionDeUsuariosTests(AutenticacionTestBase):
    """RF05 a RF07: el Administrador gestiona las cuentas del personal y los demás roles no.

    Un rol inexistente enviado directo a la API responde 500 (limitación L1, issue #12);
    el panel solo ofrece roles existentes, que es lo que exige RF06.
    """

    def setUp(self):
        self.admin = crear_usuario('Administrador')
        self.garzon = crear_usuario('Garzon')
        self.rol_cocina = Rol.objects.create(nombre='Cocina')
        self.client.force_authenticate(self.admin)

    def nuevo_usuario(self, **cambios):
        datos = {
            'nombre': 'Ana',
            'apellido': 'Rojas',
            'email': 'ana@test.cl',
            'password': 'secreta1',
            'rol_id': self.rol_cocina.id,
            **cambios
        }
        return self.client.post('/api/auth/usuarios/', datos, format='json')

    def test_el_administrador_lista_los_usuarios_con_su_rol(self):
        respuesta = self.client.get('/api/auth/usuarios/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        roles = {u['email']: u['rol']['nombre'] for u in respuesta.data}
        self.assertEqual(roles, {'administrador@test.cl': 'Administrador', 'garzon@test.cl': 'Garzon'})

    def test_el_administrador_crea_un_usuario_con_un_rol_existente(self):
        respuesta = self.nuevo_usuario()

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        ana = Usuario.objects.get(email='ana@test.cl')
        self.assertEqual(ana.rol.nombre, 'Cocina')
        self.assertTrue(ana.check_password('secreta1'))
        self.assertNotEqual(ana.password, 'secreta1')

    def test_la_respuesta_nunca_incluye_la_clave(self):
        self.nuevo_usuario()

        respuesta = self.client.get('/api/auth/usuarios/')

        self.assertTrue(all('password' not in u for u in respuesta.data))

    def test_una_clave_de_menos_de_6_caracteres_se_rechaza(self):
        respuesta = self.nuevo_usuario(password='corta')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', respuesta.data)

    def test_un_correo_repetido_se_rechaza(self):
        respuesta = self.nuevo_usuario(email='garzon@test.cl')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', respuesta.data)

    def test_editar_cambia_nombre_y_clave_pero_no_el_correo_ni_el_rol(self):
        respuesta = self.client.patch(
            f'/api/auth/usuarios/{self.garzon.id}/editar/',
            {'nombre': 'Pedro', 'password': 'nueva-clave', 'email': 'otro@test.cl',
             'rol_id': self.rol_cocina.id},
            format='json'
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.garzon.refresh_from_db()
        self.assertEqual(self.garzon.nombre, 'Pedro')
        self.assertEqual(self.garzon.email, 'garzon@test.cl')
        self.assertEqual(self.garzon.rol.nombre, 'Garzon')
        self.assertEqual(self.login('garzon@test.cl', 'nueva-clave').status_code, status.HTTP_200_OK)
        self.assertEqual(self.login('garzon@test.cl').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_desactivar_impide_entrar_y_reactivar_lo_permite(self):
        url = f'/api/auth/usuarios/{self.garzon.id}/estado/'

        desactivado = self.client.patch(url, {'activo': False}, format='json')
        login_desactivado = self.login('garzon@test.cl')
        self.client.patch(url, {'activo': True}, format='json')
        login_reactivado = self.login('garzon@test.cl')

        self.assertEqual(desactivado.status_code, status.HTTP_200_OK)
        self.assertEqual(login_desactivado.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(login_reactivado.status_code, status.HTTP_200_OK)

    def test_cambiar_estado_sin_el_campo_activo_responde_400(self):
        respuesta = self.client.patch(f'/api/auth/usuarios/{self.garzon.id}/estado/', {}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_un_usuario_inexistente_responde_404(self):
        editar = self.client.patch('/api/auth/usuarios/999/editar/', {'nombre': 'X'}, format='json')
        estado = self.client.patch('/api/auth/usuarios/999/estado/', {'activo': False}, format='json')

        self.assertEqual(editar.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(estado.status_code, status.HTTP_404_NOT_FOUND)

    def test_el_administrador_ve_los_roles(self):
        respuesta = self.client.get('/api/auth/roles/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual({r['nombre'] for r in respuesta.data}, {'Administrador', 'Garzon', 'Cocina'})

    def test_garzon_y_cocina_no_gestionan_usuarios_ni_ven_roles(self):
        cocina = crear_usuario('Cocina')
        for usuario in (self.garzon, cocina):
            self.client.force_authenticate(usuario)
            with self.subTest(rol=usuario.rol.nombre):
                self.assertEqual(self.client.get('/api/auth/usuarios/').status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(self.nuevo_usuario().status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(self.client.get('/api/auth/roles/').status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(
                    self.client.patch(f'/api/auth/usuarios/{self.admin.id}/estado/',
                                      {'activo': False}, format='json').status_code,
                    status.HTTP_403_FORBIDDEN
                )

    def test_sin_sesion_no_se_accede_a_la_gestion_de_usuarios(self):
        self.client.force_authenticate(None)

        self.assertEqual(self.client.get('/api/auth/usuarios/').status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.nuevo_usuario().status_code, status.HTTP_401_UNAUTHORIZED)
