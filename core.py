"""Piezas compartidas por las páginas de la app: paleta, i18n, CSS y lectura de parquets.

`app.py` es el entry point (st.navigation) y corre antes de cada página; las páginas viven
en `app_pages/`. Todo lo que necesita más de una página vive acá — el resto se queda en la
página que lo usa. No importa streamlit-de-página: no dibuja nada por sí mismo.
"""

import json
from pathlib import Path

import streamlit as st

BASE = Path(__file__).parent

ADI_THRESHOLD = 1.32
CV2_THRESHOLD = 0.49
H = 4
MIN_PERIODOS = 16   # duplicado de pipeline.py (ahi se deriva de H/STEP_SIZE/N_WINDOWS/MIN_TRAIN)

# Debajo de este ancho la app se bloquea y pide una computadora (ver inject_css). El mensaje va
# en los dos idiomas a proposito: el visitante llega en telefono sin haber tocado el selector,
# y ademas inject_css() corre antes de que app.py fije st.session_state["lang"].
MOBILE_BREAKPOINT = 768
MOBILE_MSG = ("Este dashboard necesita una computadora.\\A Abrilo desde una laptop o desktop."
              "\\A\\A This dashboard needs a computer.\\A Please open it on a laptop or desktop.")

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
    # gris deliberado: "Sin registro" no es un estado del inventario, es ausencia de dato
    "Sin registro": "#7A828E",
}
ESTADO_EN = {"Riesgo de quiebre": "Stockout risk", "Sobre-stock": "Overstock", "Normal": "Normal",
             "Sin registro": "No stock record"}
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
        "reset_filters": "Limpiar",
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
        "error_no_parquet": "No se encontró resultados.parquet. Corre primero:  python pipeline.py",
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
        "forecast_menu_title": "¿Qué querés hacer?",
        "forecast_menu_sub": "Elegí una opción — podés volver a este menú en cualquier momento.",
        "forecast_opt_dashboard_title": "Ver Dashboard con información",
        "forecast_opt_dashboard_body": "Vista general, KPIs, clasificación de demanda y drill-down por SKU.",
        "forecast_opt_dashboard_btn": "Ver Dashboard",
        "forecast_opt_risk_title": "Ver productos cercanos a quiebre de stock",
        "forecast_opt_risk_body": "Listado priorizado por urgencia con días para quiebre, fecha ideal y cantidad a reordenar.",
        "forecast_opt_risk_btn": "Ver quiebres",
        "forecast_opt_over_title": "Ver productos sobrestockeados",
        "forecast_opt_over_body": "Exceso sobre 120 días de cobertura — qué frenar y qué mover entre centros.",
        "forecast_opt_over_btn": "Ver sobrestock",
        "forecast_opt_upload_title": "Quiero subir nuevo forecast",
        "forecast_opt_upload_body": "Cargá nuevos CSVs de ventas e inventario y recalculá el forecast.",
        "forecast_opt_upload_btn": "Subir datos",
        "forecast_back": "← Volver al menú",
        "forecast_upload_title": "Subir nuevo forecast",
        "forecast_upload_body": "Usá el formulario de carga para subir tus archivos. Podés abrirlo desde acá o desde el botón de la barra lateral.",
        "forecast_upload_open": "Abrir formulario de carga",
        "title_overview": "Vista general de inventario",
        "scope_all": "todos los centros",
        "scope_caption": "Ámbito: **{scope}** · {n} combinaciones SKU-CD",
        "doh_avg": "DOH mediano",
        "wos_avg": "WOS mediano",
        "moh_avg": "MOH mediano",
        "risk_metric": "🔴 Riesgo de quiebre",
        "over_metric": "🟣 Sobre-stock",
        "normal_metric": "🟢 Normal",
        "sindato_metric": "⚪ Sin registro",
        "sindato_help": "Combinaciones con ventas pero sin dato de existencia en el archivo de inventario. No se calculan KPIs: no se sabe si están surtidas.",
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
        "cobertura_caption": "{largas:,} series tienen ≥{min} meses de historia y usan un modelo ajustado. Las otras **{cortas:,} ({pct:.0f}%) son series cortas**: su forecast repite el último mes, no es un modelo.",
        "criticos_title": "SKUs críticos — riesgo de quiebre y sobre-stock",
        "criticos_caption": "{n} combinaciones fuera de estado Normal. Tabla ordenable — clic en encabezados.",
        "export_button": "Descargar datos de reporte e Histórico de Venta",
        "col_sku": "SKU", "col_cd": "CD", "col_clase": "Clasificación", "col_estado": "Estado",
        "col_existencia": "Existencia", "col_fcst": "Fcst. mensual", "col_doh": "DOH", "col_wos": "WOS",
        "col_lead": "Lead time (d)", "col_reorden": "Reorden sugerido", "col_modelo": "Modelo", "col_mase": "MASE",
        "col_moh": "MOH", "col_fcst_compra": "Forecast de compra", "col_fecha_ideal": "Fecha ideal reorden",
        "col_motivo": "Motivo",
        "motivo_sin_demanda": "Sin demanda proyectada",
        "motivo_cobertura": "Cobertura > 120 días",
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
        # ---- Landing (app_pages/inicio.py) — comercial
        "landing_hero_title": "Mirá fácil cuánto vas a vender, cuánto stock te falta y cuánto te sobra",
        "landing_hero_sub": "Subís tu histórico de ventas y tu inventario. La app pronostica la demanda "
                            "de los próximos {h} meses para cada combinación SKU-centro, elige el modelo "
                            "que mejor le sirve a cada serie y traduce ese pronóstico en días de cobertura, "
                            "riesgo de quiebre y cantidad a reordenar.",
        "landing_hero_badge": "Forecast mensual · KPIs de inventario · Reposición sugerida",
        "landing_cta": "Ver forecast ahora",
        "landing_cta_sub": "Sin instalar nada — tus CSVs, tu forecast en minutos",
        "landing_dialog_title": "Un momento antes de entrar",
        "landing_dialog_body": "El dashboard puede tardar unos segundos en abrir: al entrar se cargan "
                               "los modelos y los resultados de todas las combinaciones SKU-centro.",
        "landing_dialog_tip": "Es solo la primera vez — después navegás entre vistas sin espera.",
        "landing_dialog_confirm": "Entendido, ver forecast",
        "landing_pain_title": "¿Te suena familiar?",
        "landing_pain_sub": "Si alguna de estas te describe, IntelliForecast te ahorra horas por semana:",
        "landing_pain_q1_title": "¿Te topas con quiebres de stock?",
        "landing_pain_q1_body": "Te enterás tarde, perdés ventas y clientes. La app alerta con semanas de anticipación "
                                "qué SKU-centro se queda sin cobertura y cuándo reordenar.",
        "landing_pain_q2_title": "¿Te enredás con múltiples productos a forecastear?",
        "landing_pain_q2_body": "Cientos de combinaciones SKU-centro, cada una con su estacionalidad. "
                                "Cada serie compite entre 7 modelos y gana el que menos se equivoca — sin Excel manual.",
        "landing_pain_q3_title": "¿Querés liberar tiempo a tu equipo?",
        "landing_pain_q3_body": "Dejan de armar planillas y pasan a decidir: qué comprar, qué frenar y qué mover entre centros. "
                                "El forecast y los KPIs salen listos para compartir.",
        "landing_benefits_title": "Qué obtienes",
        "landing_benefits_sub": "Del histórico al plan de compra, sin pasos manuales en el medio.",
        "landing_benefit1_title": "Forecast por SKU y centro",
        "landing_benefit1_body": "Pronóstico mensual a 4 meses, uno por combinación. No es un promedio general: cada serie "
                                 "elige su mejor modelo por MASE en backtesting.",
        "landing_benefit2_title": "Alertas de quiebre con fecha y cantidad",
        "landing_benefit2_body": "Si la cobertura (DOH) no cubre el lead time, aparece en riesgo con días para el quiebre, "
                                 "fecha ideal de reorden y cantidad redondeada al pack del proveedor.",
        "landing_benefit3_title": "Sobre-stock visible y accionable",
        "landing_benefit3_body": "Lista ordenada por exceso sobre 120 días de cobertura: qué dejar de comprar y dónde liberar capital dormido.",
        "landing_benefit4_title": "Dashboard + Excel listo para comprar",
        "landing_benefit4_body": "Vista general, riesgo y sobre-stock en 3 pestañas, con filtros y descarga en Excel (KPIs + histórico 24m).",
        "landing_how_title": "Cómo funciona",
        "landing_how_lead": "Subí tus datos, ¡nosotros hacemos el resto!",
        "landing_how_sub": "4 pasos, sin código. Tus headers no tienen que coincidir: los mapeás en la carga.",
        "landing_step1_title": "1 · Subís tus CSVs",
        "landing_step1_body": "Ventas históricas e inventario, con cualquier nombre de columna. Mapeás cada campo y eliges formatos en un modal.",
        "landing_step2_title": "2 · Clasificamos la demanda",
        "landing_step2_body": "Cada serie cae en Suave / Errático / Intermitente / Irregular (SBC) según frecuencia y variabilidad.",
        "landing_step3_title": "3 · Compiten los modelos",
        "landing_step3_body": "Regulares: AutoETS, AutoARIMA, Theta, SeasonalNaive. Intermitentes: Croston, TSB, ADIDA. Gana el de menor error.",
        "landing_step4_title": "4 · Traducimos a inventario",
        "landing_step4_body": "Cruzamos forecast con existencia: DOH/WOS/MOH, estado y reposición sugerida (1.5× lead time, múltiplo de pack).",
        "landing_dashboard_title": "Así se ve el dashboard",
        "landing_dashboard_sub": "Tres vistas que tu equipo puede usar el mismo día. Abajo, el ejemplo real del demo.",
        "landing_dashboard_caption": "Vista general con clasificación de demanda, estado de inventario y tabla de críticos — filtros por centro, proveedor y categoría.",
        "landing_trust_title": "Hecho para equipos que compran todos los meses",
        "landing_trust_body": "Corrido sobre datos reales de venta e inventario. Mismos números si lo corres local con `python pipeline.py` o desde la app.",
        # legacy (compat, ya no usados en la nueva landing pero los dejamos por si otra rama los referencia)
        "landing_metric_series": "Series SKU-centro",
        "landing_metric_skus": "SKUs",
        "landing_metric_cds": "Centros",
        "landing_metric_meses": "Meses de histórico",
        "landing_metric_horizonte": "Horizonte",
        "landing_meses_unit": "meses",
        "landing_metric_riesgo": "En riesgo de quiebre",
        "landing_uses_title": "Para qué sirve",
        "landing_use1_title": "Anticipar la demanda",
        "landing_use1_body": "Un pronóstico mensual por SKU y centro, no un promedio general.",
        "landing_use2_title": "Comprar antes del quiebre",
        "landing_use2_body": "Si la cobertura no llega a cubrir el lead time, la combinación aparece en riesgo.",
        "landing_use3_title": "Liberar capital dormido",
        "landing_use3_body": "El sobre-stock se lista con las unidades en exceso sobre 120 días.",
        "landing_charts_title": "Así se ve con los datos cargados",
        "landing_chart_fcst_title": "Ejemplo de forecast · {sku} · {cd}",
        "landing_chart_fcst_caption": "Serie de mayor volumen del dataset.",
        "landing_hero_badge": "🚀 Análisis inteligente de demanda",
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
        "reset_filters": "Clear",
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
        "error_no_parquet": "No resultados.parquet found. Run first:  python pipeline.py",
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
        "forecast_menu_title": "What do you want to do?",
        "forecast_menu_sub": "Pick an option — you can return to this menu anytime.",
        "forecast_opt_dashboard_title": "View Dashboard with insights",
        "forecast_opt_dashboard_body": "Overview, KPIs, demand classification and SKU drill-down.",
        "forecast_opt_dashboard_btn": "View Dashboard",
        "forecast_opt_risk_title": "View products close to stockout",
        "forecast_opt_risk_body": "List ranked by urgency with days to stockout, ideal date and reorder qty.",
        "forecast_opt_risk_btn": "View stockouts",
        "forecast_opt_over_title": "View overstocked products",
        "forecast_opt_over_body": "Excess over 120 days of coverage — what to pause and what to move.",
        "forecast_opt_over_btn": "View overstock",
        "forecast_opt_upload_title": "Upload new forecast",
        "forecast_opt_upload_body": "Upload new sales & inventory CSVs and recompute the forecast.",
        "forecast_opt_upload_btn": "Upload data",
        "forecast_back": "← Back to menu",
        "forecast_upload_title": "Upload new forecast",
        "forecast_upload_body": "Use the upload form to submit your files. You can open it here or from the sidebar button.",
        "forecast_upload_open": "Open upload form",
        "title_overview": "Inventory overview",
        "scope_all": "all distribution centers",
        "scope_caption": "Scope: **{scope}** · {n} SKU-DC combinations",
        "doh_avg": "Median DOH",
        "wos_avg": "Median WOS",
        "moh_avg": "Median MOH",
        "risk_metric": "🔴 Stockout risk",
        "over_metric": "🟣 Overstock",
        "normal_metric": "🟢 Normal",
        "sindato_metric": "⚪ No stock record",
        "sindato_help": "Combinations with sales but no stock figure in the inventory file. No KPIs are computed: there is no way to tell whether they are stocked.",
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
        "cobertura_caption": "{largas:,} series have ≥{min} months of history and use a fitted model. The other **{cortas:,} ({pct:.0f}%) are short series**: their forecast just repeats the last month, it is not a model.",
        "criticos_title": "Critical SKUs — stockout risk and overstock",
        "criticos_caption": "{n} combinations outside Normal status. Sortable table — click headers.",
        "export_button": "Download report data and Sales History",
        "col_sku": "SKU", "col_cd": "DC", "col_clase": "Classification", "col_estado": "Status",
        "col_existencia": "Stock", "col_fcst": "Monthly fcst.", "col_doh": "DOH", "col_wos": "WOS",
        "col_lead": "Lead time (d)", "col_reorden": "Suggested reorder", "col_modelo": "Model", "col_mase": "MASE",
        "col_moh": "MOH", "col_fcst_compra": "Purchase forecast", "col_fecha_ideal": "Ideal reorder date",
        "col_motivo": "Reason",
        "motivo_sin_demanda": "No projected demand",
        "motivo_cobertura": "Coverage > 120 days",
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
        # ---- Landing (app_pages/inicio.py) — commercial
        "landing_hero_title": "See at a glance how much you'll sell, how much stock you're short and how much you have to spare",
        "landing_hero_sub": "Upload your sales history and your inventory. The app forecasts demand for the "
                             "next {h} months for every SKU-center combination, picks the model that fits each "
                             "series best, and turns that forecast into days of coverage, stockout risk and "
                             "reorder quantity.",
        "landing_hero_badge": "Monthly forecast · Inventory KPIs · Suggested reorder",
        "landing_cta": "Go to forecast",
        "landing_cta_sub": "No setup — your CSVs, your forecast in minutes",
        "landing_dialog_title": "One moment before you go in",
        "landing_dialog_body": "The dashboard may take a few seconds to open: entering loads the "
                               "models and the results for every SKU-center combination.",
        "landing_dialog_tip": "Only the first time — after that you move between views with no wait.",
        "landing_dialog_confirm": "Got it, show forecast",
        "landing_pain_title": "Does this sound familiar?",
        "landing_pain_sub": "If any of these describe you, IntelliForecast saves hours every week:",
        "landing_pain_q1_title": "Running into stockouts?",
        "landing_pain_q1_body": "You find out too late, lose sales and customers. The app flags which SKU-center "
                                "will run out, with weeks of lead time and the ideal reorder date.",
        "landing_pain_q2_title": "Juggling hundreds of SKUs to forecast?",
        "landing_pain_q2_body": "Every SKU-center has its own seasonality. Each series competes across 7 models "
                                "and the most accurate wins — no manual Excel.",
        "landing_pain_q3_title": "Want to free up your team's time?",
        "landing_pain_q3_body": "They stop building spreadsheets and start deciding: what to buy, what to pause, "
                                "and what to move between centers. Forecast and KPIs come ready to share.",
        "landing_benefits_title": "What you get",
        "landing_benefits_sub": "From history to purchase plan, with no manual steps in between.",
        "landing_benefit1_title": "Forecast per SKU and center",
        "landing_benefit1_body": "4-month monthly forecast, one per combination. Not a blanket average: each series "
                                 "picks its best model by MASE in backtesting.",
        "landing_benefit2_title": "Stockout alerts with date & quantity",
        "landing_benefit2_body": "If coverage (DOH) doesn't cover lead time, it shows as at-risk with days to stockout, "
                                 "ideal reorder date and pack-rounded quantity.",
        "landing_benefit3_title": "Visible, actionable overstock",
        "landing_benefit3_body": "Ranked list by excess over 120 days of coverage: what to stop buying and where to free idle capital.",
        "landing_benefit4_title": "Dashboard + Excel ready to buy",
        "landing_benefit4_body": "Overview, risk and overstock in 3 tabs, with filters and Excel download (KPIs + 24m history).",
        "landing_how_title": "How it works",
        "landing_how_lead": "Upload your data, we do the rest!",
        "landing_how_sub": "4 steps, no code. Your headers don't need to match — you map them on upload.",
        "landing_step1_title": "1 · Upload your CSVs",
        "landing_step1_body": "Sales history and inventory, with any column names. Map each field and pick date formats in a modal.",
        "landing_step2_title": "2 · We classify demand",
        "landing_step2_body": "Each series lands in Smooth / Erratic / Intermittent / Lumpy (SBC) by frequency and variability.",
        "landing_step3_title": "3 · Models compete",
        "landing_step3_body": "Regular: AutoETS, AutoARIMA, Theta, SeasonalNaive. Intermittent: Croston, TSB, ADIDA. Lowest error wins.",
        "landing_step4_title": "4 · We translate to inventory",
        "landing_step4_body": "Forecast meets stock: DOH/WOS/MOH, status and suggested reorder (1.5× lead time, pack multiple).",
        "landing_dashboard_title": "Dashboard preview",
        "landing_dashboard_sub": "Three views your team can use the same day. Below, the real demo example.",
        "landing_dashboard_caption": "Overview with demand classification, inventory status and criticals table — filters by center, supplier and category.",
        "landing_trust_title": "Built for teams that buy every month",
        "landing_trust_body": "Run on real sales and inventory data. Same numbers whether you run `python pipeline.py` locally or from the app.",
        # legacy compat
        "landing_metric_series": "SKU-center series",
        "landing_metric_skus": "SKUs",
        "landing_metric_cds": "Centers",
        "landing_metric_meses": "Months of history",
        "landing_metric_horizonte": "Horizon",
        "landing_meses_unit": "months",
        "landing_metric_riesgo": "At stockout risk",
        "landing_uses_title": "What it's for",
        "landing_use1_title": "Anticipate demand",
        "landing_use1_body": "A monthly forecast per SKU and center, not a blanket average.",
        "landing_use2_title": "Buy before the stockout",
        "landing_use2_body": "If coverage doesn't reach lead time, the combination shows as at risk.",
        "landing_use3_title": "Free up idle capital",
        "landing_use3_body": "Overstock is listed with units in excess over 120 days.",
        "landing_charts_title": "This is how it looks with data loaded",
        "landing_chart_fcst_title": "Forecast example · {sku} · {cd}",
        "landing_chart_fcst_caption": "Highest-volume series in the dataset.",
        "landing_hero_badge": "🚀 Intelligent demand analysis",
        "landing_no_data": "No results computed yet. Upload your CSVs from the sidebar, or run "
                           "`python pipeline.py` in a terminal.",
    },
}


