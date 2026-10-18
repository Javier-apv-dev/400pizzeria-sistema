# 400 Pizzería — Sistema web de gestión operativa interna

Sistema web desarrollado como proyecto de título de Ingeniería en Computación e Informática (Universidad Andrés Bello) para **400 Pizzería**, restaurante de la Región Metropolitana de Santiago de Chile.

La plataforma reemplaza la toma de pedidos verbal, el control visual de mesas y el registro manual de ventas por dos interfaces que consumen una misma API REST:

- **Carta digital pública**: el cliente escanea el código QR de su mesa, navega el menú por categorías, arma su pedido y lo envía a cocina sin intervención del garzón ni autenticación.
- **Panel administrativo**: interfaz protegida con JWT y control de acceso por rol para gestionar usuarios, categorías, productos, mesas, pedidos y pagos.

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | React 19, Vite 8, React Router 7, Axios, react-hot-toast, lucide-react |
| Backend | Python 3.14, Django 6.0, Django REST Framework 3.17, SimpleJWT 5.5 (con blacklist), django-cors-headers, qrcode, Pillow |
| Base de datos | MySQL (driver `mysqlclient`, charset `utf8mb4`) |
| Autenticación | JSON Web Token (access 8 h, refresh 24 h, rotación + blacklist) |

## Estructura del repositorio

```
400pizzeria/
├── backend/
│   ├── config/            # settings, urls raíz y clases de permisos por rol (permissions.py)
│   ├── apps/
│   │   ├── usuarios/      # Usuario (login por email), Rol, login/logout/perfil
│   │   ├── productos/     # Categoria, Producto (imagen, disponibilidad)
│   │   ├── mesas/         # Mesa + generación de QR en base64
│   │   ├── pedidos/       # Pedido, DetallePedido, flujo de estados
│   │   └── pagos/         # Pago (registro, anulación, eliminación)
│   ├── manage.py
│   └── requirements.txt
└── frontend/
    └── src/
        ├── context/       # AuthContext (sesión JWT), CartContext (carrito de la carta)
        ├── services/      # api.js (Axios + interceptores) y un servicio por módulo
        ├── routes/        # AppRouter y ProtectedRoute
        ├── layouts/       # AdminLayout (sidebar filtrado por rol), CartaLayout
        └── pages/         # Login, carta/CartaDigital, admin/* (Dashboard, Usuarios, ...)
```

## Roles y permisos

Los permisos se implementan en `backend/config/permissions.py` comparando el nombre del rol, por lo que los roles deben existir con estos nombres exactos (sin tilde): `Administrador`, `Garzon`, `Cocina`.

| Rol | Acceso en el panel |
|-----|--------------------|
| Administrador | Todos los módulos: usuarios, categorías, productos, mesas, pedidos y pagos |
| Garzon | Pedidos (envía a cocina y marca como entregado), mesas y pagos (registrar y anular) |
| Cocina | Pedidos (empieza los pendientes y marca como listos los que están en preparación) |
| Cliente | Carta digital pública, sin autenticación |

## Flujo operativo

1. El cliente escanea el QR de la mesa → `/carta?mesa=<id>`.
2. Envía su pedido, con indicaciones opcionales por producto para la cocina (“sin cebolla”, máximo 140 caracteres) → se crea en estado `pendiente` y la mesa pasa a `ocupada`.
3. Estados del pedido: `pendiente` → `en_preparacion` → `listo` → `entregado`, siempre en ese orden. Preparar lo hacen Cocina o Garzon; marcar listo, Cocina; entregar, Garzon (el Administrador puede todos). Cada cambio queda en el historial del pedido con su hora y quién lo hizo. Al quedar entregado el último pedido activo de la mesa, esta vuelve a `libre`.
4. En cualquier momento el cliente puede **llamar al garzón** o **pedir la cuenta** desde la carta. El aviso aparece arriba de cualquier pantalla del panel para Garzon y Administrador, que lo marcan como atendido. Si la mesa toca el botón varias veces, el aviso no se duplica.
5. El garzón registra el pago de un pedido entregado (efectivo, débito, crédito o transferencia). El monto debe coincidir con el total del pedido.
6. Un pago puede anularse y el pedido vuelve a quedar disponible para cobrarse; el pago anulado se conserva como historial. Cada pedido tiene a lo más un pago vigente. Solo los pagos anulados pueden eliminarse, y solo por el Administrador.

## API REST

Todas las rutas cuelgan de `http://localhost:8000/api/`. Las marcadas como públicas no requieren token; el resto exige `Authorization: Bearer <access>`.

