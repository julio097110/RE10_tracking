"""
entur_client.py
----------------
Consulta la JourneyPlanner API de Entur y devuelve las llegadas
previstas/reales del RE10 en Oslo S y Tangen.
"""

import time

import requests

URL_API = "https://api.entur.io/journey-planner/v3/graphql"

# Entur exige identificarte con este header (no hace falta cuenta ni API key,
# solo un texto con el formato "empresa-aplicacion").
# Añadimos también un User-Agent explícito: algunos servidores tratan de
# forma más estricta (o incluso bloquean) las peticiones que llegan con el
# User-Agent por defecto de la librería requests.
CABECERAS = {
    "ET-Client-Name": "julio-re10delaytracker",
    "User-Agent": "re10-delay-tracker/1.0 (proyecto personal)",
}

OSLO_S = "NSR:StopPlace:59872"
TANGEN = "NSR:StopPlace:60530"

LINEA_RE10 = "RE10"

QUERY = """
query($stopId: String!, $numDep: Int!, $timeRange: Int!) {
  stopPlace(id: $stopId) {
    id
    name
    estimatedCalls(
      numberOfDepartures: $numDep
      timeRange: $timeRange
      arrivalDeparture: arrivals
      includeCancelledTrips: true
    ) {
      realtime
      aimedArrivalTime
      expectedArrivalTime
      actualArrivalTime
      cancellation
      destinationDisplay {
        frontText
      }
      serviceJourney {
        id
        line {
          publicCode
          name
        }
      }
    }
  }
}
"""


def obtener_llegadas(stop_place_id: str, num_llegadas: int = 20, ventana_horas: int = 20) -> list[dict]:
    """
    Pide a Entur las próximas llegadas a una estación (todas las líneas),
    y devuelve solo las que son del RE10.

    ventana_horas: cuántas horas hacia delante mirar (Entur lo pide en segundos).
    """
    variables = {
        "stopId": stop_place_id,
        "numDep": num_llegadas,
        "timeRange": ventana_horas * 3600,
    }

    # Reintentamos hasta 3 veces si hay un fallo de conexión (no si Entur
    # responde con un error "de verdad", como un 400 por una consulta mal
    # formada -- eso no se arregla reintentando).
    intentos = 3
    for intento in range(1, intentos + 1):
        try:
            respuesta = requests.post(
                URL_API,
                json={"query": QUERY, "variables": variables},
                headers=CABECERAS,
                timeout=15,
            )
            respuesta.raise_for_status()  # error si Entur responde con código de fallo (4xx/5xx)
            break  # si ha ido bien, salimos del bucle de reintentos
        except requests.exceptions.ConnectionError as error:
            if intento == intentos:
                raise  # ya hemos agotado los reintentos, dejamos que falle de verdad
            print(f"Fallo de conexión (intento {intento}/{intentos}): {error}. Reintentando en 5s...")
            time.sleep(5)

    datos = respuesta.json()
    llamadas = datos["data"]["stopPlace"]["estimatedCalls"]

    # Filtramos aquí, en Python, en vez de pedirle a Entur que filtre por
    # línea directamente: es más simple y no depende de conocer el ID
    # interno exacto de la línea RE10 en el sistema de Entur.
    llegadas_re10 = [
        llamada for llamada in llamadas
        if llamada["serviceJourney"]["line"]["publicCode"] == LINEA_RE10
    ]
    return llegadas_re10


if __name__ == "__main__":
    # Prueba rápida: mostrar las próximas llegadas del RE10 a Oslo S.
    # OJO: esto solo funcionará cuando lo ejecutes en un entorno con
    # acceso a internet a api.entur.io (por ejemplo, dentro de GitHub
    # Actions) -- desde aquí no lo puedo comprobar en vivo.
    llegadas = obtener_llegadas(OSLO_S)
    print(f"Encontradas {len(llegadas)} llegadas del RE10 a Oslo S:")
    for llegada in llegadas:
        print(llegada)
