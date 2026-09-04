"""
generate_report.py
-------------------
Genera una página web estática (docs/index.html) con el listado de
retrasos/cancelaciones guardados en la base de datos, para poder
consultarlo desde GitHub Pages.
"""

import db
import utils

RUTA_HTML = db._encontrar_raiz_proyecto() / "docs" / "index.html"

PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>RE10 - Retrasos reclamables</title>
<style>
  body {{ font-family: sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ font-size: 1.4rem; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
  th, td {{ text-align: left; padding: 0.5rem; border-bottom: 1px solid #ddd; }}
  th {{ background: #f4f4f4; }}
  .cancelado {{ color: #b00020; font-weight: bold; }}
  .retraso {{ color: #b26a00; }}
  .actualizado {{ color: #666; font-size: 0.85rem; margin-top: 1.5rem; }}
</style>
</head>
<body>
<h1>RE10 Oslo S &lharu; Tangen &mdash; Retrasos y cancelaciones reclamables</h1>
<p>Umbral: retraso &ge; 25 min en destino, o cancelacion total/parcial del trayecto.</p>
{tabla}
<p class="actualizado">Ultima actualizacion: {fecha_actualizacion} UTC</p>
</body>
</html>
"""

FILA_TABLA = """<tr>
  <td>{fecha_viaje}</td>
  <td>{sentido}</td>
  <td class="{clase_css}">{tipo_texto}</td>
  <td>{hora_prevista}</td>
  <td>{hora_real}</td>
</tr>
"""


def _formatear_fila(registro) -> str:
    if registro["cancelado"]:
        clase_css = "cancelado"
        tipo_texto = "Cancelado"
        hora_real = "-"
    else:
        clase_css = "retraso"
        tipo_texto = f"{registro['retraso_minutos']} min tarde"
        hora_real = utils.formatear_hora(registro["hora_real_llegada"])

    return FILA_TABLA.format(
        fecha_viaje=registro["fecha_viaje"],
        sentido=registro["sentido"],
        clase_css=clase_css,
        tipo_texto=tipo_texto,
        hora_prevista=utils.formatear_hora(registro["hora_prevista_llegada"]),
        hora_real=hora_real,
    )


def generar_html() -> str:
    registros = db.obtener_retrasos()

    if not registros:
        tabla = "<p>No hay ninguna incidencia registrada todavia.</p>"
    else:
        # Mostramos las mas recientes primero.
        filas = "".join(_formatear_fila(r) for r in reversed(registros))
        tabla = (
            "<table><thead><tr>"
            "<th>Fecha</th><th>Sentido</th><th>Incidencia</th>"
            "<th>Hora prevista</th><th>Hora real</th>"
            "</tr></thead><tbody>" + filas + "</tbody></table>"
        )

    from datetime import datetime, timezone
    fecha_actualizacion = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    return PLANTILLA.format(tabla=tabla, fecha_actualizacion=fecha_actualizacion)


def generar_y_guardar() -> None:
    RUTA_HTML.parent.mkdir(parents=True, exist_ok=True)
    RUTA_HTML.write_text(generar_html(), encoding="utf-8")
    print(f"Informe generado en: {RUTA_HTML}")


if __name__ == "__main__":
    generar_y_guardar()
