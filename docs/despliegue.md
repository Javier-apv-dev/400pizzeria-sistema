# Despliegue: dónde se ejecuta el sistema

El sistema **no está desplegado en un servidor de producción**. Se ejecuta en el notebook del autor, con dos configuraciones de Django: una de desarrollo y una de prueba (QA).

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "Arial", "fontSize": "16px", "lineColor": "#555555", "primaryTextColor": "#222222", "edgeLabelBackground": "#FFFFFF"}, "flowchart": {"curve": "basis", "padding": 13, "nodeSpacing": 24, "rankSpacing": 46, "wrappingWidth": 260}}}%%
flowchart TB
    subgraph equipo["Notebook del autor · Windows 11"]
        direction TB
        navegador["Navegador web (Chrome o Edge)<br/>carta digital y panel"]

        subgraph nodo["Node.js 24"]
            vite["Vite 8 · servidor de desarrollo<br/>localhost:5173<br/>entrega la SPA de React 19"]
        end

        subgraph python["Python 3.14 · venv"]
            django["Django 6 · runserver<br/>localhost:8000<br/>API /api/ e imágenes /media/"]
        end

        mysql[("MySQL 8.4<br/>localhost:3306<br/>base pizzeria400")]
        sqlite[("SQLite (QA)<br/>%TEMP%/400pizzeria-qa")]
    end

    github["GitHub<br/>repositorio, issues<br/>y tablero Kanban"]

    navegador -->|"descarga la aplicación"| vite
    navegador ==>|"llamadas a la API<br/>HTTP + JSON"| django
    django -->|"desarrollo<br/>config.settings"| mysql
    django -.->|"pruebas<br/>config.settings_qa"| sqlite
    equipo -.->|git push| github

    classDef nodoSw fill:#E3E7EE,stroke:#1F2A37,stroke-width:1.5px,color:#222222
    classDef cliente fill:#F9E4E6,stroke:#B3202A,stroke-width:1.5px,color:#222222
    classDef datos fill:#EEEEEE,stroke:#6B7280,stroke-width:1.5px,color:#222222
    classDef externo fill:#FFFFFF,stroke:#6B7280,stroke-width:1.5px,stroke-dasharray:5 4,color:#444444
    class vite,django nodoSw
    class navegador cliente
    class mysql,sqlite datos
    class github externo
    style equipo fill:#FFFFFF,stroke:#1F2A37,stroke-width:2px,color:#1F2A37
    style nodo fill:#F7F8FA,stroke:#6B7280,stroke-width:1px,color:#444444
    style python fill:#F7F8FA,stroke:#6B7280,stroke-width:1px,color:#444444
```

La fuente del diagrama, con sus estilos, es [`despliegue.mmd`](despliegue.mmd). Hay copias exportadas en [`despliegue.svg`](despliegue.svg) y [`despliegue.png`](despliegue.png).

## Procesos y configuraciones

| Proceso | Comando | Dirección |
|---|---|---|
| Frontend (desarrollo) | `npm run dev` en `frontend/` | `http://localhost:5173` |
| Backend | `python manage.py runserver` en `backend/` | `http://localhost:8000` |
| Base de datos de desarrollo | Servicio de MySQL 8.4 | `localhost:3306`, base `pizzeria400` |

- **Desarrollo:** `config.settings` lee las credenciales de MySQL desde `backend/.env` (ver `.env.example`).
- **Prueba (QA):** `config.settings_qa` usa SQLite y una carpeta de imágenes temporal en `%TEMP%/400pizzeria-qa`, para no tocar la base de desarrollo. Con esa configuración existen los comandos `cargar_datos_qa` y `medir_tiempos`. Las pruebas automatizadas usan una base SQLite en memoria.

El navegador descarga la aplicación desde Vite y después llama directamente a la API de Django. Las imágenes de los productos se sirven desde `/media/` solo con `DEBUG` activado.

## Limitación: hoy solo funciona en el mismo equipo

Todas las direcciones están fijas en `localhost`:
- `frontend/src/services/api.js` llama a la API en `http://localhost:8000/api`;
- `backend/config/settings.py` solo acepta `localhost` y `127.0.0.1` en `ALLOWED_HOSTS`, y solo `http://localhost:5173` en `CORS_ALLOWED_ORIGINS`;
- el servidor de Vite escucha solo en `localhost`.

Por eso, un teléfono que escanea el código QR de una mesa no puede abrir la carta ni llamar a la API: la carta y el panel funcionan solo en el navegador del mismo notebook. Para usar el sistema desde la red del local o desde un servidor, hay que hacer configurables esas direcciones con variables de entorno y, en un servidor, reemplazar `runserver` y Vite por un servidor de aplicaciones y los archivos compilados del frontend (`npm run build`).
