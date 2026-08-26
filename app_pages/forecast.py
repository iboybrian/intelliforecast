"""Forecast: hub de entrada (4 opciones) + vistas dedicadas con sub-navegación.

`forecast_view = None` es el hub; una vez adentro, el segmented_control salta entre las 3
vistas en 1 clic y "Volver al menú" regresa al hub. Solo se renderiza la vista elegida — las
tres son caras y st.tabs las dibujaría todas. El upload se delega al modal de app.py vía
flag trigger_upload_dialog.
"""

import datetime
import io

import polars as pl
import plotly.graph_objects as go
import streamlit as st
import xlsxwriter

import core
from core import (ACCENT_CYAN, ACCENT_ORANGE, ADI_THRESHOLD, BG_DARK, BG_PANEL, CLASE_COLOR,
                  CV2_THRESHOLD, H, MIN_PERIODOS, PLOTLY_LAYOUT, TEXT_LIGHT, axis)

# Sidebar colapsado en el dashboard: la pantalla es angosta para 7 filtros + tablas, y todo lo
# que vivia ahi ya tiene salida propia aca (nav de vistas, boton de subir datos). Se colapsa, no
# se esconde: el chevron sigue estando para el idioma y para volver al inicio. Los demas
# parametros de set_page_config se heredan de la llamada de app.py.
st.set_page_config(initial_sidebar_state="collapsed")

TXT = core.txt()
ESTADO_MAP, ESTADO_COLOR, CLASE_MAP = core.mapas()


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


res, hist = core.load()
if res is None:
    st.error(TXT.get("error_no_parquet", "No se encontró resultados.parquet. Corre primero:  python pipeline.py"))
    st.stop()

if avisos_carga := st.session_state.pop("avisos_carga", None):
    with st.expander(TXT["avisos_title"].format(n=len(avisos_carga))):
        for aviso in avisos_carga:
            st.write(aviso)

res = res.with_columns(
    pl.col("estado_inventario").replace(ESTADO_MAP).alias("estado_inventario"),
    pl.col("clasificacion").replace(CLASE_MAP).alias("clasificacion"),
)

# ------------------------------------------------------------------ Hub + navegacion entre vistas
VISTAS = {"overview": TXT["tab_overview"], "risk": TXT["tab_risk"], "overstock": TXT["tab_overstock"]}
view = st.session_state.setdefault("forecast_view", None)


def abrir_upload():
    st.session_state["trigger_upload_dialog"] = True   # el modal vive en app.py
    st.rerun()


# Hub de entrada: nada de datos por default. Se llega aca al entrar a la pagina y al volver
# desde cualquier vista.
if view is None:
    st.title(TXT.get("forecast_menu_title", "¿Qué querés hacer?"))
    st.caption(TXT.get("forecast_menu_sub", ""))
    st.divider()

    # las tarjetas reusan el patron st-key-card_ de la landing (mismo BG_PANEL)
    st.html(f"""<style>[class*="st-key-card_hub"]{{background-color:{BG_PANEL};border:1px solid rgba(245,247,250,0.10) !important;border-radius:12px;padding:10px;height:100%}}</style>""")

    opciones = [
        ("dashboard", "overview", ":material/dashboard:", "forecast_opt_dashboard"),
        ("risk", "risk", ":material/warning:", "forecast_opt_risk"),
        ("over", "overstock", ":material/inventory_2:", "forecast_opt_over"),
        ("upload", None, ":material/upload:", "forecast_opt_upload"),
    ]
    celdas = [*st.columns(2), *st.columns(2)]
    for celda, (slug, destino, icono, clave) in zip(celdas, opciones):
        with celda.container(border=True, key=f"card_hub_{slug}"):
            st.markdown(f"**{TXT.get(clave + '_title', '')}**")
            st.caption(TXT.get(clave + "_body", ""))
            if st.button(TXT.get(clave + "_btn", ""), key=f"hub_{slug}", use_container_width=True,
                         type="primary" if destino else "secondary", icon=icono):
                if destino is None:
                    abrir_upload()
                st.session_state["forecast_view"] = destino
                st.rerun()
    st.stop()

# segmented_control y no st.tabs: las tres vistas son caras (21k filas + plotly) y tabs las
# renderiza todas en cada rerun. Desde el hub se entra una vez y despues se salta en 1 clic.
volver, nav, subir = st.columns([1, 3, 1], vertical_alignment="bottom")
if volver.button(TXT.get("forecast_back", "← Volver al menú"), key="back_menu", use_container_width=True):
    st.session_state["forecast_view"] = None
    st.rerun()
view = nav.segmented_control(TXT["nav_forecast"], list(VISTAS), format_func=VISTAS.get,
                             key="forecast_view", label_visibility="collapsed") or view
if subir.button(TXT.get("forecast_opt_upload_btn", "Subir datos"), key="nav_upload",
                use_container_width=True, icon=":material/upload:"):
    abrir_upload()
st.divider()

