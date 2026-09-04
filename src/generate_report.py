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
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RE10 · Retrasos reclamables</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #14171A;
    --panel: #1B1F23;
    --panel-border: #2A2F35;
    --texto: #E8E6DF;
    --texto-tenue: #7C8289;
    --ambar: #E8A33D;
    --rojo: #D64545;
    --verde: #6FBF8B;
  }}

  * {{ box-sizing: border-box; }}

  body {{
    background: var(--bg);
    color: var(--texto);
    font-family: "IBM Plex Sans", sans-serif;
    margin: 0;
    padding: 2.5rem 1.25rem 4rem;
  }}

  main {{ max-width: 760px; margin: 0 auto; }}

  header {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
    border-bottom: 1px solid var(--panel-border);
    padding-bottom: 1.25rem;
  }}

  h1 {{
    font-size: 1.5rem;
    font-weight: 600;
    margin: 0;
    letter-spacing: 0.02em;
  }}

  h1 .linea {{
    font-family: "IBM Plex Mono", monospace;
    color: var(--ambar);
  }}

  .subtitulo {{
    color: var(--texto-tenue);
    font-size: 0.9rem;
    margin: 0.35rem 0 0;
  }}

  .estado {{
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.8rem;
    color: var(--texto-tenue);
  }}

  .punto {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--verde);
  }}

  .stats {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: var(--panel-border);
    margin: 1.5rem 0;
    border: 1px solid var(--panel-border);
  }}

  .stat {{
    background: var(--panel);
    padding: 1rem 1.1rem;
  }}

  .stat .valor {{
    font-family: "IBM Plex Mono", monospace;
    font-size: 1.6rem;
    font-weight: 500;
  }}

  .stat .etiqueta {{
    font-size: 0.78rem;
    color: var(--texto-tenue);
    margin-top: 0.2rem;
  }}

  .tabla-envoltorio {{
    overflow-x: auto;
    border: 1px solid var(--panel-border);
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.85rem;
    white-space: nowrap;
  }}

  th {{
    text-align: left;
    font-family: "IBM Plex Sans", sans-serif;
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    color: var(--texto-tenue);
    font-weight: 500;
    padding: 0.7rem 0.9rem;
    border-bottom: 1px solid var(--panel-border);
  }}

  td {{
    padding: 0.7rem 0.9rem;
    border-bottom: 1px solid var(--panel-border);
    background: var(--panel);
  }}

  tr:last-child td {{ border-bottom: none; }}

  .estado-fila {{
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 3px;
    font-size: 0.78rem;
  }}

  .estado-fila.retraso {{ color: var(--ambar); background: rgba(232, 163, 61, 0.12); }}
  .estado-fila.cancelado {{ color: var(--rojo); background: rgba(214, 69, 69, 0.12); }}

  .vacio {{
    padding: 2.5rem 1rem;
    text-align: center;
    color: var(--texto-tenue);
    font-size: 0.9rem;
    background: var(--panel);
  }}

  footer {{
    margin-top: 1.25rem;
    color: var(--texto-tenue);
    font-size: 0.78rem;
    font-family: "IBM Plex Mono", monospace;
  }}

  @media (max-width: 600px) {{
    .stats {{ grid-template-columns: 1fr; }}

    table, thead, tbody, tr, td {{ display: block; width: 100%; }}
    thead {{ display: none; }}

    tr {{
      border-bottom: 1px solid var(--panel-border);
      padding: 0.7rem 0.9rem;
    }}

    tr:last-child {{ border-bottom: none; }}

    td {{
      border-bottom: none;
      padding: 0.2rem 0;
      white-space: normal;
      display: flex;
      justify-content: space-between;
      gap: 1rem;
    }}

    td::before {{
      content: attr(data-label);
      font-family: "IBM Plex Sans", sans-serif;
      color: var(--texto-tenue);
      font-size: 0.72rem;
    }}
  }}
</style>
</head>
<body>
<main>
  <header>
    <div>
      <h1><span class="linea">RE10</span> · Oslo S &#8646; Tangen</h1>
      <p class="subtitulo">Retrasos &#8805;25 min o cancelaciones, en cualquiera de los dos sentidos</p>
    </div>
    <div class="estado"><span class="punto"></span>revisado cada 15 min</div>
  </header>

  <div class="stats">
    <div class="stat">
      <div class="valor">{total_incidencias}</div>
      <div class="etiqueta">incidencias registradas</div>
    </div>
    <div class="stat">
      <div class="valor">{retraso_medio}</div>
      <div class="etiqueta">retraso medio (min)</div>
    </div>
    <div class="stat">
      <div class="valor">{total_cancelados}</div>
      <div class="etiqueta">cancelaciones</div>
    </div>
  </div>

  {tabla}

  <footer>Ultima revision: {fecha_actualizacion} CET/CEST</footer>
</main>
</body>
</html>
"""

FILA_TABLA = """<tr>
  <td data-label="Fecha">{fecha_viaje}</td>
  <td data-label="Sentido">{sentido}</td>
  <td data-label="Incidencia"><span class="estado-fila {clase_css}">{tipo_texto}</span></td>
  <td data-label="Prevista">{hora_prevista}</td>
  <td data-label="Real">{hora_real}</td>
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
        tabla = (
            '<div class="tabla-envoltorio"><div class="vacio">'
            "Sin incidencias registradas todavia. En cuanto el RE10 llegue con 25 min de "
            "retraso o se cancele, aparecera aqui."
            "</div></div>"
        )
    else:
        # Mostramos las mas recientes primero.
        filas = "".join(_formatear_fila(r) for r in reversed(registros))
        tabla = (
            '<div class="tabla-envoltorio"><table><thead><tr>'
            "<th>Fecha</th><th>Sentido</th><th>Incidencia</th>"
            "<th>Prevista</th><th>Real</th>"
            "</tr></thead><tbody>" + filas + "</tbody></table></div>"
        )

    cancelados = [r for r in registros if r["cancelado"]]
    con_retraso = [r for r in registros if not r["cancelado"] and r["retraso_minutos"] is not None]
    retraso_medio = (
        round(sum(r["retraso_minutos"] for r in con_retraso) / len(con_retraso))
        if con_retraso else "-"
    )

    from datetime import datetime, timezone
    ahora_utc = datetime.now(timezone.utc).isoformat()
    fecha_actualizacion = utils.formatear_hora(ahora_utc)

    return PLANTILLA.format(
        tabla=tabla,
        total_incidencias=len(registros),
        retraso_medio=retraso_medio,
        total_cancelados=len(cancelados),
        fecha_actualizacion=fecha_actualizacion,
    )


def generar_y_guardar() -> None:
    RUTA_HTML.parent.mkdir(parents=True, exist_ok=True)
    RUTA_HTML.write_text(generar_html(), encoding="utf-8")
    print(f"Informe generado en: {RUTA_HTML}")


if __name__ == "__main__":
    generar_y_guardar()
