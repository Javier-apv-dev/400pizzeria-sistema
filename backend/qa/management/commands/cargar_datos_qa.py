"""Deja el entorno de prueba en su estado inicial y carga los datos de QA.

- Sin opciones: los datos de prueba del catálogo (docs/qa/casos-de-prueba.md), cargados
  pasando por la API real para que corran sus validaciones y la generación de los QR.
- Con --volumen: además, completa 20 mesas, 100 productos y 500 pedidos (RNF5, caso CNF-05).
  Los pedidos se reparten en los últimos 30 días, con su historial de estados y su pago.

Uso, desde backend/:
    python manage.py cargar_datos_qa --settings=config.settings_qa [--volumen]
"""
import random
import secrets
import shutil
from datetime import timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw
from rest_framework.test import APIClient

from apps.mesas.models import Mesa
from apps.pagos.models import Pago
from apps.pedidos.models import DetallePedido, HistorialEstadoPedido, Pedido
from apps.productos.models import Categoria, Producto
from apps.usuarios.models import Rol, Usuario

# ─────────────────────────────────────────────
# Datos de prueba del catálogo (sección «Datos de prueba»)
# ─────────────────────────────────────────────
USUARIOS = [
    ('admin@qa.cl', 'Adriana', 'Soto', 'Administrador'),
    ('garzon@qa.cl', 'Gonzalo', 'Muñoz', 'Garzon'),
    ('cocina@qa.cl', 'Carmen', 'Rivas', 'Cocina'),
]
CATEGORIAS = [
    ('Pizzas', 'Masa delgada, horno a leña', True),
    ('Bebidas', '', True),
    ('Postres', '', False),
]
# nombre, descripción, precio, categoría, disponible, color de la imagen (None = sin imagen)
PRODUCTOS = [
    ('Margherita', 'Salsa de tomate, mozzarella y albahaca', 9990, 'Pizzas', True, (178, 60, 40)),
    ('Diavola', 'Mozzarella y salame picante', 11990, 'Pizzas', True, None),
    ('Capricciosa', 'Jamón, champiñones, alcachofas y aceitunas', 10990, 'Pizzas', False, None),
    ('Coca-Cola', 'Lata 350 ml', 1990, 'Bebidas', True, None),
    ('Tiramisú', 'Receta de la casa', 4990, 'Postres', True, None),
]
MESAS = [(1, 4), (2, 2), (3, 6), (4, 4)]

# ─────────────────────────────────────────────
# Datos de volumen (RNF5): se completan hasta estos totales
# ─────────────────────────────────────────────
TOTAL_MESAS = 20
TOTAL_PRODUCTOS = 100
TOTAL_PEDIDOS = 500
DIAS_DE_HISTORIA = 30

# categoría (nueva o existente), nombres, precio mínimo y máximo
PRODUCTOS_VOLUMEN = [
    ('Pizzas', [
        f'{nombre} {tamano}'
        for nombre in ('Fugazza', 'Prosciutto', 'Funghi', 'Quattro Formaggi', 'Hawaiana',
                       'Vegetariana', 'Marinara', 'Calzone', 'Carbonara', 'Pollo BBQ',
                       'Española', 'Primavera', 'Pesto', 'Rúcula y serrano', 'Salame',
                       'Cuatro Estaciones', 'Mechada', 'Camarón', 'Champiñón', 'Choclo y albahaca')
        for tamano in ('individual', 'familiar')
    ], 7990, 16990),
    ('Bebidas', [
        'Coca-Cola Zero', 'Sprite', 'Fanta', 'Agua con gas', 'Agua sin gas',
        'Jugo de frambuesa', 'Jugo de mango', 'Limonada', 'Limonada menta jengibre', 'Té',
        'Café espresso', 'Café cortado', 'Cerveza rubia', 'Cerveza roja', 'Cerveza sin alcohol',
        'Kombucha', 'Ginger ale', 'Agua tónica', 'Jugo de naranja', 'Mote con huesillo',
        'Chocolate caliente', 'Capuchino', 'Té helado', 'Néctar de durazno', 'Bebida energética',
    ], 1490, 4990),
    ('Entradas', [
        'Pan de ajo', 'Bruschetta', 'Focaccia', 'Papas fritas', 'Aros de cebolla',
        'Empanaditas de queso', 'Tabla de quesos', 'Ensalada César', 'Ensalada caprese',
        'Alitas BBQ', 'Nachos', 'Provoleta', 'Antipasto', 'Palitos de mozzarella',
        'Champiñones al ajillo',
    ], 3990, 8990),
    ('Pastas', [
        'Lasaña boloñesa', 'Lasaña vegetariana', 'Fettuccine Alfredo', 'Spaghetti boloñesa',
        'Spaghetti carbonara', 'Ravioles de ricota', 'Ñoquis al pesto', 'Penne arrabbiata',
        'Canelones', 'Sorrentinos', 'Tallarines a la crema', 'Fusilli primavera',
        'Pappardelle con ragú', 'Linguine con camarones', 'Gnocchi cuatro quesos',
    ], 7990, 11990),
]
NOTAS = ['sin cebolla', 'bien cocida', 'sin hielo', 'extra queso', 'cortada en 8', 'sin sal']
# Pedidos en curso al cargar los datos, como en un turno con movimiento
ACTIVOS = {'pendiente': 5, 'en_preparacion': 4, 'listo': 3}
METODOS = (['efectivo'] * 30 + ['debito'] * 35 + ['credito'] * 20 + ['transferencia'] * 15)