def txt():
    """Diccionario de strings del idioma activo. El radio del sidebar escribe st.session_state['lang']."""
    return STRINGS[st.session_state.get("lang", "en")]


def mapas():
    """(estado_map, estado_color, clase_map) para el idioma activo.

    Los datos canónicos del parquet están en español; estos mapas son solo de vista.
    -> identidad en el idioma en que ya están guardados."""
    lang = st.session_state.get("lang", "en")
    estado_map = ESTADO_EN if lang == "en" else {k: k for k in ESTADO_COLOR_ES}
    estado_color = ESTADO_COLOR_EN if lang == "en" else ESTADO_COLOR_ES
    clase_map = CLASE_ES if lang == "es" else {k: k for k in CLASE_COLOR}
    return estado_map, estado_color, clase_map


def cargar_favicon():
    """Recorta assets/intelliforecast.png a cuadrado y lo reduce para el tab del navegador."""
    ruta = BASE / "assets" / "intelliforecast.png"
    if not ruta.exists():
        return "📦"
    from PIL import Image

    im = Image.open(ruta).convert("RGBA")
    lado = min(im.size)
    x0 = (im.width - lado) // 2
    y0 = (im.height - lado) // 2
    return im.crop((x0, y0, x0 + lado, y0 + lado)).resize((64, 64), Image.LANCZOS)


