"""
utils.py
--------
Funciones pequeñas compartidas entre varios módulos.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

ZONA_OSLO = ZoneInfo("Europe/Oslo")


def formatear_hora(texto_iso: str | None) -> str:
    """
    Convierte un string ISO (como los que da Entur, con su propio
    desfase horario) a un texto legible en hora de Oslo, con formato
    dd/mm/aaaa hh:mm. Devuelve "-" si no hay hora (por ejemplo, un
    tren cancelado que nunca llegó).
    """
    if texto_iso is None:
        return "-"

    momento = datetime.fromisoformat(texto_iso)
    momento_oslo = momento.astimezone(ZONA_OSLO)
    return momento_oslo.strftime("%d/%m/%Y %H:%M")
