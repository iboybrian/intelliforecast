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

# Duplicado de pipeline.REQ y de las listas de app.py. La landing los muestra y no puede
# importar pipeline (arrastra statsforecast). Si cambian allá, cambiar acá.
COLUMNAS_VENTAS_REQ = ("sku", "centro_distribucion", "fecha", "cantidad")
COLUMNAS_INVENTARIO_REQ = ("sku", "existencia")
COLUMNAS_INVENTARIO_OPC = ("centro_distribucion", "pack", "lead_time_dias")
DEMO_DIR = BASE / "demo"

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
        "landing_hero_sub": "Subís tu histórico de ventas y tu inventario. El algoritmo pronostica la demanda "
                            "de los próximos meses para cada combinación SKU-centro, elige el modelo "
                            "que mejor le sirve a cada serie y te dice cuándo un producto está en sobre-stock, "
                            "cuándo está cerca de un quiebre y cuánto reordenar.",
        "landing_hero_badge": "Forecast mensual · KPIs de inventario · Reposición sugerida",
        "landing_cta": "Probar demo",
        "landing_cta_sub": "Datos de muestra, sin cuenta. Con el acceso beta cargás tus propios archivos.",
        "landing_dialog_title": "Un momento antes de entrar",
        "landing_dialog_body": "El dashboard puede tardar unos segundos en abrir: al entrar se cargan "
                               "los modelos y los resultados de todas las combinaciones SKU-centro.",
        "landing_dialog_tip": "Es solo la primera vez — después navegás entre vistas sin espera.",
        "landing_dialog_confirm": "Entendido, ver forecast",
        "auth_titulo": "Acceso de clientes",
        "auth_usuario": "Usuario",
        "auth_password": "Contraseña",
        "auth_entrar": "Entrar",
        "auth_error": "Usuario o contraseña incorrectos.",
        "auth_bloqueado": "Demasiados intentos. Probá de nuevo en {s} s.",
        "auth_sin_perfiles": "No hay perfiles cargados todavía. Creá uno y pegalo en los secrets:",
        "auth_bienvenida": "Listo, {u}.",
        "auth_continuar": "Continuar a tu dashboard",
        "auth_sesion": "Sesión: {u}",
        "auth_salir": "Cerrar sesión",
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
        "landing_step1_body": "Ventas históricas e inventario, con cualquier nombre de columna. Mapeás cada campo y eliges formatos en un modal. "
                              "No hace falta tocar el archivo antes: el mapeo se guarda y se reusa la próxima vez que subís datos.",
        "landing_step2_title": "2 · Clasificamos la demanda",
        "landing_step2_body": "Cada serie cae en Suave / Errático / Intermitente / Irregular (SBC) según frecuencia y variabilidad. "
                              "Esa clasificación decide qué familia de modelos compite después: no es lo mismo pronosticar algo que vendés "
                              "todos los días que un repuesto que se pide una vez cada dos meses.",
        "landing_step3_title": "3 · Compiten los modelos",
        "landing_step3_body": "Regulares: AutoETS, AutoARIMA, Theta, SeasonalNaive. Intermitentes: Croston, TSB, ADIDA. Gana el de menor error. "
                              "El error se mide con backtesting real, corriendo el modelo sobre meses que ya pasaron y comparando contra lo que "
                              "efectivamente se vendió — no una promesa teórica.",
        "landing_step4_title": "4 · Traducimos a inventario",
        "landing_step4_body": "Cruzamos forecast con existencia: DOH/WOS/MOH, estado y reposición sugerida (1.5× lead time, múltiplo de pack). "
                              "El resultado es una cantidad concreta a pedir, no solo una alerta: sabés cuánto comprar y de qué SKU, listo para "
                              "mandarle al proveedor.",
        "landing_dashboard_title": "Así se ve el dashboard",
        "landing_dashboard_sub": "Tres vistas que tu equipo puede usar el mismo día. Las capturas ilustran el producto; el demo interactivo usa datos sintéticos.",
        "landing_dashboard_caption": "Vista general con clasificación de demanda, estado de inventario y tabla de críticos — filtros por centro, proveedor y categoría.",
        "landing_trust_title": "Hecho para equipos que compran todos los meses",
        "landing_trust_body": "El demo público corre sobre datos sintéticos, claramente ficticios. Con acceso de cliente, el forecast usa tus propias ventas e inventario.",
        "landing_hero_cta_start": "Empezar a pronosticar",
        "landing_hero_cta_contact": "Hablar con ventas",
        "landing_why_title": "Por qué IntelliForecast",
        "landing_why_r1_title": "Anticipás el quiebre antes de que pase",
        "landing_why_r1_body": "La app avisa con semanas de anticipación qué SKU-centro se queda sin cobertura y cuándo reordenar — no te enterás cuando ya perdiste la venta.",
        "landing_why_r2_title": "Un modelo por serie, no un promedio general",
        "landing_why_r2_body": "Cientos de combinaciones SKU-centro, cada una compite entre 7 modelos de forecast y gana el que menos se equivoca en backtesting.",
        "landing_why_r3_title": "Tu equipo deja el Excel y pasa a decidir",
        "landing_why_r3_body": "El forecast y los KPIs salen listos para compartir: qué comprar, qué frenar y qué mover entre centros.",
        "landing_what_side_title": "Pensado para el equipo, no solo para el dato",
        "landing_what_side_b1": "Compradores y planners ven lo mismo, sin planillas paralelas.",
        "landing_what_side_b2": "Cada alerta trae fecha, cantidad y motivo — lista para actuar.",
        "landing_what_side_b3": "Exportás a Excel en un clic para la reunión de compras.",
        "landing_services_title": "Nuestras soluciones",
        "landing_services_sub": "Dos formas de tener el forecast corriendo — vos elegís el nivel de involucramiento.",
        "landing_service_pro_title": "Acceso a IntelliForecast Pro",
        "landing_service_pro_body": "Subís tus CSVs y corrés el dashboard vos mismo, self-service, con soporte para la carga inicial.",
        "landing_service_pro_cta": "Empezar",
        "landing_service_inhouse_title": "Demand Planning in-house",
        "landing_service_inhouse_body": "Nuestro equipo implementa y opera el forecasting dentro de tu empresa: integración con tus sistemas y acompañamiento continuo.",
        "landing_service_inhouse_cta": "Hablar con ventas",
        "landing_contact_title": "Sé tester beta",
        "landing_contact_pending": "Formulario en configuración — mientras tanto, escribinos.",
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
        "landing_no_data": "Todavía no hay resultados calculados. Con una cuenta de cliente, la carga de CSVs está en el forecast.",
        "demo_cta": "Probar demo",
        "demo_beta_cta": "Sé tester beta",
        "demo_client_cta": "Ya tengo acceso",
        "demo_login_hint": "¿Sin usuario? Podés recorrer el forecast completo con datos de muestra.",
        "demo_sidebar": "Viendo el demo con datos sintéticos",
        "demo_salir": "Salir del demo",
        "demo_banner_title": "Demo con datos sintéticos",
        "demo_banner": "Los SKU, centros y proveedores de esta vista son ficticios. No hay datos de una empresa real.",
        "demo_upload_title": "La carga es parte del acceso de cliente",
        "demo_upload_body": "En el demo no se pueden subir archivos: eso reemplazaría los datos de muestra. Pedí acceso beta para probar con los tuyos.",
        "error_no_demo": "No se encontró el demo de muestra. Falta demo/resultados.parquet.",
        "feedback_btn": "Enviar comentarios",
        "feedback_title": "¿Qué tal te fue?",
        "feedback_hint": "Contanos qué funcionó y qué no. Llega al mismo lugar que el pedido de acceso.",
        "feedback_worked": "Qué funcionó",
        "feedback_didnt": "Qué no funcionó",
        "feedback_email": "Email (opcional, si querés que te respondamos)",
        "feedback_send": "Enviar",
        "feedback_need_one": "Contanos al menos una cosa que funcionó o que no.",
        "form_intro": "Contanos de tu operación y te escribimos para el acceso de tester, o para conversar con el equipo.",
        "form_nombre": "Nombre",
        "form_email": "Email",
        "form_empresa": "Empresa",
        "form_rol": "Rol",
        "form_industria": "Industria",
        "form_skus": "Cantidad aproximada de SKUs",
        "form_centros": "Centros o bodegas (aproximado)",
        "form_mensaje": "Mensaje",
        "form_enviar": "Enviar",
        "form_ok": "Recibimos tu mensaje. Te escribimos pronto.",
        "form_fallback": "No hay un envío automático configurado. Escribinos a {email} — tus respuestas quedan abajo para copiar.",
        "form_fallback_fail": "No pudimos entregar el mensaje. Escribinos a {email} — tus respuestas quedan abajo para copiar.",
        "form_unconfigured": "El formulario no tiene destino ni email de contacto. Quien administra la app tiene que configurar [contact] en los secrets.",
        "form_mailto": "Abrir email",
        "form_error_email": "Ingresá un email válido.",
        "form_error_required": "Completá nombre, email y empresa.",
        "columns_title": "Qué columnas esperamos",
        "columns_sub": "El forecast usa estos campos. Si tus headers se llaman distinto, los mapeás al subir el archivo.",
        "columns_sales_title": "**Ventas históricas — obligatorias**",
        "columns_inv_title": "**Inventario — obligatorias**",
        "columns_inv_opt_title": "**Inventario — opcionales**",
        "columns_extra": "Cualquier otra columna (por ejemplo proveedor o categoría) viaja como dimensión y se puede filtrar. En las plantillas están de muestra.",
        "columns_units": "La existencia tiene que estar en las mismas unidades que la cantidad vendida.",
        "columns_dates": "Fechas aceptadas: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, YYYY-MM, o detección automática.",
        "columns_blank": "Una existencia en blanco no es cero: esa combinación queda como Sin registro, fuera de la lista de quiebre. La última fila de la plantilla de inventario lo muestra.",
        "columns_download_sales": "Descargar plantilla de ventas",
        "columns_download_inv": "Descargar plantilla de inventario",
        "colhelp_sku": "Identificador del producto.",
        "colhelp_cd_ventas": "Centro, tienda o bodega donde se vendió.",
        "colhelp_fecha": "Fecha de la venta. Puede ser día, semana o mes: se agrega a mes antes de pronosticar.",
        "colhelp_cantidad": "Unidades vendidas en ese período. Los negativos entran como devoluciones.",
        "colhelp_existencia": "Unidades en stock hoy.",
        "colhelp_cd_inv": "Si viene, el stock se cruza con las ventas de ese mismo centro. Si no, el stock del SKU se reparte entre sus centros según el histórico.",
        "colhelp_pack": "Múltiplo de compra. Si la columna no está, se usa 1.",
        "colhelp_lead": "Días de reposición. Si la columna no está, se usan 30. Un lead time inventado cambia el estado de inventario.",
                           

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
                             "next months for every SKU-center combination, picks the model that fits each "
                             "series best, and gives you a report on when it's in overstock, when it's close to stockout and how much you should reorder.",
        "landing_hero_badge": "Monthly forecast · Inventory KPIs · Suggested reorder",
        "landing_cta": "Try the demo",
        "landing_cta_sub": "Sample data, no account. Beta access is how you load your own files.",
        "landing_dialog_title": "One moment before you go in",
        "landing_dialog_body": "The dashboard may take a few seconds to open: entering loads the "
                               "models and the results for every SKU-center combination.",
        "landing_dialog_tip": "Only the first time — after that you move between views with no wait.",
        "landing_dialog_confirm": "Got it, show forecast",
        "auth_titulo": "Client access",
        "auth_usuario": "Username",
        "auth_password": "Password",
        "auth_entrar": "Sign in",
        "auth_error": "Wrong username or password.",
        "auth_bloqueado": "Too many attempts. Try again in {s} s.",
        "auth_sin_perfiles": "No profiles configured yet. Create one and paste it into your secrets:",
        "auth_bienvenida": "You're in, {u}.",
        "auth_continuar": "Continue to your dashboard",
        "auth_sesion": "Signed in: {u}",
        "auth_salir": "Sign out",
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
        "landing_step1_body": "Sales history and inventory, with any column names. Map each field and pick date formats in a modal. "
                              "No need to touch the file beforehand: the mapping is saved and reused the next time you upload data.",
        "landing_step2_title": "2 · We classify demand",
        "landing_step2_body": "Each series lands in Smooth / Erratic / Intermittent / Lumpy (SBC) by frequency and variability. "
                              "That classification decides which family of models competes next: forecasting something you sell every day "
                              "isn't the same as a spare part ordered once every two months.",
        "landing_step3_title": "3 · Models compete",
        "landing_step3_body": "Regular: AutoETS, AutoARIMA, Theta, SeasonalNaive. Intermittent: Croston, TSB, ADIDA. Lowest error wins. "
                              "The error comes from real backtesting, running the model over months that already happened and checking it "
                              "against what actually sold — not a theoretical promise.",
        "landing_step4_title": "4 · We translate to inventory",
        "landing_step4_body": "Forecast meets stock: DOH/WOS/MOH, status and suggested reorder (1.5× lead time, pack multiple). "
                              "The result is a concrete quantity to order, not just an alert: you know how much to buy and for which SKU, "
                              "ready to send to the supplier.",
        "landing_dashboard_title": "Dashboard preview",
        "landing_dashboard_sub": "Three views your team can use the same day. The screenshots illustrate the product; the interactive demo uses synthetic data.",
        "landing_dashboard_caption": "Overview with demand classification, inventory status and criticals table — filters by center, supplier and category.",
        "landing_trust_title": "Built for teams that buy every month",
        "landing_trust_body": "The public demo runs on clearly fictional sample data. With client access, the forecast uses your own sales and inventory.",
        "landing_hero_cta_start": "Start forecasting",
        "landing_hero_cta_contact": "Contact sales",
        "landing_why_title": "Why IntelliForecast",
        "landing_why_r1_title": "Catch the stockout before it happens",
        "landing_why_r1_body": "The app flags weeks ahead which SKU-center will run out of coverage and when to reorder — no finding out after the sale is already lost.",
        "landing_why_r2_title": "One model per series, not a blanket average",
        "landing_why_r2_body": "Hundreds of SKU-center combinations, each competing across 7 forecast models — the most accurate wins in backtesting.",
        "landing_why_r3_title": "Your team trades spreadsheets for decisions",
        "landing_why_r3_body": "Forecast and KPIs come ready to share: what to buy, what to pause, and what to move between centers.",
        "landing_what_side_title": "Built for the team, not just the data",
        "landing_what_side_b1": "Buyers and planners see the same numbers — no parallel spreadsheets.",
        "landing_what_side_b2": "Every alert carries a date, quantity and reason — ready to act on.",
        "landing_what_side_b3": "Export to Excel in one click for the buying meeting.",
        "landing_services_title": "Our solutions",
        "landing_services_sub": "Two ways to get the forecast running — pick the level of involvement you want.",
        "landing_service_pro_title": "Access to IntelliForecast Pro",
        "landing_service_pro_body": "Upload your CSVs and run the dashboard yourself, self-service, with support for the initial setup.",
        "landing_service_pro_cta": "Get started",
        "landing_service_inhouse_title": "In-house Demand Planning",
        "landing_service_inhouse_body": "Our team implements and runs the forecasting inside your company: integration with your systems and ongoing support.",
        "landing_service_inhouse_cta": "Contact sales",
        "landing_contact_title": "Become a beta tester",
        "landing_contact_pending": "Form is being set up — reach out to us in the meantime.",
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
        "landing_no_data": "No results computed yet. With a client account, CSV upload lives on the forecast page.",
        "demo_cta": "Try the demo",
        "demo_beta_cta": "Become a beta tester",
        "demo_client_cta": "I already have access",
        "demo_login_hint": "No account? You can walk through the full forecast on sample data.",
        "demo_sidebar": "Viewing the demo on synthetic data",
        "demo_salir": "Leave demo",
        "demo_banner_title": "Demo on synthetic data",
        "demo_banner": "The SKUs, centers and suppliers in this view are fictional. There is no real company data here.",
        "demo_upload_title": "Upload is part of client access",
        "demo_upload_body": "The demo can't accept file uploads — that would replace the sample. Request beta access to try your own files.",
        "error_no_demo": "The sample demo is missing. demo/resultados.parquet was not found.",
        "feedback_btn": "Send feedback",
        "feedback_title": "How did it go?",
        "feedback_hint": "Tell us what worked and what didn't. It goes to the same place as an access request.",
        "feedback_worked": "What worked",
        "feedback_didnt": "What didn't",
        "feedback_email": "Email (optional, if you want a reply)",
        "feedback_send": "Send",
        "feedback_need_one": "Tell us at least one thing that worked or didn't.",
        "form_intro": "Tell us about your operation and we'll write back about tester access, or to talk with the team.",
        "form_nombre": "Name",
        "form_email": "Email",
        "form_empresa": "Company",
        "form_rol": "Role",
        "form_industria": "Industry",
        "form_skus": "Approximate number of SKUs",
        "form_centros": "Centers or warehouses (approximate)",
        "form_mensaje": "Message",
        "form_enviar": "Send",
        "form_ok": "We got your message. We'll write back soon.",
        "form_fallback": "Automatic delivery isn't configured. Email us at {email} — your answers are below if you want to paste them.",
        "form_fallback_fail": "We couldn't deliver the message. Email us at {email} — your answers are below if you want to paste them.",
        "form_unconfigured": "The form has no destination and no contact email. Whoever runs the app needs to set [contact] in secrets.",
        "form_mailto": "Open email",
        "form_error_email": "Enter a valid email.",
        "form_error_required": "Name, email and company are required.",
        "columns_title": "Which columns we expect",
        "columns_sub": "The forecast uses these fields. If your headers differ, you map them when you upload.",
        "columns_sales_title": "**Sales history — required**",
        "columns_inv_title": "**Inventory — required**",
        "columns_inv_opt_title": "**Inventory — optional**",
        "columns_extra": "Any other column (for example supplier or category) travels as a dimension and can be filtered. The templates include a couple as examples.",
        "columns_units": "On-hand stock has to be in the same units as quantity sold.",
        "columns_dates": "Accepted dates: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, YYYY-MM, or automatic detection.",
        "columns_blank": "A blank on-hand figure is not zero: that combination is marked No stock record, and stays off the stockout list. The last row of the inventory template shows this.",
        "columns_download_sales": "Download sales template",
        "columns_download_inv": "Download inventory template",
        "colhelp_sku": "Product identifier.",
        "colhelp_cd_ventas": "Center, store or warehouse where it sold.",
        "colhelp_fecha": "Sale date. Day, week or month all work: everything is aggregated to a month before forecasting.",
        "colhelp_cantidad": "Units sold in that period. Negatives are kept as returns.",
        "colhelp_existencia": "Units on hand today.",
        "colhelp_cd_inv": "If present, stock is matched to sales from that same center. If absent, the SKU's stock is split across its centers by sales history.",
        "colhelp_pack": "Purchase multiple. If the column is missing, 1 is used.",
        "colhelp_lead": "Replenishment days. If the column is missing, 30 is used. A made-up lead time changes the inventory status.",
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


