"""Landing: qué resuelve la app, cómo funciona y tres gráficos con los datos ya calculados.

Página de st.navigation (entry point: app.py). El CTA salta a app_pages/forecast.py.
Sin parquets NO corta la página: esconde métricas y gráficos y deja la instrucción de correr
pipeline.py — al revés que el dashboard, que sin datos no tiene nada que mostrar.
"""

import plotly.graph_objects as go
import polars as pl
import streamlit as st

import core
from core import (ACCENT_CYAN, ACCENT_ORANGE, ADI_THRESHOLD, BG_DARK, BG_PANEL, CLASE_COLOR,
                  CV2_THRESHOLD, H, PLOTLY_LAYOUT, TEXT_LIGHT, axis)

TXT = core.txt()
ESTADO_MAP, ESTADO_COLOR, CLASE_MAP = core.mapas()

PAGINA_FORECAST = "app_pages/forecast.py"

# Los `key` de container/button se vuelven clases `.st-key-<key>`: es la unica forma de
# pintar solo las tarjetas de esta pagina sin tocar los contenedores del dashboard.
st.html(f"""
<style>
[class*="st-key-card_"] {{
    background-color: {BG_PANEL};
    border: 1px solid rgba(245,247,250,0.10) !important;
    border-radius: 10px;
    padding: 4px 6px;
    height: 100%;
}}
[class*="st-key-cta_"] button {{
    background-color: {ACCENT_CYAN} !important;
    color: {BG_DARK} !important;
    border: none !important;
    font-weight: 700;
    padding: 0.6rem 1.6rem;
}}
[class*="st-key-cta_"] button:hover {{
    background-color: {ACCENT_ORANGE} !important;
}}
[class*="st-key-cta_"] button * {{
    color: {BG_DARK} !important;
}}
</style>
""")


def cta(key):
    """Botón 'ir al forecast'. Se repite arriba y abajo: la landing es larga."""
    if st.button(TXT["landing_cta"], key=key, icon=":material/arrow_forward:"):
        st.switch_page(PAGINA_FORECAST)


# ------------------------------------------------------------------ Hero
logo, titulo = st.columns([1, 6], vertical_alignment="center")
logo.image(str(core.BASE / "assets" / "intelliforecast.png"), width=110)
titulo.title(TXT["landing_hero_title"])
titulo.markdown(TXT["landing_hero_sub"].format(h=H))

cta("cta_top")

res, hist = core.load()
hay_datos = res is not None
if not hay_datos:
    st.info(TXT["landing_no_data"], icon=":material/info:")
else:
    res = res.with_columns(
        pl.col("estado_inventario").replace(ESTADO_MAP).alias("estado_inventario"),
        pl.col("clasificacion").replace(CLASE_MAP).alias("clasificacion"),
    )
    n_riesgo = res.filter(pl.col("estado_inventario") == ESTADO_MAP["Riesgo de quiebre"]).height

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric(TXT["landing_metric_series"], f"{res.height:,}")
    m2.metric(TXT["landing_metric_skus"], f"{res['sku'].n_unique():,}")
    m3.metric(TXT["landing_metric_cds"], f"{res['centro_distribucion'].n_unique():,}")
    m4.metric(TXT["landing_metric_meses"], f"{hist['fecha'].n_unique():,}")
    m5.metric(TXT["landing_metric_horizonte"], f"{H} {TXT['landing_meses_unit']}")
    m6.metric(TXT["landing_metric_riesgo"], f"{n_riesgo:,}")

# ------------------------------------------------------------------ Para qué sirve
st.subheader(TXT["landing_uses_title"])

usos = [
    (":material/query_stats:", TXT["landing_use1_title"], TXT["landing_use1_body"]),
    (":material/warning:", TXT["landing_use2_title"], TXT["landing_use2_body"]),
    (":material/savings:", TXT["landing_use3_title"], TXT["landing_use3_body"]),
]
for i, (col, (icono, tit, cuerpo)) in enumerate(zip(st.columns(3), usos)):
    # key indexado (no el titulo): se vuelve nombre de clase CSS, sin espacios ni acentos.
    with col.container(border=True, key=f"card_uso_{i}"):
        st.markdown(f"### {icono}")
        st.markdown(f"**{tit}**")
        st.caption(cuerpo)

