"""Piezas compartidas por las páginas de la app: paleta, i18n, CSS y lectura de parquets.

`app.py` es el entry point (st.navigation) y corre antes de cada página; las páginas viven
en `app_pages/`. Todo lo que necesita más de una página vive acá — el resto se queda en la
página que lo usa. No importa streamlit-de-página: no dibuja nada por sí mismo.
"""

import json
from pathlib import Path

import polars as pl
import streamlit as st
from PIL import Image

BASE = Path(__file__).parent

ADI_THRESHOLD = 1.32
CV2_THRESHOLD = 0.49
H = 4

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
        "nav_inicio": "Inicio",
        "nav_forecast": "Forecast",
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
        "log_completo": "Ver log completo",
        "avisos_title": "⚠️ {n} aviso(s) de la última carga",
        "map_help": "Elegí de qué columna de tu CSV sale cada campo:",
        "upload_missing": "Faltan columnas requeridas:",
        "map_placeholder": "— elegir —",
        "map_no_disponible": "— no está en el CSV —",
        "map_ventas_title": "**Ventas — campos obligatorios**",
        "map_inventario_title": "**Inventario — campos obligatorios**",
        "map_inventario_opc": "**Inventario — opcionales**",
        "inv_cd_help": "Si tu inventario indica en qué centro está cada existencia, asignalo acá: "
                       "el stock se matchea directo contra las ventas de ese mismo centro. "
                       "Si lo dejás sin asignar, la existencia del SKU se reparte entre sus "
                       "centros proporcional al histórico de ventas.",
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
        # ---- Landing (app_pages/inicio.py)
        "landing_hero_title": "Cuánto vas a vender y cuánto stock te falta, por SKU y por centro",
        "landing_hero_sub": "Subís tu histórico de ventas y tu inventario. La app pronostica la demanda "
                            "de los próximos {h} meses para cada combinación SKU-centro, elige el modelo "
                            "que mejor le sirve a cada serie y traduce ese pronóstico en días de cobertura, "
                            "riesgo de quiebre y cantidad a reordenar.",
        "landing_cta": "Ir al forecast",
        "landing_metric_series": "Series SKU-centro",
        "landing_metric_skus": "SKUs",
        "landing_metric_cds": "Centros",
        "landing_metric_meses": "Meses de histórico",
        "landing_metric_horizonte": "Horizonte",
        "landing_meses_unit": "meses",
        "landing_metric_riesgo": "En riesgo de quiebre",
        "landing_uses_title": "Para qué sirve",
        "landing_use1_title": "Anticipar la demanda",
        "landing_use1_body": "Un pronóstico mensual por SKU y centro, no un promedio general. "
                             "Cada serie compite entre varios modelos y gana el que menos se equivoca en su propio histórico.",
        "landing_use2_title": "Comprar antes del quiebre",
        "landing_use2_body": "Si la cobertura no llega a cubrir el lead time del proveedor, la combinación "
                             "aparece en riesgo con la fecha ideal de reorden y la cantidad sugerida.",
        "landing_use3_title": "Liberar capital dormido",
        "landing_use3_body": "El sobre-stock se lista con las unidades en exceso sobre 120 días de cobertura: "
                             "qué frenar de comprar y qué mover entre centros.",
        "landing_charts_title": "Así se ve con los datos cargados",
        "landing_chart_fcst_title": "Ejemplo de forecast · {sku} · {cd}",
        "landing_chart_fcst_caption": "Serie de mayor volumen del dataset. Línea sólida = histórico mensual; "
                                      "punteada = {h} meses de forecast del modelo ganador (**{modelo}**).",
        "landing_how_title": "Cómo funciona",
        "landing_step1_title": "1 · Agregación mensual",
        "landing_step1_body": "Tus CSVs se agregan a mes calendario por SKU y centro. Los headers son libres: "
                              "se mapean campo por campo en la pantalla de carga.",
        "landing_step2_title": "2 · Clasificación SBC",
        "landing_step2_body": "Cada serie cae en un cuadrante según cada cuánto se vende (ADI) y cuánto varía "
                              "el tamaño del pedido (CV²): Suave, Errático, Intermitente o Irregular.",
        "landing_step3_title": "3 · Competencia de modelos",
        "landing_step3_body": "Series regulares corren AutoETS, AutoARIMA, Theta y SeasonalNaive; las "
                              "intermitentes corren Croston, TSB y ADIDA. Gana el de menor MASE en backtesting "
                              "con ventanas móviles.",
        "landing_step4_title": "4 · KPIs de inventario",
        "landing_step4_body": "El forecast se cruza con tu existencia: DOH/WOS/MOH, estado (riesgo, normal, "
                              "sobre-stock) y cantidad de reorden redondeada al múltiplo de pack.",
        "landing_no_data": "Todavía no hay resultados calculados. Cargá tus CSVs desde la barra lateral, "
                           "o corré `python pipeline.py` en una terminal.",
    },
    "en": {
        "app_title": "📦 Demand Forecast",
        "app_caption": "Demo — SBC classification + statsforecast (Nixtla)",
        "lang_label": "Language",
        "nav_inicio": "Home",
        "nav_forecast": "Forecast",
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
        "log_completo": "View full log",
        "avisos_title": "⚠️ {n} warning(s) from the last upload",
        "map_help": "Pick which column of your CSV maps to each field:",
        "upload_missing": "Missing required columns:",
        "map_placeholder": "— pick one —",
        "map_no_disponible": "— not in the CSV —",
        "map_ventas_title": "**Sales — required fields**",
        "map_inventario_title": "**Inventory — required fields**",
        "map_inventario_opc": "**Inventory — optional**",
        "inv_cd_help": "If your inventory states which center holds each stock, map it here: "
                       "stock is matched directly against sales from that same center. "
                       "If you leave it unassigned, the SKU's stock is split across its "
                       "centers proportionally to sales history.",
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
        # ---- Landing (app_pages/inicio.py)
        "landing_hero_title": "How much you'll sell and how much stock you're missing, by SKU and center",
        "landing_hero_sub": "Upload your sales history and your inventory. The app forecasts demand for the "
                            "next {h} months for every SKU-center combination, picks the model that fits each "
                            "series best, and turns that forecast into days of coverage, stockout risk and "
                            "reorder quantity.",
        "landing_cta": "Go to forecast",
        "landing_metric_series": "SKU-center series",
        "landing_metric_skus": "SKUs",
        "landing_metric_cds": "Centers",
        "landing_metric_meses": "Months of history",
        "landing_metric_horizonte": "Horizon",
        "landing_meses_unit": "months",
        "landing_metric_riesgo": "At stockout risk",
        "landing_uses_title": "What it's for",
        "landing_use1_title": "Anticipate demand",
        "landing_use1_body": "A monthly forecast per SKU and center, not a blanket average. Every series runs "
                             "a model competition and the one that misses least on its own history wins.",
        "landing_use2_title": "Buy before the stockout",
        "landing_use2_body": "If coverage doesn't reach the supplier's lead time, the combination shows up as "
                             "at risk, with the ideal reorder date and the suggested quantity.",
        "landing_use3_title": "Free up idle capital",
        "landing_use3_body": "Overstock is listed with the units in excess over 120 days of coverage: what to "
                             "stop buying and what to move between centers.",
        "landing_charts_title": "This is how it looks with data loaded",
        "landing_chart_fcst_title": "Forecast example · {sku} · {cd}",
        "landing_chart_fcst_caption": "Highest-volume series in the dataset. Solid line = monthly history; "
                                      "dotted = {h} months of forecast from the winning model (**{modelo}**).",
        "landing_how_title": "How it works",
        "landing_step1_title": "1 · Monthly aggregation",
        "landing_step1_body": "Your CSVs are aggregated to calendar month per SKU and center. Headers are free "
                              "form: you map them field by field on the upload screen.",
        "landing_step2_title": "2 · SBC classification",
        "landing_step2_body": "Every series lands in a quadrant based on how often it sells (ADI) and how much "
                              "order size varies (CV²): Smooth, Erratic, Intermittent or Lumpy.",
        "landing_step3_title": "3 · Model competition",
        "landing_step3_body": "Regular series run AutoETS, AutoARIMA, Theta and SeasonalNaive; intermittent ones "
                              "run Croston, TSB and ADIDA. Lowest MASE in rolling-origin backtesting wins.",
        "landing_step4_title": "4 · Inventory KPIs",
        "landing_step4_body": "The forecast is crossed with your stock: DOH/WOS/MOH, status (risk, normal, "
                              "overstock) and reorder quantity rounded to the pack multiple.",
        "landing_no_data": "No results computed yet. Upload your CSVs from the sidebar, or run "
                           "`python pipeline.py` in a terminal.",
    },
}


