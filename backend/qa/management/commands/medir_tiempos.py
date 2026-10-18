"""Mide los tiempos de respuesta de la API con usuarios simultáneos (RNF3, caso CNF-04).

Hace peticiones HTTP reales a un servidor en marcha, como lo harían la carta y el panel:
1. Un usuario: cada ruta se pide varias veces seguidas, como línea base.
2. Usuarios simultáneos (10 por defecto) durante un tiempo fijo, sin pausas entre peticiones.
   Se reparten en clientes que ven la carta y piden; cocina, que prepara los pedidos, y
   garzones, que los entregan y cobran.

Criterio del RNF3: p95 < 1.500 ms en todas las rutas; carta (categorías y productos) y
pedidos activos, p95 < 800 ms. El reporte (Markdown) y cada petición (CSV) quedan en
<QA_DIR>/mediciones/.

Uso, desde backend/, con el servidor de prueba levantado en otra terminal:
    python manage.py runserver --settings=config.settings_qa
    python manage.py medir_tiempos --settings=config.settings_qa [--usuarios 10] [--duracion 60]
"""
import csv
import http.client
import json
import math
import platform
import random
import statistics
import subprocess
import threading
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import django
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from qa.management.commands.cargar_datos_qa import leer_credenciales

UMBRAL_GENERAL_MS = 1500
UMBRAL_CARTA_Y_ACTIVOS_MS = 800

# Rutas medidas: etiqueta → umbral de p95. La vista «Activos» de Pedidos pide GET /api/pedidos/
RUTAS = {
    'GET /api/categorias/': UMBRAL_CARTA_Y_ACTIVOS_MS,
    'GET /api/productos/?categoria={id}': UMBRAL_CARTA_Y_ACTIVOS_MS,
    'GET /api/pedidos/': UMBRAL_CARTA_Y_ACTIVOS_MS,
    'GET /api/mesas/{id}/': UMBRAL_GENERAL_MS,
    'GET /api/mesas/': UMBRAL_GENERAL_MS,
    'GET /api/solicitudes/?estado=pendiente': UMBRAL_GENERAL_MS,
    'GET /api/productos/': UMBRAL_GENERAL_MS,
    'GET /api/pagos/': UMBRAL_GENERAL_MS,
    'GET /api/pedidos/?estado=entregado': UMBRAL_GENERAL_MS,
    'POST /api/pedidos/': UMBRAL_GENERAL_MS,
    'POST /api/mesas/{id}/solicitudes/': UMBRAL_GENERAL_MS,
    'PATCH /api/pedidos/{id}/estado/': UMBRAL_GENERAL_MS,
    'POST /api/pagos/': UMBRAL_GENERAL_MS,
}
# Respuestas esperadas: dos usuarios del mismo rol pueden intentar avanzar o cobrar el mismo
# pedido, y el segundo recibe 400; una solicitud ya pendiente se devuelve con 200
ESPERADOS = {
    'POST /api/pedidos/': {201},
    'POST /api/pagos/': {201, 400},
    'POST /api/mesas/{id}/solicitudes/': {200, 201},
    'PATCH /api/pedidos/{id}/estado/': {200, 400},
}
SIGUIENTE = {'pendiente': 'en_preparacion', 'en_preparacion': 'listo', 'listo': 'entregado'}


