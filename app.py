"""Entry point del dashboard de forecast de demanda (demo).

Multipágina con st.navigation: `app_pages/inicio.py` (landing) + `app_pages/forecast.py`
(el dashboard de 3 pestañas, que consume resultados.parquet + historico.parquet de pipeline.py).
Este archivo corre ANTES de cada página: acá viven la config de página, el CSS, el selector
de idioma y la carga de datos, que son comunes a las dos. Correr con:  streamlit run app.py
"""

import re
import json
import shutil
import subprocess
import sys

import streamlit as st

import core
from core import H

st.set_page_config(page_title="Forecast de Demanda", page_icon=core.cargar_favicon(), layout="wide")

# columnas de salida de pipeline.py — nunca ofrecer como "dimensión extra" al elegir columnas
# en la carga de CSVs (duplicado a propósito, mismo patrón que ADI/CV2_THRESHOLD en core.py).
RESERVED_DIM_COLS = {
    "unique_id", "adi", "cv2", "clasificacion", "modelo_ganador", "mase",
    "existencia", "existencia_cd", "ventas_totales_cd", "pack", "lead_time_dias",
    "n_periodos", "flag_serie_corta",
    "forecast_mensual_promedio", "demanda_diaria_promedio", "doh", "wos", "moh",
    "estado_inventario", "demanda_lead_time", "cantidad_reorden",
    *[f"forecast_w{i}" for i in range(1, H + 1)], *[f"fecha_w{i}" for i in range(1, H + 1)],
}
# orden fijo: define el orden de los selectbox de mapeo (un set los desordenaria en cada rerun)
VENTAS_REQUIRED_COLS = ["sku", "centro_distribucion", "fecha", "cantidad"]
INVENTARIO_REQUIRED_COLS = ["sku", "existencia"]
# opcionales: si el CSV no las trae, pipeline.py usa el default del number_input
INVENTARIO_OPCIONALES = {"pack": 1, "lead_time_dias": 30}

# "YYYY-MM" cubre los CSV con columna de periodo (2026-02): polars lo resuelve al dia 1,
# que es justo el grano al que aggregate_monthly trunca despues.
FORMATOS_FECHA = {"Auto": "auto", "YYYY-MM-DD": "%Y-%m-%d",
                  "DD/MM/YYYY": "%d/%m/%Y", "MM/DD/YYYY": "%m/%d/%Y",
                  "YYYY-MM": "%Y-%m"}

# arriba de este umbral de series se pide confirmacion antes de lanzar el pipeline:
# con AutoARIMA exhaustivo la corrida puede durar horas y bloquea la app entera.
UMBRAL_SERIES = 2000
SEGUNDOS_POR_SERIE = 0.3

core.inject_css()

if "lang" not in st.session_state:
    st.session_state["lang"] = "en"

st.sidebar.radio(
    "🌐 " + core.STRINGS[st.session_state["lang"]]["lang_label"],
    options=["es", "en"],
    format_func=lambda x: "Español" if x == "es" else "English",
    horizontal=True,
    key="lang",
)
TXT = core.txt()


