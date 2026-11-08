import json

from django.urls import URLResolver, get_resolver, resolve
from rest_framework.test import APITestCase

from apps.mesas.models import Mesa, Solicitud
from apps.pagos.models import Pago
from apps.pedidos.models import Pedido
from apps.productos.models import Categoria, Producto
from apps.usuarios.models import Rol, Usuario

ADMIN, GARZON, COCINA, ANONIMO = 'Administrador', 'Garzon', 'Cocina', 'anónimo'
TODOS = {ADMIN, GARZON, COCINA, ANONIMO}
PERSONAL = {ADMIN, GARZON, COCINA}
SOLO_ADMIN = {ADMIN}
ADMIN_GARZON = {ADMIN, GARZON}
ADMIN_COCINA = {ADMIN, COCINA}

# Matriz de permisos esperada: quién puede usar cada ruta con cada método (RF07, RNF1).
# Las rutas usan los objetos creados en setUp.
MATRIZ = [
    # Autenticación y usuarios
    ('POST', '/api/auth/login/', TODOS),
    ('POST', '/api/auth/token/refresh/', TODOS),
    ('POST', '/api/auth/logout/', PERSONAL),
    ('GET', '/api/auth/perfil/', PERSONAL),
    ('GET', '/api/auth/usuarios/', SOLO_ADMIN),
    ('POST', '/api/auth/usuarios/', SOLO_ADMIN),
    ('PATCH', '/api/auth/usuarios/{usuario}/estado/', SOLO_ADMIN),
    ('PATCH', '/api/auth/usuarios/{usuario}/editar/', SOLO_ADMIN),
    ('GET', '/api/auth/roles/', SOLO_ADMIN),
    # Categorías y productos
    ('GET', '/api/categorias/', TODOS),
    ('POST', '/api/categorias/', SOLO_ADMIN),
    ('GET', '/api/categorias/{categoria}/', SOLO_ADMIN),
    ('PUT', '/api/categorias/{categoria}/', SOLO_ADMIN),
    ('DELETE', '/api/categorias/{categoria}/', SOLO_ADMIN),
    ('PATCH', '/api/categorias/{categoria}/estado/', SOLO_ADMIN),
    ('GET', '/api/productos/', TODOS),
    ('POST', '/api/productos/', SOLO_ADMIN),
    ('GET', '/api/productos/{producto}/', TODOS),
    ('PUT', '/api/productos/{producto}/', SOLO_ADMIN),
    ('DELETE', '/api/productos/{producto}/', SOLO_ADMIN),
    # Mesas y avisos de mesa
    ('GET', '/api/mesas/', TODOS),
    ('POST', '/api/mesas/', SOLO_ADMIN),
    ('GET', '/api/mesas/{mesa}/', TODOS),
    ('PUT', '/api/mesas/{mesa}/', SOLO_ADMIN),
    ('DELETE', '/api/mesas/{mesa}/', SOLO_ADMIN),
    ('PATCH', '/api/mesas/{mesa}/estado/', ADMIN_GARZON),
    ('POST', '/api/mesas/{mesa}/qr/', SOLO_ADMIN),
    ('POST', '/api/mesas/{mesa}/solicitudes/', TODOS),
    ('GET', '/api/solicitudes/', ADMIN_GARZON),
    ('PATCH', '/api/solicitudes/{solicitud}/atender/', ADMIN_GARZON),
    # Pedidos (el paso entre estados lo restringe además TRANSICIONES, según el rol)
    ('GET', '/api/pedidos/', PERSONAL),
    ('POST', '/api/pedidos/', TODOS),
    ('GET', '/api/pedidos/{pedido}/', ADMIN_COCINA),
    ('DELETE', '/api/pedidos/{pedido}/', SOLO_ADMIN),
    ('PATCH', '/api/pedidos/{pedido}/estado/', PERSONAL),
    # Pagos
    ('GET', '/api/pagos/', ADMIN_GARZON),
    ('POST', '/api/pagos/', ADMIN_GARZON),
    ('GET', '/api/pagos/{pago}/', PERSONAL),
    ('PATCH', '/api/pagos/{pago}/anular/', ADMIN_GARZON),
    ('DELETE', '/api/pagos/{pago}/eliminar/', SOLO_ADMIN),
]

METODOS = ('get', 'post', 'put', 'patch', 'delete')