# ------------------------------------------------------------------ Filtros compartidos (solo para vistas de datos)
f1, f2, f3, f4, f5, f6, f7 = st.columns([1, 1.2, 1, 1, 1.3, 0.9, 0.8])

# key con prefijo "f_" en todo lo que filtra: es lo que hace posible el boton de limpiar.
# El sku de drill-down NO lleva key a proposito: sus opciones dependen del filtro y un valor
# guardado que ya no esta en la lista revienta el selectbox.
cds = [TXT["all"]] + sorted(res["centro_distribucion"].unique().to_list())
cd_sel = f1.selectbox(TXT["cd_label"], cds, key="f_cd")

clases_disp = sorted(res["clasificacion"].unique().to_list())
clase_sel = f2.multiselect(TXT["clase_label"], clases_disp, default=clases_disp, key="f_clase")

with f7:
    st.write("")   # alinea el boton con la base de los selectbox
    if st.button(TXT["reset_filters"], use_container_width=True):
        for k in [k for k in st.session_state if k.startswith("f_")]:
            del st.session_state[k]
        st.rerun()


def filtro_opcional(container, col, label):
    """selectbox (Todos)+valores si la columna existe; deshabilitado si no."""
    if col in res.columns:
        opciones = [TXT["all"]] + sorted(res[col].drop_nulls().unique().to_list())
        return container.selectbox(label, opciones, key=f"f_{col}")
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

dims_disp = sorted({d for d in core.load_dim_config() if d in res.columns} - {"proveedor", "categoria"})
if dims_disp:
    elegidas = st.multiselect(TXT["add_filters_label"], dims_disp, default=[], key="f_dims")
    if elegidas:
        for c, dim in zip(st.columns(len(elegidas)), elegidas):
            val_sel = filtro_opcional(c, dim, dim)
            if val_sel != TXT["all"]:
                res_f = res_f.filter(pl.col(dim) == val_sel)

if res_f.height == 0:
    st.warning(TXT["no_data_filter"])
    st.stop()

skus = sorted(res_f["sku"].unique().to_list())
# sku selector solo relevante para overview, pero lo mantenemos para consistencia; en risk/overstock se ignora
sku_sel = f5.selectbox(TXT["sku_label"], skus)
f6.metric(TXT["combos_metric"], res_f.height)

# estados ya traducidos
estado_riesgo = ESTADO_MAP["Riesgo de quiebre"]
estado_sobre = ESTADO_MAP["Sobre-stock"]
estado_normal = ESTADO_MAP["Normal"]
estado_sindato = ESTADO_MAP["Sin registro"]

