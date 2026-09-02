"""
db.py
-----
Funciones para guardar y leer los retrasos/cancelaciones del RE10
en una base de datos SQLite.

Este módulo no sabe nada de la API de Entur ni de Telegram: solo
sabe "guardar filas" y "leer filas". Esa separación es a propósito:
así podemos probar esta parte sola, sin depender de internet.
"""

import sqlite3
from pathlib import Path

# Path(__file__) es la ruta de este propio fichero (src/db.py).
# .parent sube una carpeta (a src/), y otro .parent sube otra (a la raíz del proyecto).
# Así, sea cual sea la carpeta desde la que ejecutes el script, siempre
# encuentra data/retrasos.db en el mismo sitio relativo al proyecto.
def _encontrar_raiz_proyecto() -> Path:
    """
    Busca la carpeta raíz del proyecto subiendo desde este archivo hasta
    encontrar la que contiene 'requirements.txt'.

    Esto hace que el código funcione igual tanto si tienes los .py sueltos
    en una sola carpeta (como en tu ordenador) como si están organizados
    en subcarpetas, por ejemplo con este archivo dentro de src/ (como en
    GitHub) -- en ambos casos, requirements.txt está siempre en la raíz.
    """
    carpeta = Path(__file__).parent
    while carpeta != carpeta.parent:  # hasta llegar a la raíz del disco
        if (carpeta / "requirements.txt").exists():
            return carpeta
        carpeta = carpeta.parent
    return Path(__file__).parent  # último recurso, si no la encuentra


RUTA_BD = _encontrar_raiz_proyecto() / "data" / "retrasos.db"

# Esto es SQL, no Python: es el lenguaje para hablar con la base de datos.
# "CREATE TABLE IF NOT EXISTS" significa "créala solo si no existe ya",
# así podemos llamar a esta función cada vez que arranca el script sin
# que se queje de que la tabla ya está creada.
SQL_CREAR_TABLA = """
CREATE TABLE IF NOT EXISTS retrasos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_viaje TEXT NOT NULL,
    linea TEXT NOT NULL,
    sentido TEXT NOT NULL,
    estacion_origen TEXT NOT NULL,
    estacion_destino TEXT NOT NULL,
    hora_prevista_llegada TEXT NOT NULL,
    hora_real_llegada TEXT,
    retraso_minutos INTEGER,
    cancelado INTEGER NOT NULL DEFAULT 0,
    tipo_incidencia TEXT NOT NULL,
    detectado_en TEXT NOT NULL,
    avisado_telegram INTEGER NOT NULL DEFAULT 0,
    service_journey_id TEXT NOT NULL UNIQUE
);
"""


def crear_conexion() -> sqlite3.Connection:
    """
    Abre (o crea si no existe) el fichero de base de datos, se asegura
    de que la tabla 'retrasos' existe, y devuelve la conexión lista
    para usar.
    """
    # Si la carpeta "data" no existe todavía, la creamos.
    RUTA_BD.parent.mkdir(parents=True, exist_ok=True)

    conexion = sqlite3.connect(RUTA_BD)
    conexion.execute(SQL_CREAR_TABLA)
    conexion.commit()  # guarda los cambios en el fichero de forma permanente
    return conexion


