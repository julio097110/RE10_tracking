"""
telegram_bot.py
----------------
Envía mensajes de aviso al bot de Telegram cuando se detecta un
retraso o cancelación que cumple el criterio de reclamación.

El token del bot y el chat_id NUNCA se escriben aquí en el código.
Se leen de variables de entorno, para no dejarlos guardados en
texto plano en un fichero que subimos a un repositorio público.
"""

import os

import requests

import utils

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def enviar_alerta(mensaje: str) -> bool:
    """
    Envía un mensaje de texto al chat configurado.
    Devuelve True si se ha enviado correctamente, False si algo ha fallado
    (por ejemplo, si faltan las variables de entorno).
    """
    if not TOKEN or not CHAT_ID:
        print(
            "Aviso: faltan TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID como "
            "variables de entorno. No se puede enviar el mensaje."
        )
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    respuesta = requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": mensaje},
        timeout=15,
    )

    if respuesta.status_code != 200:
        print(f"Error al enviar el mensaje a Telegram: {respuesta.status_code} {respuesta.text}")
        return False

    return True


def formatear_mensaje(registro: dict) -> str:
    """
    Construye el texto del aviso a partir de un registro de la tabla
    'retrasos' (un diccionario, tal y como lo devuelve db.obtener_retrasos()).
    """
    if registro["cancelado"]:
        return (
            f"🚫 RE10 CANCELADO\n"
            f"Sentido: {registro['sentido']}\n"
            f"Fecha: {registro['fecha_viaje']}\n"
            f"Hora prevista: {utils.formatear_hora(registro['hora_prevista_llegada'])}"
        )

    return (
        f"⏰ RE10 con retraso reclamable\n"
        f"Sentido: {registro['sentido']}\n"
        f"Fecha: {registro['fecha_viaje']}\n"
        f"Retraso: {registro['retraso_minutos']} min\n"
        f"Hora prevista: {utils.formatear_hora(registro['hora_prevista_llegada'])}\n"
        f"Hora real: {utils.formatear_hora(registro['hora_real_llegada'])}"
    )


if __name__ == "__main__":
    # Prueba rápida y manual: manda un mensaje de prueba al chat.
    # Ejecuta esto en tu terminal tras definir las variables de entorno
    # (ver instrucciones más abajo).
    exito = enviar_alerta("✅ Mensaje de prueba desde re10-delay-tracker")
    print("Mensaje enviado correctamente" if exito else "No se pudo enviar el mensaje")