class Command(BaseCommand):
    help = 'Mide media y p95 por ruta con usuarios simultáneos contra el servidor de prueba (RNF3).'

    def add_arguments(self, parser):
        parser.add_argument('--url', default='http://127.0.0.1:8000', help='Servidor bajo prueba.')
        parser.add_argument('--usuarios', type=int, default=10, help='Usuarios simultáneos.')
        parser.add_argument('--duracion', type=int, default=60, help='Segundos de la fase simultánea.')
        parser.add_argument('--repeticiones', type=int, default=20,
                            help='Peticiones por ruta en la fase de un usuario.')
        parser.add_argument('--pausa', type=float, default=0,
                            help='Segundos de espera entre una vuelta y otra de cada usuario.')
        parser.add_argument('--pedido-cada', type=int, default=20,
                            help='Cada cuántos segundos envía un pedido cada cliente.')
        parser.add_argument('--semilla', type=int, default=400)
        parser.add_argument('--salida', help='Carpeta del reporte (por defecto <QA_DIR>/mediciones).')

    def handle(self, *args, **op):
        self.url = op['url'].rstrip('/')
        self.servidor = urllib.parse.urlsplit(self.url)
        if self.servidor.scheme != 'http' or self.servidor.path:
            raise CommandError('--url debe ser http://<host>:<puerto>, sin ruta.')
        self.op = op
        self.muestras = []
        self.candado = threading.Lock()
        self.hilo = threading.local()  # conexión HTTP propia de cada usuario virtual

        self.preparar()
        volumen_inicial = self.volumen()

        self.stdout.write(f'Fase 1: un usuario, {op["repeticiones"]} peticiones por ruta…')
        self.fase_un_usuario()

        perfiles = repartir_perfiles(op['usuarios'])
        self.stdout.write(f'Fase 2: {op["usuarios"]} usuarios simultáneos durante {op["duracion"]} s '
                          f'({", ".join(f"{n} {p}" for p, n in contar(perfiles).items())})…')
        inicio = time.perf_counter()
        self.fase_simultanea(perfiles)
        segundos = time.perf_counter() - inicio

        reporte = self.escribir_reporte(volumen_inicial, self.volumen(), perfiles, segundos)
        self.stdout.write(self.style.SUCCESS(f'Reporte: {reporte}'))

    # ─────────────────────────────────────────
    # Preparación: sesión del personal y datos que usan las peticiones
    # ─────────────────────────────────────────
    def preparar(self):
        try:
            self.pedir('GET', '/api/categorias/', registrar=False)
        except OSError as error:
            raise CommandError(f'No responde el servidor en {self.url} ({error}). Levántalo con: '
                               'python manage.py runserver --settings=config.settings_qa')

        claves = leer_credenciales(Path(settings.QA_DIR) / 'credenciales.txt')
        self.tokens = {}
        for perfil, email in (('garzón', 'garzon@qa.cl'), ('cocina', 'cocina@qa.cl')):
            if email not in claves:
                raise CommandError('Faltan las credenciales de QA: corre antes cargar_datos_qa.')
            estado, _, datos = self.pedir('POST', '/api/auth/login/', registrar=False,
                                          cuerpo={'email': email, 'password': claves[email]})
            # Si no entra con las cuentas de QA, no es el servidor de prueba: no se mide
            if estado != 200:
                raise CommandError(f'{email} no pudo iniciar sesión en {self.url} ({estado}). '
                                   '¿Es el servidor de prueba, con los datos de cargar_datos_qa?')
            self.tokens[perfil] = datos['access']

        _, _, mesas = self.pedir('GET', '/api/mesas/', registrar=False)
        _, _, categorias = self.pedir('GET', '/api/categorias/', registrar=False)
        self.mesas = [m['id'] for m in mesas]
        self.categorias = [c['id'] for c in categorias]
        self.productos = {}
        for categoria in self.categorias:
            _, _, productos = self.pedir('GET', f'/api/productos/?categoria={categoria}', registrar=False)
            self.productos[categoria] = [p['id'] for p in productos]
        if not self.mesas or not any(self.productos.values()):
            raise CommandError('La base de prueba no tiene mesas o productos: corre cargar_datos_qa.')

    def volumen(self):
        token = self.tokens['garzón']
        return {nombre: len(self.pedir('GET', ruta, token, registrar=False)[2])
                for nombre, ruta in (('mesas', '/api/mesas/'), ('productos', '/api/productos/'),
                                     ('pedidos', '/api/pedidos/'), ('pagos', '/api/pagos/'))}

    # ─────────────────────────────────────────
    # Fases de medición
    # ─────────────────────────────────────────
    def fase_un_usuario(self):
        garzon = self.tokens['garzón']
        mesa, categoria = self.mesas[0], self.categorias[0]
        lecturas = [
            ('GET /api/categorias/', '/api/categorias/', None),
            ('GET /api/productos/?categoria={id}', f'/api/productos/?categoria={categoria}', None),
            ('GET /api/mesas/{id}/', f'/api/mesas/{mesa}/', None),
            ('GET /api/pedidos/', '/api/pedidos/', garzon),
            ('GET /api/mesas/', '/api/mesas/', garzon),
            ('GET /api/solicitudes/?estado=pendiente', '/api/solicitudes/?estado=pendiente', garzon),
            ('GET /api/productos/', '/api/productos/', garzon),
            ('GET /api/pagos/', '/api/pagos/', garzon),
            ('GET /api/pedidos/?estado=entregado', '/api/pedidos/?estado=entregado', garzon),
        ]
        for etiqueta, ruta, token in lecturas:
            self.pedir('GET', ruta, token, registrar=False)  # calentamiento, no se cuenta
            for _ in range(self.op['repeticiones']):
                self.pedir('GET', ruta, token, etiqueta=etiqueta, fase=1, perfil='un usuario')

    def fase_simultanea(self, perfiles):
        fin = time.perf_counter() + self.op['duracion']
        hilos = [threading.Thread(target=self.usuario_virtual, args=(i, perfil, fin))
                 for i, perfil in enumerate(perfiles)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

    def usuario_virtual(self, numero, perfil, fin):
        azar = random.Random(self.op['semilla'] + numero)
        mesa = self.mesas[numero % len(self.mesas)]
        ultimo_pedido = time.perf_counter() - azar.uniform(0, self.op['pedido_cada'])
        while time.perf_counter() < fin:
            if perfil == 'cliente':
                ultimo_pedido = self.vuelta_cliente(azar, mesa, ultimo_pedido)
            else:
                self.vuelta_personal(azar, perfil)
            if self.op['pausa']:
                time.sleep(self.op['pausa'])

    def vuelta_cliente(self, azar, mesa, ultimo_pedido):
        """Abre la carta de su mesa, recorre categorías y, cada cierto tiempo, pide."""
        def pedir(metodo, etiqueta, ruta, cuerpo=None):
            return self.pedir(metodo, ruta, cuerpo=cuerpo, etiqueta=etiqueta, fase=2, perfil='cliente')

        pedir('GET', 'GET /api/mesas/{id}/', f'/api/mesas/{mesa}/')
        pedir('GET', 'GET /api/categorias/', '/api/categorias/')
        for categoria in azar.sample(self.categorias, min(2, len(self.categorias))):
            pedir('GET', 'GET /api/productos/?categoria={id}', f'/api/productos/?categoria={categoria}')

        if time.perf_counter() - ultimo_pedido >= self.op['pedido_cada']:
            disponibles = [p for lista in self.productos.values() for p in lista]
            productos = [{'producto_id': p, 'cantidad': azar.randint(1, 2)}
                         for p in azar.sample(disponibles, min(azar.randint(1, 3), len(disponibles)))]
            pedir('POST', 'POST /api/pedidos/', '/api/pedidos/', {'mesa_id': mesa, 'productos': productos})
            ultimo_pedido = time.perf_counter()
        elif azar.random() < 0.1:
            pedir('POST', 'POST /api/mesas/{id}/solicitudes/', f'/api/mesas/{mesa}/solicitudes/',
                  {'tipo': azar.choice(['garzon', 'cuenta'])})
        return ultimo_pedido

    def vuelta_personal(self, azar, perfil):
        """Garzón y cocina miran la vista «Activos» y avanzan un pedido si les toca."""
        token = self.tokens[perfil]

        def pedir(metodo, etiqueta, ruta, cuerpo=None):
            return self.pedir(metodo, ruta, token, cuerpo, etiqueta=etiqueta, fase=2, perfil=perfil)

        _, _, pedidos = pedir('GET', 'GET /api/pedidos/', '/api/pedidos/')
        activos = [p for p in (pedidos or []) if p['estado'] != 'entregado']
        avanza = ('listo',) if perfil == 'garzón' else ('pendiente', 'en_preparacion')
        candidatos = [p for p in activos if p['estado'] in avanza]
        if candidatos:
            pedido = azar.choice(candidatos)
            estado, _, avanzado = pedir('PATCH', 'PATCH /api/pedidos/{id}/estado/',
                                        f'/api/pedidos/{pedido["id"]}/estado/',
                                        {'estado': SIGUIENTE[pedido['estado']]})
            if perfil == 'garzón' and estado == 200:
                self.cobrar(pedir, azar, avanzado)

        if perfil == 'garzón':
            pedir('GET', 'GET /api/solicitudes/?estado=pendiente', '/api/solicitudes/?estado=pendiente')
            pedir('GET', 'GET /api/mesas/', '/api/mesas/')
            if azar.random() < 0.2:  # de vez en cuando abre el Dashboard
                pedir('GET', 'GET /api/pagos/', '/api/pagos/')
                pedir('GET', 'GET /api/productos/', '/api/productos/')

    def cobrar(self, pedir, azar, pedido):
        """Como «Registrar pago» en la pantalla Pagos: busca los entregados sin pago y cobra uno."""
        _, _, entregados = pedir('GET', 'GET /api/pedidos/?estado=entregado', '/api/pedidos/?estado=entregado')
        _, _, pagos = pedir('GET', 'GET /api/pagos/', '/api/pagos/')
        con_pago = {p['pedido']['id'] for p in pagos or [] if p['estado'] != 'anulado'}
        if pedido['id'] in {p['id'] for p in entregados or []} - con_pago:
            pedir('POST', 'POST /api/pagos/', '/api/pagos/', {
                'pedido_id': pedido['id'],
                'metodo_pago': azar.choice(['efectivo', 'debito', 'credito', 'transferencia']),
                'monto': pedido['total'],
            })

    # ─────────────────────────────────────────
    # Una petición HTTP, cronometrada
    # ─────────────────────────────────────────
    def pedir(self, metodo, ruta, token=None, cuerpo=None, etiqueta=None, fase=None, perfil=None,
              registrar=True):
        cabeceras = {'Accept': 'application/json'}
        datos = None
        if cuerpo is not None:
            datos = json.dumps(cuerpo).encode('utf-8')
            cabeceras['Content-Type'] = 'application/json'
        if token:
            cabeceras['Authorization'] = f'Bearer {token}'

        inicio = time.perf_counter()
        try:
            estado, contenido = self.enviar(metodo, ruta, datos, cabeceras)
        except (OSError, http.client.HTTPException) as error:
            if not registrar:
                raise
            estado, contenido = 0, str(error).encode()
        ms = (time.perf_counter() - inicio) * 1000

        if registrar:
            esperado = estado in ESPERADOS.get(etiqueta, {200})
            with self.candado:
                self.muestras.append({
                    'fase': fase, 'perfil': perfil, 'ruta': etiqueta, 'url': ruta, 'estado': estado,
                    'ms': round(ms, 1), 'bytes': len(contenido), 'error': not esperado,
                })
        try:
            return estado, ms, json.loads(contenido) if contenido else None
        except ValueError:
            return estado, ms, None

    def enviar(self, metodo, ruta, datos, cabeceras):
        """Cada usuario virtual reutiliza su conexión (keep-alive), como un navegador.

        Abrir una conexión por petición agota los puertos locales de Windows a cientos de
        peticiones por segundo. Si el servidor cerró la conexión, se reabre y se reintenta
        una vez; el tiempo medido incluye el reintento.
        """
        for intento in (1, 2):
            conexion = getattr(self.hilo, 'conexion', None)
            if conexion is None:
                conexion = self.hilo.conexion = http.client.HTTPConnection(
                    self.servidor.hostname, self.servidor.port or 80, timeout=30)
            try:
                conexion.request(metodo, ruta, body=datos, headers=cabeceras)
                respuesta = conexion.getresponse()
                return respuesta.status, respuesta.read()
            except (http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError):
                conexion.close()
                self.hilo.conexion = None
                if intento == 2:
                    raise

    # ─────────────────────────────────────────
    # Reporte
    # ─────────────────────────────────────────
    def escribir_reporte(self, volumen_inicial, volumen_final, perfiles, segundos):
        ahora = datetime.now()
        carpeta = Path(self.op['salida'] or Path(settings.QA_DIR) / 'mediciones')
        carpeta.mkdir(parents=True, exist_ok=True)
        nombre = f'rnf3_{ahora:%Y-%m-%d_%H%M}_{volumen_inicial["pedidos"]}-pedidos'

        with open(carpeta / f'{nombre}.csv', 'w', newline='', encoding='utf-8') as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=list(self.muestras[0]))
            escritor.writeheader()
            escritor.writerows(self.muestras)

        fase1 = agrupar(m for m in self.muestras if m['fase'] == 1)
        fase2 = agrupar(m for m in self.muestras if m['fase'] == 2)
        todas = [m for m in self.muestras if m['fase'] == 2]
        p95_global = percentil([m['ms'] for m in todas], 95)
        errores = sum(m['error'] for m in todas)
        rechazos = {ruta: sum(m['estado'] == 400 for m in todas if m['ruta'] == ruta)
                    for ruta in ('PATCH /api/pedidos/{id}/estado/', 'POST /api/pagos/')}

        filas, cumple = [], p95_global < UMBRAL_GENERAL_MS and errores == 0
        for ruta, umbral in RUTAS.items():
            if ruta not in fase2:
                continue
            s = resumen(fase2[ruta])
            ok = s['p95'] < umbral and s['errores'] == 0
            cumple = cumple and ok
            filas.append(f'| `{ruta}` | {s["n"]} | {s["errores"]} | {s["media"]:.0f} | {s["p50"]:.0f} | '
                         f'{s["p95"]:.0f} | {s["max"]:.0f} | {s["kib"]:.1f} | < {miles(umbral)} '
                         f'| {"Cumple" if ok else "**No cumple**"} |')

        base = []
        for ruta in RUTAS:
            if ruta in fase1:
                s = resumen(fase1[ruta])
                base.append(f'| `{ruta}` | {s["n"]} | {s["media"]:.0f} | {s["p95"]:.0f} | {s["max"]:.0f} '
                            f'| {s["kib"]:.1f} |')

        resultado = (f'**Resultado: {"CUMPLE" if cumple else "NO CUMPLE"} el RNF3** (p95 < 1.500 ms en todas '
                     'las rutas; carta y pedidos activos, p95 < 800 ms; sin errores).')
        fase2_texto = (f'{len(todas)} peticiones en {segundos:.0f} s ({len(todas) / segundos:.1f} por segundo). '
                       f'p95 global: **{p95_global:.0f} ms**. Errores: {errores}.')
        tabla_fase2 = [
            '| Ruta | Peticiones | Errores | Media (ms) | p50 (ms) | p95 (ms) | Máx. (ms) | KiB por respuesta '
            '| Umbral p95 (ms) | Resultado |',
            '|---|---|---|---|---|---|---|---|---|---|',
            *filas,
        ]
        lineas = [
            f'# Medición de tiempos de respuesta (RNF3) · {ahora:%d-%m-%Y %H:%M}',
            '',
            resultado,
            '',
            '## Entorno',
            '',
            f'- Servidor: `{self.url}` (`runserver` de Django con `config.settings_qa`, base SQLite).',
            f'- Commit: `{commit_actual()}` · Python {platform.python_version()} · Django {django.get_version()} '
            f'· {platform.system()} {platform.release()}, {platform.processor() or platform.machine()}.',
            f'- Datos al inicio: {volumen_inicial["mesas"]} mesas, {volumen_inicial["productos"]} productos, '
            f'{volumen_inicial["pedidos"]} pedidos y {volumen_inicial["pagos"]} pagos. '
            f'Al final: {volumen_final["pedidos"]} pedidos y {volumen_final["pagos"]} pagos.',
            f'- Parámetros: {self.op["usuarios"]} usuarios simultáneos '
            f'({", ".join(f"{n} {p}" for p, n in contar(perfiles).items())}), {self.op["duracion"]} s, '
            f'pausa entre vueltas {self.op["pausa"]} s, un pedido cada {self.op["pedido_cada"]} s por cliente, '
            f'semilla {self.op["semilla"]}.',
            '',
            '## Fase 2 · Usuarios simultáneos',
            '',
            fase2_texto,
            '',
            *tabla_fase2,
            '',
            '## Fase 1 · Un usuario (línea base)',
            '',
            '| Ruta | Peticiones | Media (ms) | p95 (ms) | Máx. (ms) | KiB por respuesta |',
            '|---|---|---|---|---|---|',
            *base,
            '',
            '## Cómo se calculó',
            '',
            '- Cada tiempo va desde que se envía la petición hasta que se termina de recibir la respuesta.',
            '- El p95 usa el método del rango más cercano: el valor bajo el cual queda el 95 % de las peticiones.',
            '- Error: una respuesta distinta de la esperada (200 en las lecturas, 201 al crear un pedido) o '
            'una petición sin respuesta. Dos usuarios del mismo rol pueden intentar avanzar o cobrar el mismo '
            'pedido: el segundo recibe 400, que es el comportamiento correcto y no cuenta como error. '
            f'Rechazos 400 en esta corrida: {rechazos["PATCH /api/pedidos/{id}/estado/"]} al avanzar un '
            f'pedido y {rechazos["POST /api/pagos/"]} al cobrar.',
            f'- Detalle de cada petición: `{nombre}.csv`.',
        ]
        reporte = carpeta / f'{nombre}.md'
        reporte.write_text('\n'.join(lineas) + '\n', encoding='utf-8')

        self.stdout.write('\n'.join([resultado, fase2_texto, *tabla_fase2]))
        return reporte