def escribir_carga(ventas_file, inventario_file, mapa_v, mapa_i, dims_v, dims_i, fmt, defaults):
    """Guarda los CSV crudos (sin parsearlos: 1.5M filas no entran dos veces en RAM) y el
    carga.json que pipeline.py aplica dentro de scan_csv. -> ruta del CSV de ventas."""
    for file, destino in ((ventas_file, "ventas_historicas.csv"), (inventario_file, "inventario.csv")):
        file.seek(0)
        with open(core.BASE / destino, "wb") as out:
            shutil.copyfileobj(file, out)
    cfg = {
        "ventas": {"columnas": mapa_v, "formato_fecha": fmt, "dimensiones": dims_v},
        "inventario": {"columnas": mapa_i, "dimensiones": dims_i},
        "defaults": defaults,
    }
    # se escribe SIEMPRE (incluso con dimensiones vacias) para no dejar colgada una carga anterior.
    (core.BASE / "carga.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    return core.BASE / "ventas_historicas.csv"


def contar_series(ruta_ventas, mapa_v):
    """Series (sku x centro) del CSV ya escrito. Con pushdown polars lee solo esas 2 columnas.
    infer_schema_length=0 (todo String) por lo mismo que _preview_df: contar unicos no
    necesita tipos, y una columna mixta no debe tumbar el preflight."""
    import polars as pl

    return (pl.scan_csv(ruta_ventas, infer_schema_length=0)
            .select(pl.struct(mapa_v["sku"], mapa_v["centro_distribucion"]).n_unique())
            .collect().item())


_ETAPA = re.compile(r"^\[(\d+)/(\d+)\]\s*(.*)")
# ruido de statsmodels/numpy (llega por stderr, ver abajo): se oculta del panel, nunca del log.
_RUIDO = re.compile(r"warn|deprecat|convergen|^\s*$", re.I)


def correr_pipeline():
    """Lanza pipeline.py y muestra su avance en un panel de altura fija.
    -> (returncode, log completo, avisos).

    stderr fusionado en stdout para que un traceback aparezca en orden con las etapas;
    -u porque el hijo bufferia por bloques cuando escribe a un pipe. Esa fusion es tambien
    la que trae los warnings de statsmodels, de ahi el filtro de _RUIDO.

    El panel NO usa status.write(): ese metodo acumula un elemento por linea y hacia crecer
    el modal sin techo. Con st.empty() se reemplaza siempre la misma linea."""
    proc = subprocess.Popen(
        [sys.executable, "-u", str(core.BASE / "pipeline.py")], cwd=core.BASE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    lineas, avisos = [], []
    with st.status(TXT["upload_processing"], expanded=True) as status:
        barra = st.progress(0.0)
        detalle = st.empty()
        for linea in proc.stdout:
            linea = linea.rstrip()
            lineas.append(linea)                    # log completo, sin filtrar
            if m := _ETAPA.match(linea):
                n, total, texto = int(m[1]), int(m[2]), m[3]
                barra.progress(n / total, text=texto)
                status.update(label=texto)
            elif linea.startswith("AVISO:"):
                avisos.append(linea)
            if not _RUIDO.search(linea):
                detalle.caption(linea)
        proc.wait()
        ok = proc.returncode == 0
        barra.empty()
        detalle.empty()
        status.update(state="complete" if ok else "error",
                      label=TXT["upload_success"] if ok else TXT["upload_error"])
    return proc.returncode, "\n".join(lineas), avisos


def _preview_df(file, n=5):
    """Lee solo las primeras n filas (headers + preview) sin materializar el CSV completo:
    en un archivo de 1.5M filas, un read_csv sin limite duplicaria todo en RAM.

    infer_schema_length=0 -> todas las columnas como String. Sin eso polars infiere el tipo
    de CADA columna y, como lee por bloques (mucho mas alla de n_rows), una columna mixta
    —"1", "1", ..., "1 MUEBLES"— tumba el preview con ComputeError aunque esa columna ni
    siquiera se vaya a mapear. El preview solo muestra texto: el tipo real no importa aca."""
    if file is None:
        return None
    import polars as pl

    file.seek(0)
    df = pl.read_csv(file, n_rows=n, infer_schema_length=0)
    file.seek(0)
    return df


def _mapeo(clave, headers, campos, opcional=False):
    """Un selectbox por campo, siempre visible, preseleccionado al header homonimo.
    -> {destino: origen}; los campos sin asignar quedan afuera. `clave` incluye el lado
    (ventas/inventario) ademas de la identidad del archivo, para que campos con el mismo
    nombre (ej. "sku") en ambos lados nunca compartan `key` de widget."""
    vacio = TXT["map_no_disponible"] if opcional else TXT["map_placeholder"]
    mapa = {}
    for c in campos:
        opciones = [vacio] + headers
        sel = st.selectbox(c, opciones, key=f"map_{clave}_{c}",
                           index=opciones.index(c) if c in headers else 0)
        if sel != vacio:
            mapa[c] = sel
    return mapa


@st.dialog(TXT["upload_title"], width="large")
def modal_carga_datos():
    """Vista unica y larga (sin tabs): ventas arriba, inventario abajo, todo con scroll."""
    st.caption(TXT["upload_help"])

    st.markdown(TXT["map_ventas_title"])
    ventas_file = st.file_uploader(TXT["upload_ventas_label"], type="csv", key="modal_upload_ventas")
    # key por identidad de archivo: evita StreamlitAPIException al cambiar de archivo
    # (seleccion previa contra opciones nuevas) — arranca de cero por archivo.
    id_v = f"{ventas_file.name}_{ventas_file.size}" if ventas_file else "v"
    prev_v = _preview_df(ventas_file)

    head_v, mapa_v, dims_v_sel, fmt_sel = [], {}, [], "auto"
    if prev_v is not None:
        st.caption(TXT["upload_preview_caption"])
        st.dataframe(prev_v.head(5))
        head_v = prev_v.columns
        st.caption(TXT["map_help"])
        mapa_v = _mapeo(f"ventas_{id_v}", head_v, VENTAS_REQUIRED_COLS)
        fmt_sel = FORMATOS_FECHA[st.selectbox(TXT["map_fecha_formato"], list(FORMATOS_FECHA),
                                              key=f"modal_fmt_{id_v}")]
        cand_v = [c for c in head_v if c not in RESERVED_DIM_COLS and c not in mapa_v.values()]
        dims_v_sel = st.multiselect(TXT["dims_ventas_label"], cand_v, default=cand_v,
                                    key=f"modal_dims_ventas_{id_v}") if cand_v else []

    st.divider()

    st.markdown(TXT["map_inventario_title"])
    inventario_file = st.file_uploader(TXT["upload_inventario_label"], type="csv", key="modal_upload_inventario")
    id_i = f"{inventario_file.name}_{inventario_file.size}" if inventario_file else "i"
    prev_i = _preview_df(inventario_file)

    head_i, mapa_i, dims_i_sel, defaults = [], {}, [], {}
    if prev_i is not None:
        st.caption(TXT["upload_preview_caption"])
        st.dataframe(prev_i.head(5))
        head_i = prev_i.columns
        mapa_i = _mapeo(f"inv_{id_i}", head_i, INVENTARIO_REQUIRED_COLS)
        st.markdown(TXT["map_inventario_opc"])
        # centro_distribucion decide el modo de calculo: asignado -> join directo sku+CD;
        # sin asignar -> pipeline.py prorratea la existencia del SKU entre sus centros.
        st.caption(TXT["inv_cd_help"])
        mapa_i |= _mapeo(f"inv_{id_i}", head_i, ["centro_distribucion"], opcional=True)
        st.caption(TXT["inv_opcional_help"])
        mapa_i |= _mapeo(f"inv_{id_i}", head_i, list(INVENTARIO_OPCIONALES), opcional=True)
        defaults = {
            "pack": st.number_input(TXT["pack_default_label"], min_value=1,
                                    value=INVENTARIO_OPCIONALES["pack"], key=f"modal_packdef_{id_i}"),
            "lead_time_dias": st.number_input(TXT["lead_time_default_label"], min_value=1,
                                              value=INVENTARIO_OPCIONALES["lead_time_dias"],
                                              key=f"modal_ltdef_{id_i}"),
        }
        cand_i = [c for c in head_i if c not in RESERVED_DIM_COLS and c not in mapa_i.values()]
        dims_i_sel = st.multiselect(TXT["dims_inventario_label"], cand_i, default=cand_i,
                                    key=f"modal_dims_inventario_{id_i}") if cand_i else []

    st.divider()

    incompleto = ([f"ventas.{c}" for c in VENTAS_REQUIRED_COLS if c not in mapa_v]
                  + [f"inventario.{c}" for c in INVENTARIO_REQUIRED_COLS if c not in mapa_i])
    duplicado = len(set(mapa_v.values())) < len(mapa_v) or len(set(mapa_i.values())) < len(mapa_i)
    if head_v and head_i and (incompleto or duplicado):
        st.warning(TXT["map_dup_error"] if duplicado else f"{TXT['map_incompleto']} {', '.join(incompleto)}")

    listo = bool(ventas_file and inventario_file and not incompleto and not duplicado)
    if st.button(TXT["upload_button"], disabled=not listo, key="modal_procesar"):
        # validado contra el estado de la UI: no se leyo ni una fila de datos todavia.
        ruta = escribir_carga(ventas_file, inventario_file, mapa_v, mapa_i,
                              dims_v_sel, dims_i_sel, fmt_sel, defaults)
        st.session_state["n_series"] = contar_series(ruta, mapa_v)

    n_series = st.session_state.get("n_series")
    if n_series is not None:
        arrancar = n_series <= UMBRAL_SERIES
        if not arrancar:
            st.warning(TXT["preflight_warning"].format(
                n=n_series, min=n_series * SEGUNDOS_POR_SERIE / 60))
            st.caption(TXT["preflight_cli"])
            st.code("python pipeline.py")
            arrancar = st.button(TXT["preflight_run_anyway"], key="modal_run_anyway")
        if arrancar:
            del st.session_state["n_series"]
            codigo, log, avisos = correr_pipeline()
            if codigo == 0:
                # el rerun cierra el modal y se lleva el panel: los avisos (overlap 0, valores
                # no numericos, filas duplicadas) son justo lo accionable, asi que sobreviven aca.
                st.session_state["avisos_carga"] = avisos
                st.cache_data.clear()
                st.rerun()
            else:
                with st.expander(TXT["log_completo"], expanded=True):
                    st.code(log)


# ------------------------------------------------------------------ Navegación
pagina = st.navigation([
    st.Page("app_pages/inicio.py", title=TXT["nav_inicio"], icon=":material/home:", default=True, url_path="inicio"),
    st.Page("app_pages/forecast.py", title=TXT["nav_forecast"], icon=":material/insights:", url_path="forecast"),
])

# ------------------------------------------------------------------ Sidebar (común a las 2 páginas) — solo nav + idioma
# El upload ahora se dispara directo desde el hub de forecast (trigger_upload_dialog),
# así que no hace falta botón en sidebar. Se mantiene título/caption + selector idioma.
st.sidebar.title(TXT["app_title"])
st.sidebar.caption(TXT["app_caption"])

# Trigger desde forecast.py hub (opción 4) -> abrir modal directo
if st.session_state.pop("trigger_upload_dialog", False):
    modal_carga_datos()

pagina.run()