class Command(BaseCommand):
    help = 'Reinicia la base de prueba y carga los datos de QA (con --volumen, los del RNF5).'

    def add_arguments(self, parser):
        parser.add_argument('--volumen', action='store_true',
                            help='Completa 20 mesas, 100 productos y 500 pedidos (RNF5).')
        parser.add_argument('--semilla', type=int, default=400,
                            help='Semilla aleatoria, para repetir exactamente los mismos datos.')

    def handle(self, *args, **opciones):
        verificar_entorno()
        self.azar = random.Random(opciones['semilla'])

        call_command('migrate', verbosity=0)
        call_command('flush', interactive=False, verbosity=0)
        shutil.rmtree(Path(settings.MEDIA_ROOT) / 'productos', ignore_errors=True)

        claves = self.crear_usuarios()
        admin = cliente_con_sesion('admin@qa.cl', claves['admin@qa.cl'])
        self.cargar_datos_base(admin)
        if opciones['volumen']:
            self.cargar_volumen(admin)

        self.resumen()

    # ─────────────────────────────────────────
    # Usuarios: las contraseñas no se publican; quedan en credenciales.txt
    # ─────────────────────────────────────────
    def crear_usuarios(self):
        archivo = Path(settings.QA_DIR) / 'credenciales.txt'
        claves = leer_credenciales(archivo)

        for email, nombre, apellido, rol in USUARIOS:
            claves.setdefault(email, secrets.token_urlsafe(9))
            Usuario.objects.create_user(
                email, nombre, apellido, claves[email],
                rol=Rol.objects.get_or_create(nombre=rol)[0]
            )

        # Se conservan las claves de la carga anterior, para no tener que repartirlas de nuevo
        archivo.write_text(
            '\n'.join(f'{rol}: {email} / {claves[email]}' for email, _, _, rol in USUARIOS) + '\n',
            encoding='utf-8'
        )
        self.stdout.write(f'Credenciales del personal en {archivo}')
        return claves

    # ─────────────────────────────────────────
    # Datos del catálogo, pasando por la API
    # ─────────────────────────────────────────
    def cargar_datos_base(self, admin):
        categorias = {}
        for nombre, descripcion, _ in CATEGORIAS:
            categorias[nombre] = crear(admin, '/api/categorias/', {
                'nombre': nombre, 'descripcion': descripcion
            })

        for nombre, descripcion, precio, categoria, disponible, color in PRODUCTOS:
            datos = {
                'nombre': nombre,
                'descripcion': descripcion,
                'precio': str(precio),
                'categoria_id': categorias[categoria],
                'disponible': str(disponible).lower(),
            }
            if color:
                datos['imagen'] = imagen_de_prueba(nombre, color)
            crear(admin, '/api/productos/', datos, formato='multipart')

        # Postres se desactiva después de crear el Tiramisú, como lo haría el Administrador
        for nombre, _, activa in CATEGORIAS:
            if not activa:
                respuesta = admin.patch(f'/api/categorias/{categorias[nombre]}/estado/',
                                        {'activo': False}, format='json')
                exigir(respuesta, 200)

        for numero, capacidad in MESAS:
            crear(admin, '/api/mesas/', {'numero': numero, 'capacidad': capacidad})

    # ─────────────────────────────────────────
    # Volumen del RNF5
    # ─────────────────────────────────────────
    def cargar_volumen(self, admin):
        # Mesas y productos por la API (generan su QR y pasan las validaciones)
        for numero in range(Mesa.objects.count() + 1, TOTAL_MESAS + 1):
            crear(admin, '/api/mesas/', {'numero': numero, 'capacidad': self.azar.choice([2, 4, 4, 6])})

        faltan = TOTAL_PRODUCTOS - Producto.objects.count()
        nuevos = [(cat, nombre, minimo, maximo)
                  for cat, nombres, minimo, maximo in PRODUCTOS_VOLUMEN for nombre in nombres]
        for i, (categoria, nombre, minimo, maximo) in enumerate(nuevos[:faltan]):
            cat = Categoria.objects.filter(nombre=categoria).first()
            if not cat:
                cat = Categoria.objects.get(pk=crear(admin, '/api/categorias/', {'nombre': categoria}))
            crear(admin, '/api/productos/', {
                'nombre': nombre,
                'descripcion': '',
                'precio': str(self.azar.randrange(minimo, maximo + 1, 500)),
                'categoria_id': cat.id,
                'disponible': i % 12 != 11,  # algunos agotados
            })

        # Los pedidos van directo a la base: la API no permite fechar pedidos en el pasado
        self.crear_pedidos()

    @transaction.atomic
    def crear_pedidos(self):
        azar = self.azar
        usuarios = {u.rol.nombre: u for u in Usuario.objects.select_related('rol')}
        productos = list(Producto.objects.filter(disponible=True, categoria__activo=True))
        mesas = list(Mesa.objects.order_by('numero'))
        ahora = timezone.localtime()

        # Los activos quedan en mesas distintas, desde la 5: las mesas 1 a 4 siguen libres
        # para los casos funcionales
        activos = [estado for estado, n in ACTIVOS.items() for _ in range(n)]
        mesas_activas = mesas[4:4 + len(activos)]
        historicos = TOTAL_PEDIDOS - Pedido.objects.count() - len(activos)

        # Cada pedido: estado final, mesa, hora de creación y los pasos de su historial
        planes = []
        for _ in range(historicos):
            dia = ahora - timedelta(days=azar.randint(1, DIAS_DE_HISTORIA))
            creado = dia.replace(hour=12, minute=30, second=0, microsecond=0) \
                + timedelta(minutes=azar.randint(0, 10 * 60))
            planes.append(('entregado', azar.choice(mesas), creado, self.pasos('entregado', creado)))
        for estado, mesa in zip(activos, mesas_activas):
            # Los activos llevan de 1 a 30 minutos en su estado actual, sin fechas futuras
            pasos = self.pasos(estado, ahora)
            atraso = (pasos[-1][2] - ahora) + timedelta(minutes=azar.randint(1, 30))
            pasos = [(paso, usuario, fecha - atraso) for paso, usuario, fecha in pasos]
            planes.append((estado, mesa, pasos[0][2], pasos))
        planes.sort(key=lambda plan: plan[2])

        detalles, historial = [], []
        for estado, mesa, creado, pasos in planes:
            lineas = []
            for producto in azar.sample(productos, azar.choice([1, 1, 2, 2, 3, 4])):
                cantidad = azar.choice([1, 1, 1, 2, 2, 3])
                lineas.append((producto, cantidad, producto.precio * cantidad))
            pedido = Pedido.objects.create(
                mesa=mesa, estado=estado, total=sum(sub for _, _, sub in lineas)
            )
            # fecha_creacion es auto_now_add: se corrige después de crear el pedido
            Pedido.objects.filter(pk=pedido.pk).update(fecha_creacion=creado)

            for producto, cantidad, subtotal in lineas:
                detalles.append(DetallePedido(
                    pedido=pedido, producto=producto, cantidad=cantidad,
                    precio_unitario=producto.precio, subtotal=subtotal,
                    nota=azar.choice(NOTAS) if azar.random() < 0.1 else ''
                ))

            for paso, rol, fecha in pasos:
                historial.append(HistorialEstadoPedido(
                    pedido=pedido, estado=paso, fecha=fecha, usuario=usuarios.get(rol)
                ))
            if estado == 'entregado':
                self.pagar(pedido, pasos[-1][2], usuarios['Garzon'], usuarios['Administrador'])

        DetallePedido.objects.bulk_create(detalles)
        HistorialEstadoPedido.objects.bulk_create(historial)
        Mesa.objects.filter(pk__in=[m.pk for m in mesas_activas]).update(estado=Mesa.Estado.OCUPADA)

    def pasos(self, estado, creado):
        """Historial desde 'pendiente' hasta `estado`, con el rol que hace cada paso."""
        azar = self.azar
        minutos = [('pendiente', None, 0), ('en_preparacion', 'Cocina', azar.randint(2, 8)),
                   ('listo', 'Cocina', azar.randint(10, 20)), ('entregado', 'Garzon', azar.randint(2, 8))]
        pasos, fecha = [], creado
        for paso, rol, espera in minutos:
            fecha += timedelta(minutes=espera)
            pasos.append((paso, rol, fecha))
            if paso == estado:
                return pasos

    def pagar(self, pedido, entregado, garzon, admin):
        azar = self.azar
        cobrado = entregado + timedelta(minutes=azar.randint(15, 45))
        cajero = garzon if azar.random() < 0.8 else admin

        # Unos pocos cobros se anulan y se vuelven a registrar (queda el historial)
        if azar.random() < 0.03:
            anulado = Pago.objects.create(
                pedido=pedido, metodo_pago=azar.choice(METODOS), monto=pedido.total,
                estado=Pago.Estado.ANULADO, registrado_por=cajero, anulado_por=admin
            )
            Pago.objects.filter(pk=anulado.pk).update(fecha=cobrado - timedelta(minutes=5))

        pago = Pago.objects.create(
            pedido=pedido, metodo_pago=azar.choice(METODOS), monto=pedido.total,
            estado=Pago.Estado.COMPLETADO, registrado_por=cajero
        )
        Pago.objects.filter(pk=pago.pk).update(fecha=cobrado)

    def resumen(self):
        por_estado = {e: Pedido.objects.filter(estado=e).count() for e in Pedido.Estado.values}
        self.stdout.write(self.style.SUCCESS('Datos de QA cargados en ' + str(settings.DATABASES['default']['NAME'])))
        self.stdout.write(f'  usuarios: {Usuario.objects.count()} · categorías: {Categoria.objects.count()} '
                          f'· productos: {Producto.objects.count()} · mesas: {Mesa.objects.count()}')
        self.stdout.write(f'  pedidos: {Pedido.objects.count()} {por_estado} · pagos: {Pago.objects.count()}')