def repartir_perfiles(usuarios):
    """60 % clientes, 20 % garzones y 20 % cocina (con 10 usuarios: 6, 2 y 2)."""
    personal = max(1, round(usuarios * 0.2))
    clientes = max(1, usuarios - 2 * personal)
    return ['cliente'] * clientes + ['garzón'] * personal + ['cocina'] * personal


def contar(perfiles):
    return {p: perfiles.count(p) for p in dict.fromkeys(perfiles)}


def agrupar(muestras):
    grupos = {}
    for m in muestras:
        grupos.setdefault(m['ruta'], []).append(m)
    return grupos


def percentil(valores, p):
    """Rango más cercano: el menor valor que deja al menos el p % de las muestras a su izquierda."""
    ordenados = sorted(valores)
    return ordenados[max(0, math.ceil(p / 100 * len(ordenados)) - 1)]


def resumen(muestras):
    ms = [m['ms'] for m in muestras]
    return {
        'n': len(ms),
        'errores': sum(m['error'] for m in muestras),
        'media': statistics.fmean(ms),
        'p50': percentil(ms, 50),
        'p95': percentil(ms, 95),
        'max': max(ms),
        'kib': statistics.fmean(m['bytes'] for m in muestras) / 1024,
    }


def miles(numero):
    return f'{numero:,}'.replace(',', '.')


def commit_actual():
    try:
        return subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True,
                              cwd=settings.BASE_DIR, timeout=5).stdout.strip() or 'desconocido'
    except (OSError, subprocess.SubprocessError):
        return 'desconocido'