def rutas_de_la_api(patrones=None, prefijo=''):
    """Recorre las URL del proyecto y entrega (ruta, vista) de las que cuelgan de api/."""
    for patron in get_resolver().url_patterns if patrones is None else patrones:
        ruta = prefijo + str(patron.pattern)
        if not ruta.startswith('api'):
            continue
        if isinstance(patron, URLResolver):
            yield from rutas_de_la_api(patron.url_patterns, ruta)
        elif hasattr(patron.callback, 'view_class'):
            yield ruta, patron.callback.view_class


def crear_usuario(rol):
    return Usuario.objects.create_user(
        f'{rol.lower()}@test.cl', rol, 'Prueba', 'clave-prueba',
        rol=Rol.objects.get_or_create(nombre=rol)[0]
    )


class MatrizDePermisosTests(APITestCase):
    """RF07 y RNF1: cada rol accede solo a lo que le corresponde, en todas las rutas de la API.

    Las peticiones van sin datos: así responden 400 o 404 si el rol pasa el control de
    permisos, y 401 (sin sesión) o 403 (rol no autorizado) si no lo pasa.
    """

    def setUp(self):
        self.usuarios = {rol: crear_usuario(rol) for rol in (ADMIN, GARZON, COCINA)}
        self.usuarios[ANONIMO] = None
        categoria = Categoria.objects.create(nombre='Pizzas')
        producto = Producto.objects.create(nombre='Margherita', precio=9990, categoria=categoria)
        mesa = Mesa.objects.create(numero=1, capacidad=4)
        pedido = Pedido.objects.create(mesa=mesa, total=9990)
        cobrado = Pedido.objects.create(mesa=mesa, total=9990, estado=Pedido.Estado.ENTREGADO)
        pago = Pago.objects.create(pedido=cobrado, metodo_pago='efectivo', monto=9990,
                                   estado=Pago.Estado.COMPLETADO)
        solicitud = Solicitud.objects.create(mesa=mesa, tipo=Solicitud.Tipo.CUENTA)
        self.ids = {
            'usuario': self.usuarios[GARZON].id,
            'categoria': categoria.id,
            'producto': producto.id,
            'mesa': mesa.id,
            'pedido': pedido.id,
            'pago': pago.id,
            'solicitud': solicitud.id,
        }

    def test_cada_rol_accede_solo_a_lo_que_le_corresponde(self):
        diferencias = []
        for perfil, usuario in self.usuarios.items():
            for metodo, ruta, permitidos in MATRIZ:
                url = ruta.format(**self.ids)
                self.client.force_authenticate(usuario)
                codigo = getattr(self.client, metodo.lower())(url, {}, format='json').status_code
                denegado = 401 if usuario is None else 403
                esperado = 'acceso' if perfil in permitidos else f'{denegado}'
                obtenido = f'{denegado}' if codigo in (401, 403) else 'acceso'
                if codigo >= 500:
                    diferencias.append(f'{perfil} · {metodo} {url}: error {codigo}')
                elif obtenido != esperado or (obtenido != 'acceso' and codigo != denegado):
                    diferencias.append(f'{perfil} · {metodo} {url}: esperado {esperado}, obtenido {codigo}')

        self.assertEqual(diferencias, [], '\n' + '\n'.join(diferencias))

    def test_la_matriz_cubre_todas_las_rutas_y_metodos_de_la_api(self):
        en_la_api = {
            (ruta, metodo.upper())
            for ruta, vista in rutas_de_la_api()
            for metodo in METODOS if hasattr(vista, metodo)
        }
        en_la_matriz = {(resolve(ruta.format(**self.ids)).route, metodo) for metodo, ruta, _ in MATRIZ}

        self.assertEqual(len(MATRIZ), 40)
        self.assertEqual(en_la_matriz, en_la_api)


