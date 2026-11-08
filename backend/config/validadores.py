MAX_ID = 2 ** 63 - 1


def es_id_valido(valor):
    """Indica si un filtro de la URL se puede comparar con una clave: un entero que cabe en BIGINT.

    Se revisa el largo antes de convertir, porque int() rechaza los textos de miles de dígitos.
    """
    return valor.isdecimal() and len(valor) <= 19 and int(valor) <= MAX_ID
