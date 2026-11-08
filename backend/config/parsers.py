from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser


class JSONObjetoParser(JSONParser):
    """Rechaza con 400 un cuerpo JSON que no sea un objeto (lista, texto, número o null).

    Todas las rutas de la API reciben un objeto, y las vistas leen request.data.get(...).
    """

    def parse(self, stream, media_type=None, parser_context=None):
        datos = super().parse(stream, media_type, parser_context)
        if not isinstance(datos, dict):
            raise ParseError('El cuerpo de la petición debe ser un objeto JSON')
        return datos