class EntradasInvalidasTests(APITestCase):
    """Tabla 3.19: una entrada inválida responde 400, nunca 500.

    Estas entradas no se pueden enviar desde el panel ni desde la carta, pero sí
    llamando a la API directamente.
    """

    def setUp(self):
        self.admin = crear_usuario(ADMIN)
        self.client.force_authenticate(self.admin)
        self.categoria = Categoria.objects.create(nombre='Pizzas')
        self.producto = Producto.objects.create(nombre='Margherita', precio=9990, categoria=self.categoria)
        self.mesa = Mesa.objects.create(numero=1, capacidad=4)
        self.pedido = Pedido.objects.create(mesa=self.mesa, total=9990)
        self.url_estado_usuario = f'/api/auth/usuarios/{self.admin.id}/estado/'
        self.url_editar_usuario = f'/api/auth/usuarios/{self.admin.id}/editar/'
        self.url_estado_categoria = f'/api/categorias/{self.categoria.id}/estado/'

    def enviar(self, metodo, url, cuerpo):
        return getattr(self.client, metodo)(url, data=json.dumps(cuerpo), content_type='application/json')

    def test_un_cuerpo_json_que_no_es_objeto_responde_400(self):
        rutas = [
            ('post', '/api/auth/login/'),
            ('patch', self.url_estado_usuario),
            ('patch', self.url_editar_usuario),
            ('patch', self.url_estado_categoria),
            ('patch', f'/api/mesas/{self.mesa.id}/estado/'),
            ('post', f'/api/mesas/{self.mesa.id}/solicitudes/'),
            ('patch', f'/api/pedidos/{self.pedido.id}/estado/'),
        ]
        for metodo, url in rutas:
            for cuerpo in ([], [1, 2], 'texto', 123, None):
                with self.subTest(url=url, cuerpo=cuerpo):
                    self.assertEqual(self.enviar(metodo, url, cuerpo).status_code, 400)

    def test_un_filtro_que_no_es_un_id_valido_responde_400(self):
        for ruta in ('/api/productos/?categoria=', '/api/pedidos/?mesa='):
            for valor in ('abc', '1.5', '-1', str(10 ** 30), '9' * 5000):
                with self.subTest(ruta=ruta, valor=valor[:20]):
                    self.assertEqual(self.client.get(f'{ruta}{valor}').status_code, 400)

    def test_un_filtro_valido_sigue_filtrando(self):
        for url, encontrados in (
            (f'/api/productos/?categoria={self.categoria.id}', 1),
            ('/api/productos/?categoria=999', 0),
            (f'/api/pedidos/?mesa={self.mesa.id}', 1),
            ('/api/pedidos/?mesa=999', 0),
        ):
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(len(respuesta.data), encontrados)

    def test_credenciales_que_no_son_texto_responden_400(self):
        self.client.force_authenticate(None)
        for cuerpo in (
            {'email': 123, 'password': 456},
            {'email': ['a'], 'password': {'a': 1}},
            {'email': 'admin@test.cl', 'password': 123},
            {'email': 123, 'password': 'clave-prueba'},
        ):
            with self.subTest(cuerpo=cuerpo):
                self.assertEqual(self.enviar('post', '/api/auth/login/', cuerpo).status_code, 400)

    def test_activo_que_no_es_booleano_responde_400(self):
        for url in (self.url_estado_usuario, self.url_estado_categoria):
            for valor in ('abc', 'true', 1, 123, [], {}):
                with self.subTest(url=url, valor=valor):
                    self.assertEqual(self.enviar('patch', url, {'activo': valor}).status_code, 400)

        self.admin.refresh_from_db()
        self.categoria.refresh_from_db()
        self.assertTrue(self.admin.activo)
        self.assertTrue(self.categoria.activo)

    def test_editar_usuario_con_datos_que_no_son_texto_responde_400(self):
        for cuerpo in (
            {'password': 123},
            {'password': ['a']},
            {'nombre': 123},
            {'nombre': ['a']},
            {'apellido': {'a': 1}},
        ):
            with self.subTest(cuerpo=cuerpo):
                self.assertEqual(self.enviar('patch', self.url_editar_usuario, cuerpo).status_code, 400)

        self.admin.refresh_from_db()
        self.assertEqual(self.admin.nombre, ADMIN)
        self.assertTrue(self.admin.check_password('clave-prueba'))

    def test_editar_usuario_con_un_texto_mas_largo_que_su_columna_responde_400(self):
        for campo in ('nombre', 'apellido'):
            with self.subTest(campo=campo):
                respuesta = self.enviar('patch', self.url_editar_usuario, {campo: 'x' * 101})
                self.assertEqual(respuesta.status_code, 400)

        self.admin.refresh_from_db()
        self.assertEqual(self.admin.nombre, ADMIN)