| Recurso | Método y ruta | Permiso |
|---------|---------------|---------|
| Autenticación | `POST auth/login/` | Público |
| | `POST auth/token/refresh/` | Público (entrega un access nuevo y rota el refresh) |
| | `POST auth/logout/` | Autenticado |
| | `GET auth/perfil/` | Autenticado |
| Usuarios | `GET, POST auth/usuarios/` | Administrador |
| | `PATCH auth/usuarios/<id>/estado/` | Administrador |
| | `PATCH auth/usuarios/<id>/editar/` | Administrador |
| | `GET auth/roles/` | Administrador |
| Categorías | `GET categorias/` | Público (solo activas) / autenticado (todas) |
| | `POST categorias/` | Administrador |
| | `GET, PUT, DELETE categorias/<id>/` | Administrador (DELETE = desactivación lógica) |
| | `PATCH categorias/<id>/estado/` | Administrador |
| Productos | `GET productos/?categoria=&disponible=` | Público (solo disponibles) / autenticado |
| | `POST productos/` | Administrador (multipart, admite imagen) |
| | `GET productos/<id>/` | Público |
| | `PUT, DELETE productos/<id>/` | Administrador (DELETE = desactivación lógica) |
| Mesas | `GET mesas/`, `GET mesas/<id>/` | Público |
| | `POST mesas/`, `PUT, DELETE mesas/<id>/` | Administrador (POST genera el QR) |
| | `PATCH mesas/<id>/estado/` | Administrador o Garzon |
| | `POST mesas/<id>/qr/` | Administrador (regenera el QR) |
| | `POST mesas/<id>/solicitudes/` | Público (cuerpo `{"tipo": "garzon"}` o `{"tipo": "cuenta"}`) |
| Solicitudes | `GET solicitudes/?estado=` | Administrador o Garzon |
| | `PATCH solicitudes/<id>/atender/` | Administrador o Garzon |
| Pedidos | `POST pedidos/` | Público (carta digital) |
| | `GET pedidos/?estado=&mesa=` | Cualquier rol |
| | `GET pedidos/<id>/` | Administrador o Cocina |
| | `DELETE pedidos/<id>/` | Administrador (solo pendientes) |
| | `PATCH pedidos/<id>/estado/` | Según el paso: preparar (Admin, Garzon, Cocina), listo (Admin, Cocina), entregar (Admin, Garzon) |
| Pagos | `GET, POST pagos/?estado=` | Administrador o Garzon |
| | `GET pagos/<id>/` | Cualquier rol |
| | `PATCH pagos/<id>/anular/` | Administrador o Garzon |
| | `DELETE pagos/<id>/eliminar/` | Administrador (solo anulados) |

## Instalación y ejecución local

### Requisitos

- Python 3.14
- Node.js 24 y npm
- MySQL 8 en ejecución

### 1. Base de datos

```sql
CREATE DATABASE pizzeria400 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Backend

```bash
python -m venv venv
source venv/Scripts/activate      # Windows (Git Bash). En Linux/macOS: source venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

Completa `backend/.env` con la `SECRET_KEY` y las credenciales de MySQL. Luego, desde `backend/`:

```bash
python manage.py migrate
python manage.py shell -c "from apps.usuarios.models import Rol; [Rol.objects.get_or_create(nombre=n) for n in ('Administrador', 'Garzon', 'Cocina')]"
python manage.py createsuperuser
python manage.py shell -c "from apps.usuarios.models import Usuario, Rol; Usuario.objects.filter(is_superuser=True).update(rol=Rol.objects.get(nombre='Administrador'))"
python manage.py runserver
```

El último comando `shell` asigna el rol `Administrador` al superusuario; sin rol asignado no puede acceder al panel. La API queda disponible en `http://localhost:8000/api/`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

El panel queda en `http://localhost:5173/login` y la carta digital en `http://localhost:5173/carta?mesa=<id>`. La URL base de la API está definida en `frontend/src/services/api.js`.

## Pruebas

### Automatizadas

Son 113 pruebas de la API, en un archivo `tests.py` por app (usuarios, productos, mesas, pedidos y pagos). Además, `config/tests.py` verifica la matriz de permisos de cada rol en todas las rutas. Desde `backend/`:

```bash
python manage.py test -v 2
```

Django crea una base de pruebas temporal (`test_<DB_NAME>`) y la borra al terminar, así que el usuario de MySQL necesita permiso para crear bases de datos. Para correrlas sin MySQL, se puede usar un archivo de configuración que herede de `config.settings` y defina una base SQLite en memoria (`--settings <módulo>`).

### Funcionales y no funcionales

El catálogo de casos para ejecución manual, con 29 casos funcionales y 10 no funcionales, los datos de prueba y la cobertura de requerimientos, está en [`docs/qa/casos-de-prueba.md`](docs/qa/casos-de-prueba.md).

## Variables de entorno (backend)

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave secreta de Django |
| `DEBUG` | `True` en desarrollo (también habilita el servicio de `/media/`) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a MySQL |
| `FRONTEND_URL` | URL base del frontend usada al generar los códigos QR de las mesas |

## Metodología

El proyecto se gestionó con la Guía PMBOK 6 como marco de planificación y control: fases, hitos, riesgos, costos y calidad. El software se desarrolló con **Kanban**, como un flujo continuo de tareas con un máximo de dos en curso, registrado en el [tablero del proyecto](https://github.com/users/Javier-apv-dev/projects/1). Cada tarea terminada corresponde a un commit de este repositorio.

El sistema se entregó en cuatro etapas:

| Entrega | Fecha | Contenido |
|---------|-------|-----------|
| 1. Núcleo | 10-abr-2026 | Modelo de datos, API, carta digital con QR y panel administrativo |
| 2. Control de acceso | 10 al 16-abr-2026 | Permisos por rol, gestión de usuarios y trazabilidad de pagos |
| 3. Revisión y corrección | 12 al 15-oct-2026 | Renovación del token, README y corrección de 7 defectos detectados en un diagnóstico |
| 4. Mejoras | 15-oct-2026 | Indicaciones del cliente, historial de estados, avisos de mesa y mejoras de uso |

La planificación inicial contemplaba un Scrum adaptado con sprints. Como el trabajo real fue un flujo de tareas de distinto tamaño, en octubre de 2026 se adoptó Kanban y se formalizó con el tablero.
