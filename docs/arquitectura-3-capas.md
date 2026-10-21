# Arquitectura en tres capas

El sistema sigue una arquitectura cliente-servidor en tres capas. Cada capa tiene una responsabilidad y se comunica solo con la capa vecina.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "Arial", "fontSize": "16px", "lineColor": "#555555", "primaryTextColor": "#222222", "edgeLabelBackground": "#FFFFFF"}, "flowchart": {"curve": "basis", "padding": 13, "nodeSpacing": 14, "rankSpacing": 42, "wrappingWidth": 260}}}%%
flowchart TB
    cliente(["Cliente<br/>teléfono, sin cuenta"])
    personal(["Personal del local<br/>Administrador · Garzón · Cocina"])

    subgraph presentacion["Capa de presentación · React 19 (SPA)"]
        carta["Carta digital pública<br/>/carta?mesa=id<br/>carrito, indicaciones y avisos"]
        panel["Panel administrativo<br/>rutas protegidas por rol<br/>consulta cada 10 s"]
    end

    subgraph negocio["Capa de negocio · Django 6 y DRF 3.17"]
        seguridad["Seguridad de la API<br/>token JWT de 8 h, renovable 24 h<br/>permisos por rol"]
        usuarios["usuarios<br/>cuentas, roles<br/>y sesión"]
        productos["productos<br/>categorías,<br/>productos e imágenes"]
        mesas["mesas<br/>mesas, QR<br/>y avisos de mesa"]
        pedidos["pedidos<br/>precio en el servidor<br/>estados por rol<br/>e historial"]
        pagos["pagos<br/>un pago vigente<br/>por pedido<br/>y anulación"]
    end

    subgraph datos["Capa de datos"]
        orm["ORM de Django<br/>modelos y migraciones"]
        bd[("MySQL 8.4 · utf8mb4<br/>10 entidades")]
        media[["Imágenes de productos<br/>backend/media"]]
    end

    cliente -->|escanea el QR de la mesa| carta
    personal -->|inicia sesión| panel
    carta <==>|"HTTP + JSON<br/>rutas públicas"| seguridad
    panel <==>|"HTTP + JSON<br/>con token JWT"| seguridad
    seguridad --> usuarios & productos & mesas & pedidos & pagos
    usuarios & productos & mesas & pedidos & pagos --> orm
    orm --> bd
    orm -->|archivos| media

    classDef actor fill:#FFFFFF,stroke:#1F2A37,stroke-width:2px,color:#222222
    classDef pres fill:#F9E4E6,stroke:#B3202A,stroke-width:1.5px,color:#222222
    classDef neg fill:#E3E7EE,stroke:#1F2A37,stroke-width:1.5px,color:#222222
    classDef dat fill:#EEEEEE,stroke:#6B7280,stroke-width:1.5px,color:#222222
    class cliente,personal actor
    class carta,panel pres
    class seguridad,usuarios,productos,mesas,pedidos,pagos neg
    class orm,bd,media dat
    style presentacion fill:#FFFFFF,stroke:#B3202A,stroke-width:2px,color:#B3202A
    style negocio fill:#FFFFFF,stroke:#1F2A37,stroke-width:2px,color:#1F2A37
    style datos fill:#FFFFFF,stroke:#6B7280,stroke-width:2px,color:#444444
```

La fuente del diagrama, con sus estilos, es [`arquitectura-3-capas.mmd`](arquitectura-3-capas.mmd). Hay copias exportadas en [`arquitectura-3-capas.svg`](arquitectura-3-capas.svg) y [`arquitectura-3-capas.png`](arquitectura-3-capas.png).

## Capas

**Presentación** (`frontend/`). Es una aplicación de una sola página (SPA) en React 19, construida con Vite 8, con dos interfaces:
- La **carta digital** es pública: el cliente entra por el código QR de su mesa (`/carta?mesa=<id>`), arma su pedido con indicaciones y puede llamar al garzón o pedir la cuenta.
- El **panel administrativo** tiene rutas protegidas según el rol (`routes/ProtectedRoute.jsx`). Consulta los pedidos y los avisos de mesa cada 10 segundos; no hay notificaciones en tiempo real.

Las dos usan el mismo cliente HTTP (`services/api.js`, con Axios), que adjunta el token de sesión a cada petición del panel y lo renueva cuando vence.

**Negocio** (`backend/`). Es una API REST en Django 6 y Django REST Framework 3.17.
- **Seguridad.** Toda petición pasa primero por la autenticación con JSON Web Token (`djangorestframework-simplejwt`: acceso de 8 horas y refresco de 24, con rotación y lista negra) y por los permisos por rol de `config/permissions.py`.
- **Cinco aplicaciones.** `backend/apps/` tiene usuarios, productos, mesas, pedidos y pagos. Cada una trae sus modelos, serializadores, vistas y rutas.
- **Reglas del negocio en el servidor:**
  - el precio de cada pedido se calcula en el backend;
  - los estados del pedido avanzan en orden y según el rol (`TRANSICIONES` en `apps/pedidos/views.py`), y cada cambio queda en el historial;
  - cada pedido tiene a lo más un pago vigente: el cobro corre en una transacción que bloquea el pedido.

**Datos.** El ORM de Django traduce los modelos a tablas de MySQL 8.4 (`utf8mb4`) y versiona el esquema con migraciones. Las imágenes de los productos se guardan como archivos en `backend/media/`. El código QR de cada mesa se guarda en la base, como imagen PNG en base64.

## Recorrido de una petición

1. El navegador envía una petición HTTP con JSON. En el panel lleva el encabezado `Authorization: Bearer <token>`.
2. Django revisa el origen (CORS), autentica el token y verifica el permiso del rol para esa ruta.
3. La vista valida los datos con su serializador y aplica las reglas del negocio.
4. El modelo lee o escribe en MySQL mediante el ORM.
5. La respuesta vuelve en JSON.

Las rutas públicas no requieren token. Sirven para iniciar y renovar la sesión, leer las categorías, los productos y las mesas, crear pedidos y enviar avisos de mesa. Las 40 combinaciones de ruta y método, con el rol que puede usar cada una, están en la prueba `MatrizDePermisosTests` (`backend/config/tests.py`).
