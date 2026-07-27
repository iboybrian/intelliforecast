"""
Dashboard de forecast de demanda (demo).

Consume resultados.parquet + historico.parquet (generados por pipeline.py)
y los muestra en Streamlit. Correr con:  streamlit run app.py
"""

import datetime
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import polars as pl
import plotly.graph_objects as go
import streamlit as st
import xlsxwriter
from PIL import Image


def cargar_favicon():
    """Recorta assets/intelliforecast.png a cuadrado y lo reduce para el tab del navegador."""
    ruta = Path(__file__).parent / "assets" / "intelliforecast.png"
    if not ruta.exists():
        return "📦"
    im = Image.open(ruta).convert("RGBA")
    lado = min(im.size)
    x0 = (im.width - lado) // 2
    y0 = (im.height - lado) // 2
    return im.crop((x0, y0, x0 + lado, y0 + lado)).resize((64, 64), Image.LANCZOS)


st.set_page_config(page_title="Forecast de Demanda", page_icon=cargar_favicon(), layout="wide")

ADI_THRESHOLD = 1.32
CV2_THRESHOLD = 0.49
H = 4

# columnas de salida de pipeline.py — nunca ofrecer como "dimensión extra" al elegir columnas
# en la carga de CSVs (duplicado a propósito, mismo patrón que ADI/CV2_THRESHOLD arriba).
RESERVED_DIM_COLS = {
    "unique_id", "adi", "cv2", "clasificacion", "modelo_ganador", "mase",
    "existencia", "existencia_prorrateada", "pack", "lead_time_dias",
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

FORMATOS_FECHA = {"Auto": "auto", "YYYY-MM-DD": "%Y-%m-%d",
                  "DD/MM/YYYY": "%d/%m/%Y", "MM/DD/YYYY": "%m/%d/%Y"}

# arriba de este umbral de series se pide confirmacion antes de lanzar el pipeline:
# con AutoARIMA exhaustivo la corrida puede durar horas y bloquea la app entera.
UMBRAL_SERIES = 2000
SEGUNDOS_POR_SERIE = 0.3

# ---------------------------------------------------------------- Paleta (IntelliVet)
BG_DARK = "#0E1B2E"
BG_PANEL = "#16283F"
BG_PANEL_2 = "#1E3A5C"
TEXT_LIGHT = "#FFFFFF"
ACCENT_CYAN = "#7DD8F5"
ACCENT_ORANGE = "#E8935C"
GRID_LINE = "rgba(245,247,250,0.10)"

CLASE_COLOR = {
    "Smooth": ACCENT_CYAN,
    "Erratic": ACCENT_ORANGE,
    "Intermittent": "#5FD0A8",
    "Lumpy": "#E4607A",
}
ESTADO_COLOR_ES = {
    "Riesgo de quiebre": "#E4607A",
    "Sobre-stock": "#B685E8",
    "Normal": "#5FD0A8",
}
ESTADO_EN = {"Riesgo de quiebre": "Stockout risk", "Sobre-stock": "Overstock", "Normal": "Normal"}
ESTADO_COLOR_EN = {ESTADO_EN[k]: v for k, v in ESTADO_COLOR_ES.items()}

CLASE_ES = {"Smooth": "Suave", "Erratic": "Errático", "Intermittent": "Intermitente", "Lumpy": "Irregular"}

PLOTLY_LAYOUT = dict(paper_bgcolor=BG_PANEL, plot_bgcolor=BG_PANEL, font=dict(color=TEXT_LIGHT))


def axis(**extra):
    return dict(gridcolor=GRID_LINE, zerolinecolor=GRID_LINE, **extra)

# ---------------------------------------------------------------- i18n
STRINGS = {
    "es": {
        "app_title": "📦 Forecast de Demanda",
        "app_caption": "Demo — clasificación SBC + statsforecast (Nixtla)",
        "lang_label": "Idioma",
        "upload_title": "📤 Cargar tus datos",
        "upload_open_button": "📤 Cargar y Configurar Datos",
        "upload_preview_caption": "Vista previa (primeras 5 filas):",
        "upload_ventas_label": "Ventas históricas (CSV)",
        "upload_inventario_label": "Inventario (CSV)",
        "upload_help": "Cualquier CSV sirve: abajo se elige qué columna del archivo corresponde a cada campo.",
        "upload_button": "Procesar",
        "dims_ventas_label": "Dimensiones adicionales (ventas)",
        "dims_inventario_label": "Dimensiones adicionales (inventario)",
        "add_filters_label": "➕ Agregar filtros",
        "upload_processing": "Procesando datos y recalculando forecast…",
        "upload_success": "Datos actualizados.",
        "upload_error": "Error al procesar los archivos:",
        "map_help": "Elegí de qué columna de tu CSV sale cada campo:",
        "upload_missing": "Faltan columnas requeridas:",
        "map_placeholder": "— elegir —",
        "map_no_disponible": "— no está en el CSV —",
        "map_ventas_title": "**Ventas — campos obligatorios**",
        "map_inventario_title": "**Inventario — campos obligatorios**",
        "map_inventario_opc": "**Inventario — opcionales**",
        "map_fecha_formato": "Formato de fecha",
        "map_dup_error": "Una misma columna está asignada a dos campos distintos.",
        "map_incompleto": "Faltan campos por asignar.",
        "inv_opcional_help": "Si el CSV no trae la columna, se usa el valor de abajo para esos SKUs.",
        "pack_default_label": "Pack por defecto",
        "lead_time_default_label": "Lead time por defecto (días)",
        "preflight_warning": "{n:,} series a pronosticar (~{min:,.0f} min). La app queda bloqueada durante la corrida.",
        "preflight_cli": "Para no bloquear la app, correr en una terminal:",
        "preflight_run_anyway": "Correr igual",
        "no_data_filter": "Ninguna combinación cumple los filtros seleccionados.",
        "cd_label": "Centro de distribución",
        "clase_label": "Tipo de SKU",
        "proveedor_label": "Proveedor",
        "categoria_label": "Categoría",
        "sku_label": "SKU (drill-down)",
        "combos_metric": "Combinaciones SKU-CD",
        "all": "(Todos)",
        "tab_overview": "Vista general",
        "tab_risk": "SKUs en riesgo de quiebre",
        "tab_overstock": "SKUs en sobre-stock",
        "title_overview": "Vista general de inventario",
        "scope_all": "todos los centros",
        "scope_caption": "Ámbito: **{scope}** · {n} combinaciones SKU-CD",
        "doh_avg": "DOH promedio",
        "wos_avg": "WOS promedio",
        "moh_avg": "MOH promedio",
        "risk_metric": "🔴 Riesgo de quiebre",
        "over_metric": "🟣 Sobre-stock",
        "normal_metric": "🟢 Normal",
        "days_unit": "d",
        "weeks_unit": "sem",
        "months_unit": "mes",
        "scatter_title": "Clasificación de demanda según comportamiento",
        "scatter_caption": "Cuadrantes Syntetos-Boylan-Croston. Cada punto es una combinación SKU-CD.",
        "adi_axis": "ADI  (intervalo promedio entre demandas)",
        "cv2_axis": "CV²  (variabilidad del tamaño)",
        "estado_title": "Estado de inventario",
        "estado_caption": "Distribución de combinaciones por estado.",
        "estado_axis": "# combinaciones",
        "modelos_title": "Mix de modelos ganadores",
        "criticos_title": "SKUs críticos — riesgo de quiebre y sobre-stock",
        "criticos_caption": "{n} combinaciones fuera de estado Normal. Tabla ordenable — clic en encabezados.",
        "export_button": "Descargar datos de reporte e Histórico de Venta",
        "col_sku": "SKU", "col_cd": "CD", "col_clase": "Clasificación", "col_estado": "Estado",
        "col_existencia": "Existencia", "col_fcst": "Fcst. mensual", "col_doh": "DOH", "col_wos": "WOS",
        "col_lead": "Lead time (d)", "col_reorden": "Reorden sugerido", "col_modelo": "Modelo", "col_mase": "MASE",
        "col_moh": "MOH", "col_fcst_compra": "Forecast de compra", "col_fecha_ideal": "Fecha ideal reorden",
        "col_fcst_prom": "Fcst mensual promedio",
        "col_dias_quiebre": "Días estimados para quiebre",
        "risk_asap": "ASAP (con retraso)",
        "risk_sugerido": "Sugerido a ordenar",
        "risk_sugerido_help": "Sugerido a ordenar para cubrir 1.5× el lead time.",
        "drilldown_title": "Drill-down · {sku}",
        "cd_drill_label": "Centro de distribución para el detalle",
        "clasificacion_metric": "Clasificación",
        "modelo_metric": "Modelo ganador",
        "mase_metric": "MASE",
        "doh_metric": "DOH",
        "doh_help": "Días de cobertura al ritmo de demanda pronosticado",
        "estado_metric": "Estado",
        "badge_line": "Existencia: **{exist:,.0f}** · Reorden sugerido (múltiplo de pack {pack}): **{reorden:,.0f}**",
        "chart_hist": "Histórico",
        "chart_fcst": "Forecast ({modelo})",
        "chart_xaxis": "Fecha",
        "chart_yaxis": "Cantidad (mensual)",
        "chart_title": "{sku} · {cd} — histórico + {h} meses de forecast",
        "winner_caption": "Modelo ganador **{modelo}** seleccionado por menor MASE (**{mase:.2f}**) en backtesting con cross-validation temporal (rolling origin).",
        "short_series_caption": "⚠️ Serie corta: solo **{n}** meses de historia, insuficiente para backtesting. Se usa **SeasonalNaive** (último valor) y el MASE no es comparable con el del resto.",
        "risk_header": "SKUs en riesgo de quiebre",
        "risk_caption": "Ordenados por urgencia (menor DOH primero). Ámbito: **{scope}** · {n} combinaciones.",
        "risk_search": "Buscar SKU",
        "risk_select_sku": "Elegir combinación SKU · CD",
        "risk_total_reorden": "Unidades totales a reordenar",
        "risk_n_metric": "SKUs en riesgo",
        "risk_no_results": "No hay combinaciones en riesgo de quiebre para este filtro.",
        "risk_stock": "Stock",
        "risk_legend_full": "Demanda pronosticada durante el lead time de reabasto · DOH y fecha ideal de reorden estimados con la existencia registrada hoy ({hoy}).",
        "risk_expander": "📈 Ver venta de los últimos 12 periodos",
        "risk_sales_yaxis": "Cantidad (mensual)",
        "overstock_header": "SKUs en sobre-stock",
        "overstock_caption": "Ordenados por exceso (mayor DOH primero). Ámbito: **{scope}** · {n} combinaciones.",
        "overstock_n_metric": "SKUs en sobre-stock",
        "overstock_total_exceso": "Unidades en exceso totales",
        "overstock_no_results": "No hay combinaciones en sobre-stock para este filtro.",
        "overstock_asof_note": "DOH estimado con la existencia registrada hoy ({hoy}).",
        "col_exceso": "Exceso",
    },
    "en": {
        "app_title": "📦 Demand Forecast",
        "app_caption": "Demo — SBC classification + statsforecast (Nixtla)",
        "lang_label": "Language",
        "upload_title": "📤 Upload your data",
        "upload_open_button": "📤 Upload and Configure Data",
        "upload_preview_caption": "Preview (first 5 rows):",
        "upload_ventas_label": "Sales history (CSV)",
        "upload_inventario_label": "Inventory (CSV)",
        "upload_help": "Any CSV works: below you pick which column of your file maps to each field.",
        "upload_button": "Process",
        "dims_ventas_label": "Additional dimensions (sales)",
        "dims_inventario_label": "Additional dimensions (inventory)",
        "add_filters_label": "➕ Add filters",
        "upload_processing": "Processing data and recalculating forecast…",
        "upload_success": "Data updated.",
        "upload_error": "Error processing files:",
        "map_help": "Pick which column of your CSV maps to each field:",
        "upload_missing": "Missing required columns:",
        "map_placeholder": "— pick one —",
        "map_no_disponible": "— not in the CSV —",
        "map_ventas_title": "**Sales — required fields**",
        "map_inventario_title": "**Inventory — required fields**",
        "map_inventario_opc": "**Inventory — optional**",
        "map_fecha_formato": "Date format",
        "map_dup_error": "The same column is assigned to two different fields.",
        "map_incompleto": "Some fields are still unassigned.",
        "inv_opcional_help": "If the CSV lacks the column, the value below is used for those SKUs.",
        "pack_default_label": "Default pack",
        "lead_time_default_label": "Default lead time (days)",
        "preflight_warning": "{n:,} series to forecast (~{min:,.0f} min). The app stays blocked during the run.",
        "preflight_cli": "To avoid blocking the app, run in a terminal:",
        "preflight_run_anyway": "Run anyway",
        "no_data_filter": "No combination matches the selected filters.",
        "cd_label": "Distribution center",
        "clase_label": "SKU type",
        "proveedor_label": "Supplier",
        "categoria_label": "Category",
        "sku_label": "SKU (drill-down)",
        "combos_metric": "SKU-DC combinations",
        "all": "(All)",
        "tab_overview": "Overview",
        "tab_risk": "SKUs at stockout risk",
        "tab_overstock": "Overstock SKUs",
        "title_overview": "Inventory overview",
        "scope_all": "all distribution centers",
        "scope_caption": "Scope: **{scope}** · {n} SKU-DC combinations",
        "doh_avg": "Avg. DOH",
        "wos_avg": "Avg. WOS",
        "moh_avg": "Avg. MOH",
        "risk_metric": "🔴 Stockout risk",
        "over_metric": "🟣 Overstock",
        "normal_metric": "🟢 Normal",
        "days_unit": "d",
        "weeks_unit": "wk",
        "months_unit": "mo",
        "scatter_title": "Demand classification · ADI vs CV²",
        "scatter_caption": "Syntetos-Boylan-Croston quadrants. Each point is one SKU-DC combination.",
        "adi_axis": "ADI  (avg. interval between demands)",
        "cv2_axis": "CV²  (demand size variability)",
        "estado_title": "Inventory status",
        "estado_caption": "Distribution of combinations by status.",
        "estado_axis": "# combinations",
        "modelos_title": "Winning model mix",
        "criticos_title": "Critical SKUs — stockout risk and overstock",
        "criticos_caption": "{n} combinations outside Normal status. Sortable table — click headers.",
        "export_button": "Download report data and Sales History",
        "col_sku": "SKU", "col_cd": "DC", "col_clase": "Classification", "col_estado": "Status",
        "col_existencia": "Stock", "col_fcst": "Monthly fcst.", "col_doh": "DOH", "col_wos": "WOS",
        "col_lead": "Lead time (d)", "col_reorden": "Suggested reorder", "col_modelo": "Model", "col_mase": "MASE",
        "col_moh": "MOH", "col_fcst_compra": "Purchase forecast", "col_fecha_ideal": "Ideal reorder date",
        "col_fcst_prom": "Avg monthly fcst",
        "col_dias_quiebre": "Est. days to stockout",
        "risk_asap": "ASAP (overdue)",
        "risk_sugerido": "Suggested to order",
        "risk_sugerido_help": "Suggested to order to cover 1.5× the lead time.",
        "drilldown_title": "Drill-down · {sku}",
        "cd_drill_label": "Distribution center for detail",
        "clasificacion_metric": "Classification",
        "modelo_metric": "Winning model",
        "mase_metric": "MASE",
        "doh_metric": "DOH",
        "doh_help": "Days of coverage at forecasted demand rate",
        "estado_metric": "Status",
        "badge_line": "Stock: **{exist:,.0f}** · Suggested reorder (pack multiple of {pack}): **{reorden:,.0f}**",
        "chart_hist": "Historical",
        "chart_fcst": "Forecast ({modelo})",
        "chart_xaxis": "Date",
        "chart_yaxis": "Quantity (monthly)",
        "chart_title": "{sku} · {cd} — historical + {h}-month forecast",
        "winner_caption": "Winning model **{modelo}** selected for lowest MASE (**{mase:.2f}**) via temporal cross-validation backtesting (rolling origin).",
        "short_series_caption": "⚠️ Short series: only **{n}** months of history, not enough for backtesting. Falls back to **SeasonalNaive** (last value); its MASE is not comparable to the rest.",
        "risk_header": "SKUs at stockout risk",
        "risk_caption": "Sorted by urgency (lowest DOH first). Scope: **{scope}** · {n} combinations.",
        "risk_search": "Search SKU",
        "risk_select_sku": "Choose SKU · DC combination",
        "risk_total_reorden": "Total units to reorder",
        "risk_n_metric": "SKUs at risk",
        "risk_no_results": "No combinations at stockout risk for this filter.",
        "risk_stock": "Stock",
        "risk_legend_full": "Forecasted demand over the replenishment lead time · DOH and ideal reorder date estimated using stock on record as of today ({hoy}).",
        "risk_expander": "📈 View sales for the last 12 periods",
        "risk_sales_yaxis": "Quantity (monthly)",
        "overstock_header": "SKUs at overstock",
        "overstock_caption": "Sorted by excess (highest DOH first). Scope: **{scope}** · {n} combinations.",
        "overstock_n_metric": "Overstock SKUs",
        "overstock_total_exceso": "Total excess units",
        "overstock_no_results": "No combinations at overstock for this filter.",
        "overstock_asof_note": "DOH estimated using stock on record as of today ({hoy}).",
        "col_exceso": "Excess",
    },
}


def inject_css():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');
        html, body, [class*="css"], .stText, .stMarkdown, h1, h2, h3, h4, .stMetric, button, input, select {{
            font-family: 'JetBrains Mono', monospace !important;
        }}
        .stApp {{
            background: radial-gradient(circle at 78% 15%, {BG_PANEL_2} 0%, {BG_DARK} 55%);
            color: {TEXT_LIGHT};
        }}
        .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stApp label, .stApp span, .stApp li {{
            color: {TEXT_LIGHT} !important;
        }}
        section[data-testid="stSidebar"] {{
            background-color: {BG_PANEL};
        }}
        div[data-testid="stMetric"] {{
            background-color: {BG_PANEL};
            border: 1px solid rgba(245,247,250,0.08);
            border-radius: 10px;
            padding: 10px 14px;
        }}
        div[data-testid="stMetricLabel"] {{
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
            line-height: 1.2;
        }}
        div[data-testid="stMetricValue"] {{
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: unset !important;
            font-size: 1.5rem !important;
            line-height: 1.25;
            word-break: break-word;
        }}
        .streamlit-expanderHeader {{
            background-color: {BG_PANEL};
            border-radius: 8px;
        }}
        /* Quitar barra blanca superior pero conservar el botón de colapsar sidebar */
        header[data-testid="stHeader"] {{
            background: transparent;
        }}
        div[data-testid="stAppViewContainer"] > .main .block-container {{
            padding-top: 1rem;
        }}
        /* Filtros compactos: sin wrap vertical, menos espacio entre widgets y hacia los tabs */
        div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
            flex-wrap: nowrap;
            overflow-x: auto;
            max-height: 2.4rem;
        }}
        div[element-container-key] {{
            margin-bottom: 0 !important;
        }}
        div.stSelectbox, div.stMultiSelect {{
            margin-bottom: 0 !important;
        }}
        div[data-testid="stTabs"] {{
            margin-top: 0.25rem;
        }}
        /* Botón de descarga: alineado a la derecha, tipografía y padding consistentes */
        div.stDownloadButton {{
            display: flex;
            justify-content: flex-end;
        }}
        div.stDownloadButton button {{
            background-color: {ACCENT_CYAN} !important;
            color: {BG_DARK} !important;
            border: none !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-weight: 600;
            padding: 0.5rem 1rem;
            height: auto;
            line-height: 1.3;
        }}
        div.stDownloadButton button:hover {{
            background-color: {ACCENT_ORANGE} !important;
            color: {BG_DARK} !important;
        }}
        div.stDownloadButton button * {{
            color: {BG_DARK} !important;
        }}
        /* File uploader legible: botón siempre con color de acento */
        div[data-testid="stFileUploader"] section {{
            background-color: {BG_PANEL_2};
            border: 1px dashed {ACCENT_CYAN};
        }}
        div[data-testid="stFileUploader"] button {{
            background-color: {ACCENT_CYAN} !important;
            color: {BG_DARK} !important;
            border: none !important;
            font-weight: 600;
        }}
        div[data-testid="stFileUploader"] button:hover {{
            background-color: {ACCENT_ORANGE} !important;
            color: {BG_DARK} !important;
        }}
        div[data-testid="stFileUploader"] button * {{
            color: {BG_DARK} !important;
        }}
        /* Botones genericos (sidebar, modal de carga, "Procesar", "Correr igual"): al hacer
        click, Streamlit/BaseWeb aplica un fondo blanco de foco que queda ilegible sobre el
        tema oscuro. Forzar un gris celeste palido con texto oscuro en :active/:focus. */
        .stApp button:active, .stApp button:focus, .stApp button:focus:not(:active) {{
            background-color: #B0C4DE !important;
            color: #1A2733 !important;
            border-color: #B0C4DE !important;
        }}
        .stApp button:active *, .stApp button:focus *, .stApp button:focus:not(:active) * {{
            color: #1A2733 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()

if "lang" not in st.session_state:
    st.session_state["lang"] = "es"

st.sidebar.radio(
    "🌐 " + STRINGS[st.session_state["lang"]]["lang_label"],
    options=["es", "en"],
    format_func=lambda x: "Español" if x == "es" else "English",
    horizontal=True,
    key="lang",
)
TXT = STRINGS[st.session_state["lang"]]
LANG = st.session_state["lang"]
ESTADO_MAP = ESTADO_EN if LANG == "en" else {k: k for k in ESTADO_COLOR_ES}
ESTADO_COLOR = ESTADO_COLOR_EN if LANG == "en" else ESTADO_COLOR_ES
CLASE_MAP = CLASE_ES if LANG == "es" else {k: k for k in CLASE_COLOR}


@st.cache_data
def load():
    base = Path(__file__).parent
    if not (base / "resultados.parquet").exists():
        return None, None
    res = pl.read_parquet(base / "resultados.parquet")
    hist = pl.read_parquet(base / "historico.parquet")
    return res, hist


def load_dim_config():
    """Dimensiones extra elegidas al subir los CSVs (carga.json, escrito por escribir_carga).
    No cacheado: archivo trivial, se regenera en cada 'Procesar'."""
    ruta = Path(__file__).parent / "carga.json"
    if not ruta.exists():
        return []
    cfg = json.loads(ruta.read_text(encoding="utf-8"))
    return [d for lado in ("ventas", "inventario") for d in cfg.get(lado, {}).get("dimensiones", [])]


def escribir_carga(ventas_file, inventario_file, mapa_v, mapa_i, dims_v, dims_i, fmt, defaults):
    """Guarda los CSV crudos (sin parsearlos: 1.5M filas no entran dos veces en RAM) y el
    carga.json que pipeline.py aplica dentro de scan_csv. -> ruta del CSV de ventas."""
    base = Path(__file__).parent
    for file, destino in ((ventas_file, "ventas_historicas.csv"), (inventario_file, "inventario.csv")):
        file.seek(0)
        with open(base / destino, "wb") as out:
            shutil.copyfileobj(file, out)
    cfg = {
        "ventas": {"columnas": mapa_v, "formato_fecha": fmt, "dimensiones": dims_v},
        "inventario": {"columnas": mapa_i, "dimensiones": dims_i},
        "defaults": defaults,
    }
    # se escribe SIEMPRE (incluso con dimensiones vacias) para no dejar colgada una carga anterior.
    (base / "carga.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    return base / "ventas_historicas.csv"


def contar_series(ruta_ventas, mapa_v):
    """Series (sku x centro) del CSV ya escrito. Con pushdown polars lee solo esas 2 columnas."""
    return (pl.scan_csv(ruta_ventas)
            .select(pl.struct(mapa_v["sku"], mapa_v["centro_distribucion"]).n_unique())
            .collect().item())


def correr_pipeline():
    """Lanza pipeline.py y transmite su salida en vivo. -> (returncode, cola del log).
    stderr fusionado en stdout para que un traceback aparezca en orden con las etapas;
    -u porque el hijo bufferia por bloques cuando escribe a un pipe."""
    base = Path(__file__).parent
    proc = subprocess.Popen(
        [sys.executable, "-u", str(base / "pipeline.py")], cwd=base,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    lineas = []
    with st.status(TXT["upload_processing"], expanded=True) as status:
        for linea in proc.stdout:
            lineas.append(linea)
            status.write(linea.rstrip())
        proc.wait()
        ok = proc.returncode == 0
        status.update(state="complete" if ok else "error",
                      label=TXT["upload_success"] if ok else TXT["upload_error"])
    return proc.returncode, "".join(lineas[-60:])


def exportar_excel(df_kpi: pl.DataFrame, ids: list[str]) -> bytes:
    """xlsx con la tabla KPI visible (hoja 1) + historico mensual, ultimos 24 meses (hoja 2)."""
    hist24 = (
        hist.filter(pl.col("unique_id").is_in(ids))
        .sort(["unique_id", "fecha"])
        .group_by("unique_id", maintain_order=True).tail(24)
        .select(["sku", "centro_distribucion", "fecha", "cantidad"])
    )
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True, "nan_inf_to_errors": True})
    df_kpi.write_excel(workbook=wb, worksheet="KPIs")
    hist24.write_excel(workbook=wb, worksheet="Historico 24m")
    wb.close()
    return buf.getvalue()


def boton_descarga(container, df_kpi: pl.DataFrame, ids: list[str], file_name: str):
    container.download_button(
        TXT["export_button"], data=exportar_excel(df_kpi, ids), file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon="📥",
    )


def _preview_df(file, n=5):
    """Lee solo las primeras n filas (headers + preview) sin materializar el CSV completo:
    en un archivo de 1.5M filas, un read_csv sin limite duplicaria todo en RAM."""
    if file is None:
        return None
    file.seek(0)
    df = pl.read_csv(file, n_rows=n, infer_schema_length=n)
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
        st.dataframe(prev_v.head(5), use_container_width=True)
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
        st.dataframe(prev_i.head(5), use_container_width=True)
        head_i = prev_i.columns
        mapa_i = _mapeo(f"inv_{id_i}", head_i, INVENTARIO_REQUIRED_COLS)
        st.markdown(TXT["map_inventario_opc"])
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
            codigo, log = correr_pipeline()
            if codigo == 0:
                st.cache_data.clear()
                st.rerun()
            else:
                st.code(log)


# ------------------------------------------------------------------ Sidebar
st.sidebar.title(TXT["app_title"])
st.sidebar.caption(TXT["app_caption"])

if st.sidebar.button(TXT["upload_open_button"]):
    modal_carga_datos()

res, hist = load()
if res is None:
    st.error("No se encontró resultados.parquet. Corre primero:  python pipeline.py")
    st.stop()

res = res.with_columns(
    pl.col("estado_inventario").replace(ESTADO_MAP).alias("estado_inventario"),
    pl.col("clasificacion").replace(CLASE_MAP).alias("clasificacion"),
)

# ------------------------------------------------------------------ Filtros (una sola fila)
f1, f2, f3, f4, f5, f6 = st.columns([1, 1.2, 1, 1, 1.3, 0.9])

cds = [TXT["all"]] + sorted(res["centro_distribucion"].unique().to_list())
cd_sel = f1.selectbox(TXT["cd_label"], cds)

clases_disp = sorted(res["clasificacion"].unique().to_list())
clase_sel = f2.multiselect(TXT["clase_label"], clases_disp, default=clases_disp)


def filtro_opcional(container, col, label):
    """selectbox (Todos)+valores si la columna existe; deshabilitado si no."""
    if col in res.columns:
        opciones = [TXT["all"]] + sorted(res[col].drop_nulls().unique().to_list())
        return container.selectbox(label, opciones)
    container.selectbox(label, [TXT["all"]], disabled=True)
    return TXT["all"]


proveedor_sel = filtro_opcional(f3, "proveedor", TXT["proveedor_label"])
categoria_sel = filtro_opcional(f4, "categoria", TXT["categoria_label"])

res_f = res
if cd_sel != TXT["all"]:
    res_f = res_f.filter(pl.col("centro_distribucion") == cd_sel)
if clase_sel:
    res_f = res_f.filter(pl.col("clasificacion").is_in(clase_sel))
if "proveedor" in res.columns and proveedor_sel != TXT["all"]:
    res_f = res_f.filter(pl.col("proveedor") == proveedor_sel)
if "categoria" in res.columns and categoria_sel != TXT["all"]:
    res_f = res_f.filter(pl.col("categoria") == categoria_sel)

# dimensiones extra de carga.json: el nombre de la columna es tambien su etiqueta.
dims_disp = sorted({d for d in load_dim_config() if d in res.columns} - {"proveedor", "categoria"})
if dims_disp:
    elegidas = st.multiselect(TXT["add_filters_label"], dims_disp, default=[])
    if elegidas:
        for c, dim in zip(st.columns(len(elegidas)), elegidas):
            val_sel = filtro_opcional(c, dim, dim)
            if val_sel != TXT["all"]:
                res_f = res_f.filter(pl.col(dim) == val_sel)

if res_f.height == 0:
    st.warning(TXT["no_data_filter"])
    st.stop()

skus = sorted(res_f["sku"].unique().to_list())
sku_sel = f5.selectbox(TXT["sku_label"], skus)
f6.metric(TXT["combos_metric"], res_f.height)

tab_overview, tab_risk, tab_overstock = st.tabs(
    [TXT["tab_overview"], TXT["tab_risk"], TXT["tab_overstock"]]
)

# ==================================================================== TAB 1: Overview
with tab_overview:
    st.title(TXT["title_overview"])
    scope = TXT["scope_all"] if cd_sel == TXT["all"] else cd_sel
    st.caption(TXT["scope_caption"].format(scope=scope, n=res_f.height))

    doh_prom = res_f["doh"].mean()
    wos_prom = res_f["wos"].mean()
    moh_prom = res_f["moh"].mean()
    estado_riesgo = ESTADO_MAP["Riesgo de quiebre"]
    estado_sobre = ESTADO_MAP["Sobre-stock"]
    estado_normal = ESTADO_MAP["Normal"]
    n_riesgo = res_f.filter(pl.col("estado_inventario") == estado_riesgo).height
    n_sobre = res_f.filter(pl.col("estado_inventario") == estado_sobre).height
    n_normal = res_f.filter(pl.col("estado_inventario") == estado_normal).height

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(TXT["doh_avg"], f"{doh_prom:,.0f} {TXT['days_unit']}" if doh_prom is not None else "—")
    c2.metric(TXT["wos_avg"], f"{wos_prom:,.1f} {TXT['weeks_unit']}" if wos_prom is not None else "—")
    c3.metric(TXT["moh_avg"], f"{moh_prom:,.1f} {TXT['months_unit']}" if moh_prom is not None else "—")
    c4.metric(TXT["risk_metric"], n_riesgo)
    c5.metric(TXT["over_metric"], n_sobre)
    c6.metric(TXT["normal_metric"], n_normal)

    st.divider()

    left, right = st.columns([3, 2])

    with left:
        st.subheader(TXT["scatter_title"])
        st.caption(TXT["scatter_caption"])

        fig = go.Figure()
        x_max = max(float(res_f["adi"].max() or 3.0) * 1.05, ADI_THRESHOLD * 1.5)
        y_max = max(float(res_f["cv2"].max() or 1.0) * 1.05, CV2_THRESHOLD * 1.5)
        quad_bands = [
            (0, ADI_THRESHOLD, 0, CV2_THRESHOLD, "Smooth"),
            (0, ADI_THRESHOLD, CV2_THRESHOLD, y_max, "Erratic"),
            (ADI_THRESHOLD, x_max, 0, CV2_THRESHOLD, "Intermittent"),
            (ADI_THRESHOLD, x_max, CV2_THRESHOLD, y_max, "Lumpy"),
        ]
        for x0, x1, y0, y1, clase in quad_bands:
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                          fillcolor=CLASE_COLOR[clase], opacity=0.12, line_width=0, layer="below")
            fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=CLASE_MAP[clase], showarrow=False,
                               font=dict(size=13, color=CLASE_COLOR[clase]), opacity=0.75)

        for clase, color in CLASE_COLOR.items():
            sub = res_f.filter(pl.col("clasificacion") == CLASE_MAP[clase])
            if sub.height == 0:
                continue
            fig.add_trace(go.Scatter(
                x=sub["adi"].to_list(), y=sub["cv2"].to_list(),
                mode="markers", name=CLASE_MAP[clase],
                marker=dict(size=9, color=color, line=dict(width=0.5, color=BG_DARK), opacity=0.9),
                text=[f"{s}·{c}" for s, c in zip(sub["sku"], sub["centro_distribucion"])],
                hovertemplate="%{text}<br>ADI=%{x:.2f}<br>CV²=%{y:.2f}<extra></extra>",
            ))

        hl = res_f.filter(pl.col("sku") == sku_sel)
        if hl.height > 0:
            fig.add_trace(go.Scatter(
                x=hl["adi"].to_list(), y=hl["cv2"].to_list(),
                mode="markers", name=f"◉ {sku_sel}", showlegend=True,
                marker=dict(size=18, color="rgba(0,0,0,0)", line=dict(width=3, color=TEXT_LIGHT)),
                hoverinfo="skip",
            ))

        fig.add_vline(x=ADI_THRESHOLD, line=dict(color="rgba(245,247,250,0.35)", dash="dash", width=1))
        fig.add_hline(y=CV2_THRESHOLD, line=dict(color="rgba(245,247,250,0.35)", dash="dash", width=1))
        fig.update_layout(
            **PLOTLY_LAYOUT,
            xaxis_title=TXT["adi_axis"], yaxis_title=TXT["cv2_axis"],
            xaxis=axis(range=[0, x_max]),
            yaxis=axis(range=[0, y_max]),
            height=440, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader(TXT["estado_title"])
        st.caption(TXT["estado_caption"])
        estado_counts = res_f.group_by("estado_inventario").len().sort("len", descending=True)
        figb = go.Figure()
        for row in estado_counts.iter_rows(named=True):
            figb.add_trace(go.Bar(
                x=[row["len"]], y=[row["estado_inventario"]], orientation="h",
                marker_color=ESTADO_COLOR.get(row["estado_inventario"], "#888"),
                text=[row["len"]], textposition="outside", showlegend=False,
            ))
        figb.update_layout(**PLOTLY_LAYOUT, height=200, margin=dict(l=10, r=30, t=10, b=10),
                           xaxis=axis(), yaxis=axis(), xaxis_title=TXT["estado_axis"], barmode="stack")
        st.plotly_chart(figb, use_container_width=True)

        st.subheader(TXT["modelos_title"])
        modelos = res_f.group_by("modelo_ganador").len().sort("len", descending=True)
        figm = go.Figure(go.Bar(
            x=modelos["len"].to_list(), y=modelos["modelo_ganador"].to_list(),
            orientation="h", marker_color=ACCENT_CYAN,
            text=modelos["len"].to_list(), textposition="outside",
        ))
        figm.update_layout(**PLOTLY_LAYOUT, height=220, margin=dict(l=10, r=30, t=10, b=10),
                           xaxis=axis(), xaxis_title=TXT["estado_axis"], yaxis=axis(autorange="reversed"))
        st.plotly_chart(figm, use_container_width=True)

    st.divider()

    st.subheader(TXT["criticos_title"])
    criticos_base = res_f.filter(pl.col("estado_inventario") != estado_normal).sort(
        ["estado_inventario", "doh"]
    )
    criticos = criticos_base.select([
        pl.col("sku").alias(TXT["col_sku"]), pl.col("centro_distribucion").alias(TXT["col_cd"]),
        pl.col("clasificacion").alias(TXT["col_clase"]), pl.col("estado_inventario").alias(TXT["col_estado"]),
        pl.col("existencia_prorrateada").round(0).alias(TXT["col_existencia"]),
        pl.col("forecast_mensual_promedio").round(1).alias(TXT["col_fcst"]),
        pl.col("doh").round(1).alias(TXT["col_doh"]),
        pl.col("wos").round(1).alias(TXT["col_wos"]),
        pl.col("lead_time_dias").alias(TXT["col_lead"]),
        pl.col("cantidad_reorden").round(0).alias(TXT["col_reorden"]),
        pl.col("modelo_ganador").alias(TXT["col_modelo"]), pl.col("mase").round(2).alias(TXT["col_mase"]),
    ])
    if criticos.height > 0:
        leg_col, dl_col = st.columns([4, 1])
        leg_col.caption(TXT["criticos_caption"].format(n=criticos.height))
        boton_descarga(dl_col, criticos, criticos_base["unique_id"].to_list(), "skus_criticos.xlsx")

    st.dataframe(criticos, use_container_width=True, height=340, hide_index=True)

    st.divider()

    st.subheader(TXT["drilldown_title"].format(sku=sku_sel))

    sku_rows = res_f.filter(pl.col("sku") == sku_sel).sort("centro_distribucion")
    cd_opciones = sku_rows["centro_distribucion"].to_list()
    if len(cd_opciones) > 1:
        cd_drill = st.radio(TXT["cd_drill_label"], cd_opciones, horizontal=True)
    else:
        cd_drill = cd_opciones[0]

    row = sku_rows.filter(pl.col("centro_distribucion") == cd_drill).row(0, named=True)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric(TXT["clasificacion_metric"], row["clasificacion"])
    k2.metric(TXT["modelo_metric"], row["modelo_ganador"])
    k3.metric(TXT["mase_metric"], f"{row['mase']:.2f}")
    doh_val = row["doh"]
    k4.metric(TXT["doh_metric"], f"{doh_val:,.0f} {TXT['days_unit']}" if doh_val is not None else "∞",
              help=TXT["doh_help"])
    k5.metric(TXT["col_lead"], f"{row['lead_time_dias']:,.0f} {TXT['days_unit']}")
    k6.metric(TXT["estado_metric"], row["estado_inventario"])

    badge = ESTADO_COLOR.get(row["estado_inventario"], "#888")
    st.markdown(
        f"<span style='background:{badge};color:{BG_DARK};padding:3px 10px;border-radius:12px;"
        f"font-size:0.85em;font-weight:600'>{row['estado_inventario']}</span> &nbsp; "
        + TXT["badge_line"].format(exist=row["existencia_prorrateada"], pack=row["pack"], reorden=row["cantidad_reorden"]),
        unsafe_allow_html=True,
    )

    uid = row["unique_id"]
    serie = hist.filter(pl.col("unique_id") == uid).sort("fecha")

    fechas_fc = [row[f"fecha_w{i}"] for i in range(1, H + 1)]
    valores_fc = [row[f"forecast_w{i}"] for i in range(1, H + 1)]

    figf = go.Figure()
    figf.add_trace(go.Scatter(
        x=serie["fecha"].to_list(), y=serie["cantidad"].to_list(),
        mode="lines", name=TXT["chart_hist"], line=dict(color=ACCENT_CYAN, width=1.8),
    ))
    if serie.height > 0:
        x_bridge = [serie["fecha"].to_list()[-1]] + fechas_fc
        y_bridge = [serie["cantidad"].to_list()[-1]] + valores_fc
    else:
        x_bridge, y_bridge = fechas_fc, valores_fc
    figf.add_trace(go.Scatter(
        x=x_bridge, y=y_bridge, mode="lines+markers",
        name=TXT["chart_fcst"].format(modelo=row["modelo_ganador"]),
        line=dict(color=ACCENT_ORANGE, width=2.5, dash="dot"),
        marker=dict(size=8),
    ))
    figf.update_layout(
        **PLOTLY_LAYOUT,
        height=380, margin=dict(l=10, r=10, t=30, b=10),
        xaxis=axis(title=TXT["chart_xaxis"]), yaxis=axis(title=TXT["chart_yaxis"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        title=dict(text=TXT["chart_title"].format(sku=sku_sel, cd=cd_drill, h=H), font=dict(size=14)),
    )
    st.plotly_chart(figf, use_container_width=True)
    if row.get("flag_serie_corta"):
        # el MASE de una serie corta sale de un holdout de 1 punto: no es comparable con el de
        # 3 ventanas/h=4 de las series largas. Decirlo, o parecen las mas precisas del tablero.
        st.caption(TXT["short_series_caption"].format(n=row["n_periodos"]))
    else:
        st.caption(TXT["winner_caption"].format(modelo=row["modelo_ganador"], mase=row["mase"]))

# ==================================================================== TAB 2: SKUs en riesgo
with tab_risk:
    st.title(TXT["risk_header"])
    scope = TXT["scope_all"] if cd_sel == TXT["all"] else cd_sel

    riesgo = res_f.filter(pl.col("estado_inventario") == estado_riesgo).sort("doh")

    st.caption(TXT["risk_caption"].format(scope=scope, n=riesgo.height))

    search = st.text_input("🔎 " + TXT["risk_search"], "")
    if search:
        riesgo = riesgo.filter(pl.col("sku").str.contains(f"(?i){search}"))

    m1, m2 = st.columns(2)
    m1.metric(TXT["risk_n_metric"], riesgo.height)
    m2.metric(TXT["risk_total_reorden"], f"{riesgo['cantidad_reorden'].sum():,.0f}" if riesgo.height else "0")

    st.divider()

    if riesgo.height == 0:
        st.info(TXT["risk_no_results"])
    else:
        hoy = datetime.date.today()
        dias_atraso_expr = pl.max_horizontal(pl.col("lead_time_dias") - pl.col("doh").fill_null(0), pl.lit(0.0))
        riesgo = riesgo.with_columns(dias_atraso_expr.round(0).cast(pl.Int64).alias("dias_atraso"))
        riesgo = riesgo.with_columns(
            (pl.lit(hoy).cast(pl.Date) - pl.duration(days=pl.col("dias_atraso"))).alias("fecha_ideal_reorden")
        )
        # fecha ideal como texto: si ya pasó -> ASAP; si no, fecha (sin hora).
        fecha_txt_expr = (
            pl.when(pl.col("fecha_ideal_reorden") < pl.lit(hoy).cast(pl.Date))
              .then(pl.lit(TXT["risk_asap"]))
              .otherwise(pl.col("fecha_ideal_reorden").dt.to_string("%Y-%m-%d"))
        )
        riesgo = riesgo.with_columns(
            fecha_txt_expr.alias("fecha_ideal_txt"),
            pl.col("doh").round(0).cast(pl.Int64).alias("dias_para_quiebre"),
        )

        tabla_riesgo = riesgo.select([
            pl.col("sku").alias(TXT["col_sku"]), pl.col("centro_distribucion").alias(TXT["col_cd"]),
            pl.col("clasificacion").alias(TXT["col_clase"]),
            pl.col("lead_time_dias").alias(TXT["col_lead"]),
            pl.col("existencia_prorrateada").round(0).alias(TXT["risk_stock"]),
            pl.col("forecast_mensual_promedio").round(1).alias(TXT["col_fcst_prom"]),
            pl.col("moh").round(1).alias(TXT["col_moh"]),
            pl.col("demanda_lead_time").round(0).alias(TXT["col_fcst_compra"]),
            pl.col("modelo_ganador").alias(TXT["col_modelo"]),
            pl.col("fecha_ideal_txt").alias(TXT["col_fecha_ideal"]),
            pl.col("dias_para_quiebre").alias(TXT["col_dias_quiebre"]),
            pl.col("cantidad_reorden").round(0).alias(TXT["risk_sugerido"]),
        ])
        leg_col, dl_col = st.columns([4, 1])
        leg_col.caption(TXT["risk_legend_full"].format(hoy=hoy.isoformat()))
        boton_descarga(dl_col, tabla_riesgo, riesgo["unique_id"].to_list(), "riesgo_quiebre.xlsx")

        st.dataframe(
            tabla_riesgo, use_container_width=True, height=420, hide_index=True,
            column_config={TXT["risk_sugerido"]: st.column_config.NumberColumn(help=TXT["risk_sugerido_help"])},
        )

        st.divider()
        st.subheader(TXT["risk_expander"])

        opciones = [f"{s} · {c}" for s, c in zip(riesgo["sku"], riesgo["centro_distribucion"])]
        elegido = st.selectbox(TXT["risk_select_sku"], opciones)
        sku_e, cd_e = [p.strip() for p in elegido.split("·")]
        fila = riesgo.filter((pl.col("sku") == sku_e) & (pl.col("centro_distribucion") == cd_e)).row(0, named=True)

        serie12 = hist.filter(pl.col("unique_id") == fila["unique_id"]).sort("fecha").tail(12)
        figr = go.Figure(go.Bar(
            x=serie12["fecha"].to_list(), y=serie12["cantidad"].to_list(),
            marker_color=ACCENT_CYAN,
        ))
        figr.update_layout(
            **PLOTLY_LAYOUT, height=280, margin=dict(l=10, r=10, t=10, b=10),
            xaxis=axis(), yaxis=axis(title=TXT["risk_sales_yaxis"]),
        )
        st.plotly_chart(figr, use_container_width=True, key=f"chart_{fila['unique_id']}")

# ==================================================================== TAB 3: SKUs en sobre-stock
with tab_overstock:
    st.title(TXT["overstock_header"])
    scope = TXT["scope_all"] if cd_sel == TXT["all"] else cd_sel

    # umbral de sobre-stock: 120 dias (ver estado_inventario en pipeline.py)
    exceso_expr = pl.max_horizontal(
        pl.col("existencia_prorrateada") - pl.col("demanda_diaria_promedio") * 120, pl.lit(0.0)
    )
    sobre = res_f.filter(pl.col("estado_inventario") == estado_sobre).sort("doh", descending=True)
    sobre = sobre.with_columns(exceso_expr.round(0).alias("exceso_unidades"))

    st.caption(TXT["overstock_caption"].format(scope=scope, n=sobre.height))

    search_over = st.text_input("🔎 " + TXT["risk_search"], "", key="overstock_search")
    if search_over:
        sobre = sobre.filter(pl.col("sku").str.contains(f"(?i){search_over}"))

    m1, m2 = st.columns(2)
    m1.metric(TXT["overstock_n_metric"], sobre.height)
    m2.metric(TXT["overstock_total_exceso"], f"{sobre['exceso_unidades'].sum():,.0f}" if sobre.height else "0")

    st.divider()

    if sobre.height == 0:
        st.info(TXT["overstock_no_results"])
    else:
        tabla_sobre = sobre.select([
            pl.col("sku").alias(TXT["col_sku"]), pl.col("centro_distribucion").alias(TXT["col_cd"]),
            pl.col("clasificacion").alias(TXT["col_clase"]),
            pl.col("existencia_prorrateada").round(0).alias(TXT["risk_stock"]),
            pl.col("doh").round(1).alias(TXT["col_doh"]),
            pl.col("moh").round(1).alias(TXT["col_moh"]),
            pl.col("forecast_mensual_promedio").round(1).alias(TXT["col_fcst"]),
            pl.col("modelo_ganador").alias(TXT["col_modelo"]),
            pl.col("exceso_unidades").alias(TXT["col_exceso"]),
        ])

        leg_col, dl_col = st.columns([4, 1])
        leg_col.caption(TXT["overstock_asof_note"].format(hoy=datetime.date.today().isoformat()))
        boton_descarga(dl_col, tabla_sobre, sobre["unique_id"].to_list(), "sobre_stock.xlsx")

        st.dataframe(tabla_sobre, use_container_width=True, height=420, hide_index=True)

        st.divider()
        st.subheader(TXT["risk_expander"])

        opciones_o = [f"{s} · {c}" for s, c in zip(sobre["sku"], sobre["centro_distribucion"])]
        elegido_o = st.selectbox(TXT["risk_select_sku"], opciones_o, key="overstock_select")
        sku_o, cd_o = [p.strip() for p in elegido_o.split("·")]
        fila_o = sobre.filter((pl.col("sku") == sku_o) & (pl.col("centro_distribucion") == cd_o)).row(0, named=True)

        serie12_o = hist.filter(pl.col("unique_id") == fila_o["unique_id"]).sort("fecha").tail(12)
        figo = go.Figure(go.Bar(
            x=serie12_o["fecha"].to_list(), y=serie12_o["cantidad"].to_list(),
            marker_color=ACCENT_ORANGE,
        ))
        figo.update_layout(
            **PLOTLY_LAYOUT, height=280, margin=dict(l=10, r=10, t=10, b=10),
            xaxis=axis(), yaxis=axis(title=TXT["risk_sales_yaxis"]),
        )
        st.plotly_chart(figo, use_container_width=True, key=f"chart_over_{fila_o['unique_id']}")