# ==================================================================== VIEW: Overview (Dashboard)
if view == "overview":
    st.title(TXT["title_overview"])
    scope = TXT["scope_all"] if cd_sel == TXT["all"] else cd_sel
    st.caption(TXT["scope_caption"].format(scope=scope, n=res_f.height))

    # mediana, no media: DOH no tiene cota superior (un SKU con forecast ~0 da decenas de miles
    # de dias) y la media terminaba describiendo la cola en vez del catalogo.
    doh_prom = res_f["doh"].median()
    wos_prom = res_f["wos"].median()
    moh_prom = res_f["moh"].median()
    n_riesgo = res_f.filter(pl.col("estado_inventario") == estado_riesgo).height
    n_sobre = res_f.filter(pl.col("estado_inventario") == estado_sobre).height
    n_normal = res_f.filter(pl.col("estado_inventario") == estado_normal).height
    n_sindato = res_f.filter(pl.col("estado_inventario") == estado_sindato).height

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric(TXT["doh_avg"], f"{doh_prom:,.0f} {TXT['days_unit']}" if doh_prom is not None else "—")
    c2.metric(TXT["wos_avg"], f"{wos_prom:,.1f} {TXT['weeks_unit']}" if wos_prom is not None else "—")
    c3.metric(TXT["moh_avg"], f"{moh_prom:,.1f} {TXT['months_unit']}" if moh_prom is not None else "—")
    c4.metric(TXT["risk_metric"], n_riesgo)
    c5.metric(TXT["over_metric"], n_sobre)
    c6.metric(TXT["normal_metric"], n_normal)
    c7.metric(TXT["sindato_metric"], n_sindato, help=TXT["sindato_help"])

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
            # Scattergl + punto chico y translucido: con 20k combinaciones el SVG normal es una
            # mancha solida y ademas tarda. No se samplea: el punto del grafico es ver la cola.
            fig.add_trace(go.Scattergl(
                x=sub["adi"].to_list(), y=sub["cv2"].to_list(),
                mode="markers", name=CLASE_MAP[clase],
                marker=dict(size=4, color=color, opacity=0.45),
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
        st.plotly_chart(fig)

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
        st.plotly_chart(figb)

        st.subheader(TXT["modelos_title"])
        modelos = res_f.group_by("modelo_ganador").len().sort("len", descending=True)
        figm = go.Figure(go.Bar(
            x=modelos["len"].to_list(), y=modelos["modelo_ganador"].to_list(),
            orientation="h", marker_color=ACCENT_CYAN,
            text=modelos["len"].to_list(), textposition="outside",
        ))
        figm.update_layout(**PLOTLY_LAYOUT, height=220, margin=dict(l=10, r=30, t=10, b=10),
                           xaxis=axis(), xaxis_title=TXT["estado_axis"], yaxis=axis(autorange="reversed"))
        st.plotly_chart(figm)
        # sin esto el grafico se lee como "elegimos SeasonalNaive"; en realidad es la rama de
        # series cortas, que es lo unico que el comprador necesita saber para confiar o no.
        n_cortas = res_f.filter(pl.col("flag_serie_corta")).height
        st.caption(TXT["cobertura_caption"].format(
            largas=res_f.height - n_cortas, cortas=n_cortas, min=MIN_PERIODOS,
            pct=100 * n_cortas / res_f.height))

    st.divider()

    st.subheader(TXT["criticos_title"])
    # "Sin registro" no es critico, es dato faltante: fuera de la lista de accion.
    criticos_base = res_f.filter(~pl.col("estado_inventario").is_in([estado_normal, estado_sindato])).sort(
        ["estado_inventario", "doh"]
    )
    criticos = criticos_base.select([
        pl.col("sku").alias(TXT["col_sku"]), pl.col("centro_distribucion").alias(TXT["col_cd"]),
        pl.col("clasificacion").alias(TXT["col_clase"]), pl.col("estado_inventario").alias(TXT["col_estado"]),
        pl.col("existencia_cd").round(0).alias(TXT["col_existencia"]),
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

    st.dataframe(criticos, height=340, hide_index=True)

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
    # mase null = escala de train constante: no es medible, no es 0 (ver _mase_valido en pipeline)
    k3.metric(TXT["mase_metric"], f"{row['mase']:.2f}" if row["mase"] is not None else "—")
    doh_val = row["doh"]
    k4.metric(TXT["doh_metric"], f"{doh_val:,.0f} {TXT['days_unit']}" if doh_val is not None else "∞",
              help=TXT["doh_help"])
    k5.metric(TXT["col_lead"], f"{row['lead_time_dias']:,.0f} {TXT['days_unit']}")
    k6.metric(TXT["estado_metric"], row["estado_inventario"])

    badge = ESTADO_COLOR.get(row["estado_inventario"], "#888")
    st.markdown(
        f"<span style='background:{badge};color:{BG_DARK};padding:3px 10px;border-radius:12px;"
        f"font-size:0.85em;font-weight:600'>{row['estado_inventario']}</span> &nbsp; "
        + TXT["badge_line"].format(exist=row["existencia_cd"], pack=row["pack"], reorden=row["cantidad_reorden"]),
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
    st.plotly_chart(figf)
    if row.get("flag_serie_corta"):
        st.caption(TXT["short_series_caption"].format(n=row["n_periodos"]))
    elif row["mase"] is not None:
        st.caption(TXT["winner_caption"].format(modelo=row["modelo_ganador"], mase=row["mase"]))

# ==================================================================== VIEW: Riesgo
elif view == "risk":
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
            pl.col("existencia_cd").round(0).alias(TXT["risk_stock"]),
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
            tabla_riesgo, height=420, hide_index=True,
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
        st.plotly_chart(figr, key=f"chart_{fila['unique_id']}")

# ==================================================================== VIEW: Sobre-stock
elif view == "overstock":
    st.title(TXT["overstock_header"])
    scope = TXT["scope_all"] if cd_sel == TXT["all"] else cd_sel

    exceso_expr = pl.max_horizontal(
        pl.col("existencia_cd") - pl.col("demanda_diaria_promedio") * 120, pl.lit(0.0)
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
            pl.col("existencia_cd").round(0).alias(TXT["risk_stock"]),
            pl.col("doh").round(1).alias(TXT["col_doh"]),
            pl.col("moh").round(1).alias(TXT["col_moh"]),
            pl.col("forecast_mensual_promedio").round(1).alias(TXT["col_fcst"]),
            pl.col("modelo_ganador").alias(TXT["col_modelo"]),
            pl.col("exceso_unidades").alias(TXT["col_exceso"]),
            # DOH null aca no es un hueco: es stock sin demanda proyectada, o sea DOH infinito.
            # Sin esta columna la tabla mostraba una celda vacia y el usuario leia "dato roto".
            pl.when(pl.col("doh").is_null()).then(pl.lit(TXT["motivo_sin_demanda"]))
              .otherwise(pl.lit(TXT["motivo_cobertura"])).alias(TXT["col_motivo"]),
        ])

        leg_col, dl_col = st.columns([4, 1])
        leg_col.caption(TXT["overstock_asof_note"].format(hoy=datetime.date.today().isoformat()))
        boton_descarga(dl_col, tabla_sobre, sobre["unique_id"].to_list(), "sobre_stock.xlsx")

        st.dataframe(tabla_sobre, height=420, hide_index=True)

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
        st.plotly_chart(figo, key=f"chart_over_{fila_o['unique_id']}")