def txt():
    """Diccionario de strings del idioma activo. El radio del sidebar escribe st.session_state['lang']."""
    return STRINGS[st.session_state.get("lang", "es")]


def mapas():
    """(estado_map, estado_color, clase_map) para el idioma activo.

    Los datos canónicos del parquet están en español; estos mapas son solo de vista.
    -> identidad en el idioma en que ya están guardados."""
    lang = st.session_state.get("lang", "es")
    estado_map = ESTADO_EN if lang == "en" else {k: k for k in ESTADO_COLOR_ES}
    estado_color = ESTADO_COLOR_EN if lang == "en" else ESTADO_COLOR_ES
    clase_map = CLASE_ES if lang == "es" else {k: k for k in CLASE_COLOR}
    return estado_map, estado_color, clase_map


def cargar_favicon():
    """Recorta assets/intelliforecast.png a cuadrado y lo reduce para el tab del navegador."""
    ruta = BASE / "assets" / "intelliforecast.png"
    if not ruta.exists():
        return "📦"
    im = Image.open(ruta).convert("RGBA")
    lado = min(im.size)
    x0 = (im.width - lado) // 2
    y0 = (im.height - lado) // 2
    return im.crop((x0, y0, x0 + lado, y0 + lado)).resize((64, 64), Image.LANCZOS)


@st.cache_data
def load():
    """(resultados, historico) o (None, None) si el pipeline nunca corrió.

    No invalida por cambios en disco: después de re-correr pipeline.py hay que limpiar
    la cache (st.cache_data.clear(), que es lo que hace el modal de carga)."""
    if not (BASE / "resultados.parquet").exists():
        return None, None
    res = pl.read_parquet(BASE / "resultados.parquet")
    hist = pl.read_parquet(BASE / "historico.parquet")
    return res, hist


def load_dim_config():
    """Dimensiones extra elegidas al subir los CSVs (carga.json, escrito por escribir_carga).
    No cacheado: archivo trivial, se regenera en cada 'Procesar'."""
    ruta = BASE / "carga.json"
    if not ruta.exists():
        return []
    cfg = json.loads(ruta.read_text(encoding="utf-8"))
    return [d for lado in ("ventas", "inventario") for d in cfg.get(lado, {}).get("dimensiones", [])]


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