def verificar_entorno():
    """Se niega a correr fuera de la base SQLite de prueba: nunca toca la base real."""
    base = settings.DATABASES['default']
    qa_dir = getattr(settings, 'QA_DIR', None)
    if (base['ENGINE'] != 'django.db.backends.sqlite3' or qa_dir is None
            or Path(base['NAME']).parent != Path(qa_dir)):
        raise CommandError('Este comando solo se ejecuta con --settings=config.settings_qa.')


def leer_credenciales(archivo):
    """Lee 'Rol: email / clave' de una carga anterior; devuelve {email: clave}."""
    claves = {}
    if archivo.exists():
        for linea in archivo.read_text(encoding='utf-8').splitlines():
            if ': ' in linea and ' / ' in linea:
                email, clave = linea.split(': ', 1)[1].split(' / ', 1)
                claves[email.strip()] = clave.strip()
    return claves


def cliente_con_sesion(email, clave):
    cliente = APIClient()
    respuesta = cliente.post('/api/auth/login/', {'email': email, 'password': clave}, format='json')
    exigir(respuesta, 200)
    cliente.credentials(HTTP_AUTHORIZATION='Bearer ' + respuesta.data['access'])
    return cliente


def crear(cliente, ruta, datos, formato='json'):
    """POST a la API; devuelve el id creado o detiene la carga si la API lo rechaza."""
    respuesta = cliente.post(ruta, datos, format=formato)
    exigir(respuesta, 201)
    return respuesta.data['id']


def exigir(respuesta, codigo):
    if respuesta.status_code != codigo:
        raise CommandError(f'{respuesta.request["REQUEST_METHOD"]} {respuesta.request["PATH_INFO"]} '
                           f'respondió {respuesta.status_code}: {respuesta.data}')


def imagen_de_prueba(nombre, color):
    imagen = Image.new('RGB', (480, 360), color)
    ImageDraw.Draw(imagen).text((20, 20), nombre, fill=(255, 255, 255))
    buffer = BytesIO()
    imagen.save(buffer, 'JPEG')
    return SimpleUploadedFile(f'{nombre.lower()}.jpg', buffer.getvalue(), 'image/jpeg')