@st.cache_data
def load():
    """(resultados, historico) o (None, None) si el pipeline nunca corrió.

    No invalida por cambios en disco: después de re-correr pipeline.py hay que limpiar
    la cache (st.cache_data.clear(), que es lo que hace el modal de carga).
    Import lazy de polars para no penalizar la landing (que no lo necesita)."""
    import polars as pl

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

        /* El dashboard no funciona en pantalla de telefono: 7 filtros, tablas de 11 columnas y
           scatter de 21k puntos. En vez de servir una version rota, se bloquea y se pide una
           computadora. Media query y no user-agent: no hay que adivinar el dispositivo, y una
           ventana de escritorio angosta se arregla ensanchandola. */
        @media (max-width: {MOBILE_BREAKPOINT}px) {{
            [data-testid="stAppViewContainer"], section[data-testid="stSidebar"],
            [data-testid="stSidebarCollapsedControl"], header, footer {{
                display: none !important;
            }}
            body::before {{
                content: "{MOBILE_MSG}";
                white-space: pre-line;
                position: fixed;
                inset: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
                padding: 2rem;
                background: {BG_DARK};
                color: {TEXT_LIGHT};
                font-family: 'JetBrains Mono', monospace;
                font-size: 1rem;
                line-height: 1.6;
                z-index: 9999;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