def es_demo() -> bool:
    """El visitante entró por Probar demo. La sesión cubre el rerun; el query param
    sobrevive un F5 y un link compartido (/forecast?demo=1)."""
    if st.session_state.get("modo_demo"):
        return True
    try:
        return str(st.query_params.get("demo", "")) == "1"
    except Exception:
        return False


def entrar_demo():
    st.session_state["modo_demo"] = True
    st.session_state["forecast_view"] = None
    try:
        st.query_params["demo"] = "1"
    except Exception:
        pass


def salir_demo():
    st.session_state.pop("modo_demo", None)
    try:
        if str(st.query_params.get("demo", "")) == "1":
            del st.query_params["demo"]
    except Exception:
        pass


@st.cache_data
def load(demo: bool = False):
    """(resultados, historico) o (None, None) si el pipeline nunca corrió.

    demo=True lee demo/*.parquet (muestra sintética). El default sigue siendo el
    parquet del cliente, que es lo que ve una sesión autenticada.
    No invalida por cambios en disco: después de re-correr pipeline.py hay que limpiar
    la cache (st.cache_data.clear(), que es lo que hace el modal de carga).
    Import lazy de polars para no penalizar la landing (que no lo necesita)."""
    import polars as pl

    carpeta = DEMO_DIR if demo else BASE
    res_path = carpeta / "resultados.parquet"
    hist_path = carpeta / "historico.parquet"
    if not res_path.exists() or not hist_path.exists():
        return None, None
    return pl.read_parquet(res_path), pl.read_parquet(hist_path)


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
