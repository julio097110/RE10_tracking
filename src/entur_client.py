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


def _consultar_graphql(query: str, variables: dict) -> dict:
    """
    Hace una petición POST a la API de Entur con reintentos ante fallos
    de conexión, y devuelve el JSON de la respuesta ya parseado.
    Se usa tanto para consultar llegadas a una estación como para
    consultar el itinerario completo de un servicio concreto.
    """
    intentos = 3
    for intento in range(1, intentos + 1):
        try:
            respuesta = requests.post(
                URL_API,
                json={"query": query, "variables": variables},
                headers=CABECERAS,
                timeout=15,
            )
            respuesta.raise_for_status()
            return respuesta.json()
        except requests.exceptions.ConnectionError as error:
            if intento == intentos:
                raise
            print(f"Fallo de conexión (intento {intento}/{intentos}): {error}. Reintentando en 5s...")
            time.sleep(5)


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

    datos = _consultar_graphql(QUERY, variables)
    llamadas = datos["data"]["stopPlace"]["estimatedCalls"]

    # Filtramos aquí, en Python, en vez de pedirle a Entur que filtre por
    # línea directamente: es más simple y no depende de conocer el ID
    # interno exacto de la línea RE10 en el sistema de Entur.
    llegadas_re10 = [
        llamada for llamada in llamadas
        if llamada["serviceJourney"]["line"]["publicCode"] == LINEA_RE10
    ]
    return llegadas_re10


QUERY_ITINERARIO = """
query($id: String!) {
  serviceJourney(id: $id) {
    id
    estimatedCalls {
      quay {
        name
      }
      aimedArrivalTime
      expectedArrivalTime
      actualArrivalTime
      cancellation
    }
  }
}
"""


def obtener_itinerario(service_journey_id: str) -> list[dict]:
    """
    Consulta el itinerario completo de un servicio concreto: todas las
    paradas que hace, en orden, con su hora prevista, hora real
    (o estimada si aún no hay real) y si esa parada en concreto se
    canceló. Se usa tanto para trenes cancelados como para trenes con
    retraso, para poder mostrar el detalle parada a parada.

    Devuelve una lista vacía si Entur ya no tiene datos de ese servicio.
    """
    datos = _consultar_graphql(QUERY_ITINERARIO, {"id": service_journey_id})
    servicio = datos.get("data", {}).get("serviceJourney")

    if servicio is None:
        return []

    paradas = []
    for llamada in servicio["estimatedCalls"]:
        paradas.append({
            "estacion": llamada["quay"]["name"],
            "hora_prevista": llamada["aimedArrivalTime"],
            "hora_real": llamada["actualArrivalTime"] or llamada["expectedArrivalTime"],
            "cancelado": llamada["cancellation"],
        })
    return paradas


if __name__ == "__main__":
    # Prueba rápida: mostrar las próximas llegadas del RE10 a Oslo S.
    # OJO: esto solo funcionará cuando lo ejecutes en un entorno con
    # acceso a internet a api.entur.io (por ejemplo, dentro de GitHub
    # Actions) -- desde aquí no lo puedo comprobar en vivo.
    llegadas = obtener_llegadas(OSLO_S)
    print(f"Encontradas {len(llegadas)} llegadas del RE10 a Oslo S:")
    for llegada in llegadas:
        print(llegada)
