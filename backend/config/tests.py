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
