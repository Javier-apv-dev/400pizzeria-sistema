import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.mesas.models import Mesa
from apps.pedidos.models import DetallePedido
from apps.productos.models import Categoria, Producto
from apps.usuarios.models import Rol, Usuario


def crear_usuario(rol):
    return Usuario.objects.create_user(
        f'{rol.lower()}@test.cl', rol, 'Prueba', 'clave-prueba',
        rol=Rol.objects.get_or_create(nombre=rol)[0]
    )


def imagen_png(nombre='margherita.png'):
    contenido = BytesIO()
    Image.new('RGB', (8, 8), 'orange').save(contenido, format='PNG')
    return SimpleUploadedFile(nombre, contenido.getvalue(), content_type='image/png')


class CategoriasTests(APITestCase):
    """RF08: el Administrador crea, edita y desactiva categorías; la carta solo muestra las activas."""

    def setUp(self):
        self.admin = crear_usuario('Administrador')
        self.garzon = crear_usuario('Garzon')
        self.pizzas = Categoria.objects.create(nombre='Pizzas')
        self.postres = Categoria.objects.create(nombre='Postres', activo=False)

    def nombres(self, respuesta):
        return {c['nombre'] for c in respuesta.data}

    def test_un_visitante_ve_solo_las_categorias_activas(self):
        respuesta = self.client.get('/api/categorias/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(self.nombres(respuesta), {'Pizzas'})

    def test_el_personal_ve_tambien_las_categorias_inactivas(self):
        self.client.force_authenticate(self.garzon)

        respuesta = self.client.get('/api/categorias/')

        self.assertEqual(self.nombres(respuesta), {'Pizzas', 'Postres'})

    def test_el_administrador_crea_una_categoria(self):
        self.client.force_authenticate(self.admin)

        respuesta = self.client.post('/api/categorias/', {'nombre': 'Bebidas'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Categoria.objects.get(nombre='Bebidas').activo)

    def test_el_administrador_edita_una_categoria(self):
        self.client.force_authenticate(self.admin)

        respuesta = self.client.put(
            f'/api/categorias/{self.pizzas.id}/',
            {'nombre': 'Pizzas napolitanas', 'descripcion': 'Masa madre', 'activo': True},
            format='json'
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.pizzas.refresh_from_db()
        self.assertEqual(self.pizzas.nombre, 'Pizzas napolitanas')

    def test_eliminar_una_categoria_la_desactiva_sin_borrarla(self):
        self.client.force_authenticate(self.admin)

        respuesta = self.client.delete(f'/api/categorias/{self.pizzas.id}/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.pizzas.refresh_from_db()
        self.assertFalse(self.pizzas.activo)

    def test_el_endpoint_de_estado_activa_y_desactiva(self):
        self.client.force_authenticate(self.admin)
        url = f'/api/categorias/{self.postres.id}/estado/'

        activada = self.client.patch(url, {'activo': True}, format='json')
        sin_campo = self.client.patch(url, {}, format='json')

        self.assertEqual(activada.status_code, status.HTTP_200_OK)
        self.assertTrue(activada.data['activo'])
        self.assertEqual(sin_campo.status_code, status.HTTP_400_BAD_REQUEST)

    def test_una_categoria_inexistente_responde_404(self):
        self.client.force_authenticate(self.admin)

        for respuesta in (
            self.client.get('/api/categorias/999/'),
            self.client.put('/api/categorias/999/', {'nombre': 'X'}, format='json'),
            self.client.delete('/api/categorias/999/'),
            self.client.patch('/api/categorias/999/estado/', {'activo': True}, format='json'),
        ):
            self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_garzon_y_cocina_no_crean_editan_ni_desactivan_categorias(self):
        cocina = crear_usuario('Cocina')
        for usuario in (self.garzon, cocina):
            self.client.force_authenticate(usuario)
            with self.subTest(rol=usuario.rol.nombre):
                for respuesta in (
                    self.client.post('/api/categorias/', {'nombre': 'X'}, format='json'),
                    self.client.put(f'/api/categorias/{self.pizzas.id}/', {'nombre': 'X'}, format='json'),
                    self.client.delete(f'/api/categorias/{self.pizzas.id}/'),
                    self.client.patch(f'/api/categorias/{self.pizzas.id}/estado/', {'activo': False}, format='json'),
                ):
                    self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_sin_sesion_no_se_crean_categorias(self):
        respuesta = self.client.post('/api/categorias/', {'nombre': 'X'}, format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)


class ProductosTests(APITestCase):
    """RF09 a RF11 y RF16: productos de la carta, su categoría y su disponibilidad.

    Una categoría inexistente enviada directo a la API responde 500 (limitación L2);
    el panel solo ofrece categorías registradas, que es lo que exige RF10.
    """

    def setUp(self):
        self.admin = crear_usuario('Administrador')
        self.garzon = crear_usuario('Garzon')
        self.pizzas = Categoria.objects.create(nombre='Pizzas')
        self.postres = Categoria.objects.create(nombre='Postres', activo=False)
        self.margherita = Producto.objects.create(
            nombre='Margherita', descripcion='Tomate, mozzarella y albahaca',
            precio=9990, categoria=self.pizzas
        )
        self.diavola = Producto.objects.create(
            nombre='Diavola', precio=11990, categoria=self.pizzas, disponible=False
        )
        self.tiramisu = Producto.objects.create(nombre='Tiramisú', precio=4990, categoria=self.postres)

    def nombres(self, respuesta):
        return {p['nombre'] for p in respuesta.data}

    def datos_producto(self, **cambios):
        return {
            'nombre': 'Capricciosa',
            'descripcion': 'Jamón, champiñones y alcachofas',
            'precio': '10990',
            'categoria_id': self.pizzas.id,
            'disponible': True,
            **cambios
        }

    def test_la_carta_publica_muestra_solo_disponibles_de_categorias_activas(self):
        respuesta = self.client.get('/api/productos/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(self.nombres(respuesta), {'Margherita'})

    def test_un_visitante_no_ve_los_no_disponibles_aunque_use_el_filtro(self):
        respuesta = self.client.get('/api/productos/?disponible=false')

        self.assertEqual(self.nombres(respuesta), {'Margherita'})

    def test_la_carta_filtra_los_productos_por_categoria(self):
        Producto.objects.create(nombre='Bebida', precio=1990, categoria=Categoria.objects.create(nombre='Bebidas'))

        respuesta = self.client.get(f'/api/productos/?categoria={self.pizzas.id}')

        self.assertEqual(self.nombres(respuesta), {'Margherita'})

    def test_cada_producto_trae_descripcion_precio_y_categoria(self):
        respuesta = self.client.get('/api/productos/')
        producto = respuesta.data[0]

        self.assertEqual(producto['descripcion'], 'Tomate, mozzarella y albahaca')
        self.assertEqual(producto['precio'], '9990.00')
        self.assertEqual(producto['categoria']['nombre'], 'Pizzas')

    def test_el_personal_ve_todos_los_productos_incluso_de_categorias_inactivas(self):
        self.client.force_authenticate(self.garzon)

        respuesta = self.client.get('/api/productos/')

        self.assertEqual(self.nombres(respuesta), {'Margherita', 'Diavola', 'Tiramisú'})

    def test_el_personal_filtra_por_disponibilidad(self):
        self.client.force_authenticate(self.garzon)

        no_disponibles = self.client.get('/api/productos/?disponible=false')
        disponibles = self.client.get('/api/productos/?disponible=true')

        self.assertEqual(self.nombres(no_disponibles), {'Diavola'})
        self.assertEqual(self.nombres(disponibles), {'Margherita', 'Tiramisú'})

    def test_el_administrador_crea_un_producto_con_imagen_que_aparece_en_la_carta(self):
        carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, carpeta)
        self.client.force_authenticate(self.admin)

        with self.settings(MEDIA_ROOT=carpeta):
            respuesta = self.client.post(
                '/api/productos/', self.datos_producto(imagen=imagen_png()), format='multipart'
            )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertTrue(respuesta.data['imagen'].startswith('http://testserver/media/productos/'))
        self.assertEqual(Producto.objects.get(nombre='Capricciosa').categoria, self.pizzas)
        self.client.force_authenticate(None)
        self.assertIn('Capricciosa', self.nombres(self.client.get('/api/productos/')))

    def test_un_archivo_que_no_es_imagen_se_rechaza(self):
        self.client.force_authenticate(self.admin)
        archivo = SimpleUploadedFile('menu.txt', b'no es una imagen', content_type='text/plain')

        respuesta = self.client.post('/api/productos/', self.datos_producto(imagen=archivo), format='multipart')

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('imagen', respuesta.data)

    def test_un_precio_cero_o_negativo_se_rechaza(self):
        self.client.force_authenticate(self.admin)

        for precio in ('0', '-100'):
            with self.subTest(precio=precio):
                respuesta = self.client.post('/api/productos/', self.datos_producto(precio=precio), format='json')
                self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('precio', respuesta.data)

    def test_el_administrador_edita_un_producto(self):
        self.client.force_authenticate(self.admin)

        respuesta = self.client.put(
            f'/api/productos/{self.margherita.id}/',
            self.datos_producto(nombre='Margherita', precio='10490'),
            format='json'
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.margherita.refresh_from_db()
        self.assertEqual(self.margherita.precio, 10490)

    def test_marcar_un_producto_no_disponible_lo_saca_de_la_carta(self):
        self.client.force_authenticate(self.admin)

        self.client.put(
            f'/api/productos/{self.margherita.id}/',
            self.datos_producto(nombre='Margherita', disponible=False),
            format='json'
        )
        self.client.force_authenticate(None)

        self.assertEqual(self.nombres(self.client.get('/api/productos/')), set())

    def test_eliminar_un_producto_ya_pedido_lo_desactiva_y_conserva_el_historial(self):
        mesa = Mesa.objects.create(numero=1, capacidad=4)
        self.client.post(
            '/api/pedidos/',
            {'mesa_id': mesa.id, 'productos': [{'producto_id': self.margherita.id, 'cantidad': 1}]},
            format='json'
        )
        self.client.force_authenticate(self.admin)

        respuesta = self.client.delete(f'/api/productos/{self.margherita.id}/')

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.margherita.refresh_from_db()
        self.assertFalse(self.margherita.disponible)
        self.assertTrue(DetallePedido.objects.filter(producto=self.margherita).exists())

    def test_un_producto_inexistente_responde_404(self):
        self.client.force_authenticate(self.admin)

        for respuesta in (
            self.client.get('/api/productos/999/'),
            self.client.put('/api/productos/999/', self.datos_producto(), format='json'),
            self.client.delete('/api/productos/999/'),
        ):
            self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)

    def test_garzon_y_cocina_no_crean_editan_ni_eliminan_productos(self):
        cocina = crear_usuario('Cocina')
        for usuario in (self.garzon, cocina):
            self.client.force_authenticate(usuario)
            with self.subTest(rol=usuario.rol.nombre):
                for respuesta in (
                    self.client.post('/api/productos/', self.datos_producto(), format='json'),
                    self.client.put(f'/api/productos/{self.margherita.id}/', self.datos_producto(), format='json'),
                    self.client.delete(f'/api/productos/{self.margherita.id}/'),
                ):
                    self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_sin_sesion_no_se_crean_productos(self):
        respuesta = self.client.post('/api/productos/', self.datos_producto(), format='json')

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)