# ------------------------------------------------------------------ Gráficos (datos reales)
if hay_datos:
    st.subheader(TXT["landing_charts_title"])

    izq, der = st.columns([3, 2])

    with izq:
        st.markdown(f"**{TXT['scatter_title']}**")
        st.caption(TXT["scatter_caption"])

        fig = go.Figure()
        x_max = max(float(res["adi"].max() or 3.0) * 1.05, ADI_THRESHOLD * 1.5)
        y_max = max(float(res["cv2"].max() or 1.0) * 1.05, CV2_THRESHOLD * 1.5)
        bandas = [
            (0, ADI_THRESHOLD, 0, CV2_THRESHOLD, "Smooth"),
            (0, ADI_THRESHOLD, CV2_THRESHOLD, y_max, "Erratic"),
            (ADI_THRESHOLD, x_max, 0, CV2_THRESHOLD, "Intermittent"),
            (ADI_THRESHOLD, x_max, CV2_THRESHOLD, y_max, "Lumpy"),
        ]
        for x0, x1, y0, y1, clase in bandas:
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                          fillcolor=CLASE_COLOR[clase], opacity=0.12, line_width=0, layer="below")
            fig.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=CLASE_MAP[clase], showarrow=False,
                               font=dict(size=13, color=CLASE_COLOR[clase]), opacity=0.75)
        for clase, color in CLASE_COLOR.items():
            sub = res.filter(pl.col("clasificacion") == CLASE_MAP[clase])
            if sub.height == 0:
                continue
            fig.add_trace(go.Scatter(
                x=sub["adi"].to_list(), y=sub["cv2"].to_list(),
                mode="markers", name=CLASE_MAP[clase],
                marker=dict(size=8, color=color, line=dict(width=0.5, color=BG_DARK), opacity=0.85),
                text=[f"{s}·{c}" for s, c in zip(sub["sku"], sub["centro_distribucion"])],
                hovertemplate="%{text}<br>ADI=%{x:.2f}<br>CV²=%{y:.2f}<extra></extra>",
            ))
        fig.add_vline(x=ADI_THRESHOLD, line=dict(color="rgba(245,247,250,0.35)", dash="dash", width=1))
        fig.add_hline(y=CV2_THRESHOLD, line=dict(color="rgba(245,247,250,0.35)", dash="dash", width=1))
        fig.update_layout(
            **PLOTLY_LAYOUT,
            xaxis_title=TXT["adi_axis"], yaxis_title=TXT["cv2_axis"],
            xaxis=axis(range=[0, x_max]), yaxis=axis(range=[0, y_max]),
            height=380, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        )
        st.plotly_chart(fig)

    with der:
        st.markdown(f"**{TXT['estado_title']}**")
        st.caption(TXT["estado_caption"])

        estados = res.group_by("estado_inventario").len().sort("len", descending=True)
        figd = go.Figure(go.Pie(
            labels=estados["estado_inventario"].to_list(), values=estados["len"].to_list(),
            hole=0.62, sort=False,
            marker=dict(colors=[ESTADO_COLOR.get(e, "#888") for e in estados["estado_inventario"]],
                        line=dict(color=BG_DARK, width=2)),
            textinfo="percent", hovertemplate="%{label}<br>%{value} · %{percent}<extra></extra>",
        ))
        figd.update_layout(
            **PLOTLY_LAYOUT, height=380, margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True, legend=dict(orientation="h", yanchor="top", y=0),
            annotations=[dict(text=f"{res.height:,}", x=0.5, y=0.55, showarrow=False,
                              font=dict(size=26, color=TEXT_LIGHT)),
                         dict(text=TXT["landing_metric_series"], x=0.5, y=0.44, showarrow=False,
                              font=dict(size=11, color=ACCENT_CYAN))],
        )
        st.plotly_chart(figd)

    # Ejemplo de forecast: la serie de mayor volumen, que es la que mas se parece a lo que
    # el cliente mira primero (y la que menos chance tiene de ser una serie corta degenerada).
    top_uid = (hist.group_by("unique_id").agg(pl.col("cantidad").sum())
               .sort("cantidad", descending=True)["unique_id"][0])
    fila = res.filter(pl.col("unique_id") == top_uid).row(0, named=True)
    serie = hist.filter(pl.col("unique_id") == top_uid).sort("fecha")

    st.markdown(f"**{TXT['landing_chart_fcst_title'].format(sku=fila['sku'], cd=fila['centro_distribucion'])}**")

    fechas_fc = [fila[f"fecha_w{i}"] for i in range(1, H + 1)]
    valores_fc = [fila[f"forecast_w{i}"] for i in range(1, H + 1)]

    figf = go.Figure()
    figf.add_trace(go.Scatter(
        x=serie["fecha"].to_list(), y=serie["cantidad"].to_list(),
        mode="lines", name=TXT["chart_hist"], line=dict(color=ACCENT_CYAN, width=1.8),
    ))
    figf.add_trace(go.Scatter(
        x=[serie["fecha"].to_list()[-1]] + fechas_fc,
        y=[serie["cantidad"].to_list()[-1]] + valores_fc,
        mode="lines+markers", name=TXT["chart_fcst"].format(modelo=fila["modelo_ganador"]),
        line=dict(color=ACCENT_ORANGE, width=2.5, dash="dot"), marker=dict(size=8),
    ))
    figf.update_layout(
        **PLOTLY_LAYOUT, height=340, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=axis(title=TXT["chart_xaxis"]), yaxis=axis(title=TXT["chart_yaxis"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
    )
    st.plotly_chart(figf)
    st.caption(TXT["landing_chart_fcst_caption"].format(h=H, modelo=fila["modelo_ganador"]))

# ------------------------------------------------------------------ Cómo funciona
st.subheader(TXT["landing_how_title"])

pasos = [
    (":material/calendar_month:", TXT["landing_step1_title"], TXT["landing_step1_body"]),
    (":material/scatter_plot:", TXT["landing_step2_title"], TXT["landing_step2_body"]),
    (":material/trophy:", TXT["landing_step3_title"], TXT["landing_step3_body"]),
    (":material/inventory_2:", TXT["landing_step4_title"], TXT["landing_step4_body"]),
]
for i, (col, (icono, tit, cuerpo)) in enumerate(zip(st.columns(4), pasos)):
    with col.container(border=True, key=f"card_paso_{i}"):
        st.markdown(f"### {icono}")
        st.markdown(f"**{tit}**")
        st.caption(cuerpo)

cta("cta_bottom")
st.caption(TXT["app_caption"])
