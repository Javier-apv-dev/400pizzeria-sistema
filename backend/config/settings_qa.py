"""Configuración del entorno de prueba (QA): SQLite y media en una carpeta temporal.

Nunca toca la base MySQL ni backend/media. Los datos quedan en %TEMP%/400pizzeria-qa,
o en la carpeta que indique la variable PIZZERIA_QA_DIR.

Uso, desde backend/:
    python manage.py cargar_datos_qa --settings=config.settings_qa
    python manage.py runserver --settings=config.settings_qa
    python manage.py medir_tiempos --settings=config.settings_qa
"""
import os
import tempfile
from pathlib import Path

from django.core.management.utils import get_random_secret_key

from config.settings import *  # noqa: F401,F403
from config.settings import INSTALLED_APPS, SECRET_KEY

QA_DIR = Path(os.getenv('PIZZERIA_QA_DIR', Path(tempfile.gettempdir()) / '400pizzeria-qa'))
QA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': QA_DIR / 'qa.sqlite3',
        # Espera a que se libere la base si llegan escrituras simultáneas (prueba de carga)
        'OPTIONS': {'timeout': 20},
    }
}
MEDIA_ROOT = QA_DIR / 'media'

# DEBUG sirve las imágenes de /media/ con runserver; testserver lo usa APIClient al cargar datos
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
SECRET_KEY = SECRET_KEY or get_random_secret_key()

# Los comandos de QA (cargar_datos_qa, medir_tiempos) solo existen con esta configuración
INSTALLED_APPS = INSTALLED_APPS + ['qa']
