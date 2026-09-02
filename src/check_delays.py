"""
check_delays.py
----------------
Junta entur_client.py y db.py: consulta las llegadas del RE10, decide
si alguna cumple el criterio de reclamación (retraso >= 25 min o
cancelación), y la guarda en la base de datos si es así.
"""

from datetime import datetime, timezone

import db
import entur_client as entur
import telegram_bot

UMBRAL_MINUTOS = 25

# Configuración de los dos sentidos que vigilamos. Para cada uno:
# - estacion_id / estacion_nombre: la estación DESTINO donde medimos la llegada.
# - destino_esperado: el texto que Entur usa en destinationDisplay para
#   los trenes que van en ese sentido (el destino FINAL de la línea, no
#   la parada donde medimos).
SENTIDOS = [
    {
        "sentido": "Oslo S -> Tangen",
        "estacion_origen": "Oslo S",
        "estacion_destino": "Tangen",
        "estacion_destino_id": entur.TANGEN,
        "destino_esperado": "Lillehammer",
    },
    {
        "sentido": "Tangen -> Oslo S",
        "estacion_origen": "Tangen",
        "estacion_destino": "Oslo S",
        "estacion_destino_id": entur.OSLO_S,
        "destino_esperado": "Drammen",
    },
]


def _parsear_hora(texto_iso: str | None) -> datetime | None:
    """Convierte un string ISO de Entur (con zona horaria) a un datetime de Python."""
    if texto_iso is None:
        return None
    return datetime.fromisoformat(texto_iso)


def evaluar_llegada(llegada: dict) -> dict | None:
    """
    Analiza una llegada (tal y como la devuelve entur_client) y decide
    si cumple el criterio de reclamación.

    Devuelve None si no cumple, o un diccionario con los datos ya
    calculados (retraso en minutos, tipo de incidencia...) si sí cumple.
    """
    if llegada["cancellation"]:
        return {
            "tipo_incidencia": "cancelado",
            "hora_real_llegada": None,
            "retraso_minutos": None,
            "cancelado": True,
        }

    hora_prevista = _parsear_hora(llegada["aimedArrivalTime"])

    # Preferimos actualArrivalTime (el dato ya confirmado, el tren ha
    # pasado por la estación) y si todavía no existe, usamos
    # expectedArrivalTime (la predicción) como respaldo.
    hora_real = _parsear_hora(llegada["actualArrivalTime"]) or _parsear_hora(
        llegada["expectedArrivalTime"]
    )

    if hora_real is None or hora_prevista is None:
        return None  # no hay suficiente información todavía

    retraso_minutos = int((hora_real - hora_prevista).total_seconds() // 60)

    if retraso_minutos < UMBRAL_MINUTOS:
        return None  # llega a tiempo (o con un retraso que no cuenta)

    return {
        "tipo_incidencia": "retraso",
        "hora_real_llegada": hora_real.isoformat(),
        "retraso_minutos": retraso_minutos,
        "cancelado": False,
    }


def revisar_sentido(config_sentido: dict) -> list[dict]:
    """
    Consulta Entur para un sentido concreto, evalúa cada llegada del
    RE10 con el destino esperado, y guarda en la base de datos las que
    cumplen el criterio. Devuelve la lista de las que se han guardado
    (para poder avisar por Telegram después).
    """
    llegadas = entur.obtener_llegadas(config_sentido["estacion_destino_id"])

    # Nos quedamos solo con los trenes que van en el sentido que nos
    # interesa (lo distinguimos por el destino final del tren).
    llegadas_del_sentido = [
        llegada for llegada in llegadas
        if llegada["destinationDisplay"]["frontText"] == config_sentido["destino_esperado"]
    ]

    guardados = []
    for llegada in llegadas_del_sentido:
        resultado = evaluar_llegada(llegada)
        if resultado is None:
            continue

        nuevo_id = db.insertar_retraso(
            fecha_viaje=llegada["aimedArrivalTime"][:10],  # "2026-09-01T15:26:00+02:00" -> "2026-09-01"
            linea=entur.LINEA_RE10,
            sentido=config_sentido["sentido"],
            estacion_origen=config_sentido["estacion_origen"],
            estacion_destino=config_sentido["estacion_destino"],
            hora_prevista_llegada=llegada["aimedArrivalTime"],
            hora_real_llegada=resultado["hora_real_llegada"],
            retraso_minutos=resultado["retraso_minutos"],
            cancelado=resultado["cancelado"],
            tipo_incidencia=resultado["tipo_incidencia"],
            detectado_en=datetime.now(timezone.utc).isoformat(),
            service_journey_id=llegada["serviceJourney"]["id"],
        )

        if nuevo_id is not None:
            registro = {
                "id": nuevo_id,
                "sentido": config_sentido["sentido"],
                "fecha_viaje": llegada["aimedArrivalTime"][:10],
                "hora_prevista_llegada": llegada["aimedArrivalTime"],
                "hora_real_llegada": resultado["hora_real_llegada"],
                "retraso_minutos": resultado["retraso_minutos"],
                "cancelado": resultado["cancelado"],
            }

            mensaje = telegram_bot.formatear_mensaje(registro)
            if telegram_bot.enviar_alerta(mensaje):
                db.marcar_avisado(nuevo_id)

            guardados.append(registro)

    return guardados


def revisar_todos_los_sentidos() -> list[dict]:
    """Revisa los dos sentidos y devuelve todos los nuevos registros guardados."""
    todos_los_guardados = []
    for config_sentido in SENTIDOS:
        guardados = revisar_sentido(config_sentido)
        todos_los_guardados.extend(guardados)
    return todos_los_guardados


if __name__ == "__main__":
    nuevos = revisar_todos_los_sentidos()
    if nuevos:
        print(f"Se han detectado y guardado {len(nuevos)} nuevas incidencias:")
        for n in nuevos:
            print(n)
    else:
        print("No hay nuevas incidencias que cumplan el criterio en esta revisión.")

    borrados = db.borrar_antiguos(meses=3)
    if borrados:
        print(f"Limpieza: se han borrado {borrados} registros con más de 3 meses de antigüedad.")