def insertar_retraso(
    fecha_viaje: str,
    linea: str,
    sentido: str,
    estacion_origen: str,
    estacion_destino: str,
    hora_prevista_llegada: str,
    hora_real_llegada: str | None,
    retraso_minutos: int | None,
    cancelado: bool,
    tipo_incidencia: str,
    detectado_en: str,
    service_journey_id: str,
) -> int | None:
    """
    Guarda un nuevo registro de retraso/cancelación.
    Devuelve el id que SQLite le ha asignado a la fila nueva, o None si
    ese viaje (service_journey_id) ya estaba guardado de antes (gracias
    a la restricción UNIQUE de la columna, evitamos avisos duplicados).
    """
    conexion = crear_conexion()

    try:
        # OJO: usamos "?" como placeholders y pasamos los valores en una
        # tupla aparte, en vez de meterlos directamente en el texto del SQL
        # con f-strings. Esto se llama "consulta parametrizada" y es la
        # forma correcta y segura de hacerlo: evita errores si algún valor
        # contiene comillas, y evita la "inyección SQL".
        cursor = conexion.execute(
            """
            INSERT INTO retrasos (
                fecha_viaje, linea, sentido, estacion_origen, estacion_destino,
                hora_prevista_llegada, hora_real_llegada, retraso_minutos,
                cancelado, tipo_incidencia, detectado_en, service_journey_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fecha_viaje, linea, sentido, estacion_origen, estacion_destino,
                hora_prevista_llegada, hora_real_llegada, retraso_minutos,
                int(cancelado), tipo_incidencia, detectado_en, service_journey_id,
            ),
        )
        conexion.commit()
        nuevo_id = cursor.lastrowid
        return nuevo_id
    except sqlite3.IntegrityError:
        # La restricción UNIQUE ha saltado: este viaje ya estaba guardado.
        # No es un error real, es justo el control anti-duplicados
        # funcionando como esperamos.
        return None
    finally:
        # "finally" se ejecuta siempre, haya habido excepción o no -- así
        # nos aseguramos de cerrar la conexión pase lo que pase.
        conexion.close()


def obtener_retrasos(desde_fecha: str | None = None) -> list[sqlite3.Row]:
    """
    Devuelve todos los retrasos guardados, opcionalmente solo a partir
    de una fecha (formato "AAAA-MM-DD").
    """
    conexion = crear_conexion()
    # row_factory hace que cada fila se comporte como un diccionario
    # (por nombre de columna) en vez de solo por posición (fila[0], fila[1]...),
    # mucho más cómodo de leer en el resto del código.
    conexion.row_factory = sqlite3.Row

    if desde_fecha:
        filas = conexion.execute(
            "SELECT * FROM retrasos WHERE fecha_viaje >= ? ORDER BY fecha_viaje, hora_prevista_llegada",
            (desde_fecha,),
        ).fetchall()
    else:
        filas = conexion.execute(
            "SELECT * FROM retrasos ORDER BY fecha_viaje, hora_prevista_llegada"
        ).fetchall()

    conexion.close()
    return filas


def marcar_avisado(id_registro: int) -> None:
    """Marca un registro como ya notificado por Telegram, para no volver a avisar de él."""
    conexion = crear_conexion()
    conexion.execute(
        "UPDATE retrasos SET avisado_telegram = 1 WHERE id = ?",
        (id_registro,),
    )
    conexion.commit()
    conexion.close()


def borrar_antiguos(meses: int = 3) -> int:
    """
    Borra los registros con fecha_viaje anterior a hoy menos 'meses' meses.
    Devuelve cuántas filas se han borrado.
    """
    from datetime import date, timedelta

    # Cálculo simple de "hace X meses": restamos meses*30 días. No es
    # exacto al día (los meses no tienen todos 30 días), pero para un
    # criterio de retención no hace falta más precisión que esa.
    limite = date.today() - timedelta(days=meses * 30)
    limite_texto = limite.isoformat()

    conexion = crear_conexion()
    cursor = conexion.execute(
        "DELETE FROM retrasos WHERE fecha_viaje < ?",
        (limite_texto,),
    )
    conexion.commit()
    borrados = cursor.rowcount
    conexion.close()
    return borrados


if __name__ == "__main__":
    # Este bloque SOLO se ejecuta si corres "python3 db.py" directamente,
    # no si otro fichero hace "import db". Es el sitio típico para
    # pruebas rápidas mientras desarrollas.
    print(f"Base de datos lista en: {RUTA_BD}")

    # Insertamos un retraso de mentira, como si el RE10 de las 08:03
    # de hoy hubiera llegado con 30 minutos de retraso a Tangen.
    id_nuevo = insertar_retraso(
        fecha_viaje="2026-08-27",
        linea="RE10",
        sentido="Oslo S -> Tangen",
        estacion_origen="Oslo S",
        estacion_destino="Tangen",
        hora_prevista_llegada="2026-08-27T09:00:00",
        hora_real_llegada="2026-08-27T09:30:00",
        retraso_minutos=30,
        cancelado=False,
        tipo_incidencia="retraso",
        detectado_en="2026-08-27T09:15:00",
        service_journey_id="VYG:ServiceJourney:PRUEBA-001",
    )
    print(f"Registro de prueba insertado con id={id_nuevo}")

    # Si lo intentamos insertar otra vez con el mismo service_journey_id,
    # debe devolver None en vez de crear una fila duplicada.
    id_duplicado = insertar_retraso(
        fecha_viaje="2026-08-27", linea="RE10", sentido="Oslo S -> Tangen",
        estacion_origen="Oslo S", estacion_destino="Tangen",
        hora_prevista_llegada="2026-08-27T09:00:00", hora_real_llegada="2026-08-27T09:30:00",
        retraso_minutos=30, cancelado=False, tipo_incidencia="retraso",
        detectado_en="2026-08-27T09:15:00", service_journey_id="VYG:ServiceJourney:PRUEBA-001",
    )
    print(f"Segundo intento con el mismo viaje -> id devuelto: {id_duplicado} (debe ser None)")

    # Y ahora lo leemos de vuelta para comprobar que se guardó bien.
    registros = obtener_retrasos()
    print(f"Registros encontrados en la base de datos: {len(registros)}")
    for r in registros:
        print(dict(r))
