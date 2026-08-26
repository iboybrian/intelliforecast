"""Landing comercial liviana.

No carga parquets ni plotea con datos reales: todo es estático + screenshots
de assets/. El trabajo pesado (core.load -> resultados.parquet) solo ocurre
en app_pages/forecast.py cuando el usuario navega al forecast. Así el inicio
carga instantáneo.
"""

import streamlit as st

import core
from core import ACCENT_CYAN, ACCENT_ORANGE, BG_DARK, BG_PANEL, H

# contrapeso del "collapsed" de forecast.py: sin esto el sidebar queda cerrado al volver al
# inicio, porque el estado se hereda de la ultima llamada a set_page_config.
st.set_page_config(initial_sidebar_state="expanded")

TXT = core.txt()

PAGINA_FORECAST = "app_pages/forecast.py"

st.html(f"""
<style>
[class*="st-key-card_"] {{
    background-color: {BG_PANEL};
    border: 1px solid rgba(245,247,250,0.10) !important;
    border-radius: 12px;
    padding: 8px 10px;
    height: 100%;
}}
[class*="st-key-cta_"] button {{
    background-color: {ACCENT_CYAN} !important;
    color: {BG_DARK} !important;
    border: none !important;
    font-weight: 700;
    padding: 0.65rem 1.8rem;
    font-size: 1.02rem;
}}
[class*="st-key-cta_"] button:hover {{
    background-color: {ACCENT_ORANGE} !important;
}}
[class*="st-key-cta_"] button * {{
    color: {BG_DARK} !important;
}}
.badge {{
    display: inline-block;
    background: rgba(125,216,245,0.15);
    border: 1px solid rgba(125,216,245,0.35);
    color: {ACCENT_CYAN} !important;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}}
</style>
""")


@st.dialog(TXT.get("landing_dialog_title", "Un momento antes de entrar"), width="large")
def dialog_forecast():
    st.warning(TXT.get("landing_dialog_body", ""), icon=":material/hourglass_top:")
    st.caption(TXT.get("landing_dialog_tip", ""))
    if st.button(TXT.get("landing_dialog_confirm", "Entendido, ver forecast"),
                 type="primary", use_container_width=True):
        st.switch_page(PAGINA_FORECAST)


def cta(key):
    if st.button(TXT.get("landing_cta","Ver forecast ahora"), key=key, icon=":material/arrow_forward:"):
        dialog_forecast()


# ------------------------------------------------------------------ Hero
logo, titulo = st.columns([1, 6], vertical_alignment="center")
logo.image(str(core.BASE / "assets" / "intelliforecast.jpg"), width=110)
with titulo:
    st.markdown(f"<span class='badge'>{TXT.get('landing_hero_badge', 'Forecast mensual · KPIs de inventario · Reposición sugerida')}</span>", unsafe_allow_html=True)
    st.title(TXT.get("landing_hero_title", "Forecast de Demanda"))
    st.markdown(TXT.get("landing_hero_sub", "").format(h=H) if "{h}" in TXT.get("landing_hero_sub","") else TXT.get("landing_hero_sub",""))
    cta("cta_top")
    st.caption(TXT.get("landing_cta_sub",""))

# ------------------------------------------------------------------ ¿Te suena familiar? (pain questions)
st.subheader(TXT.get("landing_pain_title","¿Te suena familiar?"))
st.caption(TXT.get("landing_pain_sub",""))

p1, p2, p3 = st.columns(3)
pains = [
    (":material/warning:", TXT.get("landing_pain_q1_title","¿Te topas con quiebres de stock?"), TXT.get("landing_pain_q1_body","")),
    (":material/stacks:", TXT.get("landing_pain_q2_title","¿Te enredás con múltiples productos?"), TXT.get("landing_pain_q2_body","")),
    (":material/schedule:", TXT.get("landing_pain_q3_title","¿Querés liberar tiempo?"), TXT.get("landing_pain_q3_body","")),
]
for i, (col, (icono, tit, cuerpo)) in enumerate(zip([p1, p2, p3], pains)):
    with col.container(border=True, key=f"card_pain_{i}"):
        st.markdown(f"### {icono}")
        st.markdown(f"**{tit}**")
        st.caption(cuerpo)

# ------------------------------------------------------------------ Qué obtienes (beneficios)
st.subheader(TXT.get("landing_benefits_title","Qué obtienes"))
st.caption(TXT.get("landing_benefits_sub",""))

b1, b2 = st.columns(2)
b3, b4 = st.columns(2)
benefits = [
    (":material/query_stats:", TXT.get("landing_benefit1_title","Forecast por SKU y centro"), TXT.get("landing_benefit1_body","")),
    (":material/notification_important:", TXT.get("landing_benefit2_title","Alertas de quiebre"), TXT.get("landing_benefit2_body","")),
    (":material/savings:", TXT.get("landing_benefit3_title","Sobre-stock visible"), TXT.get("landing_benefit3_body","")),
    (":material/dashboard:", TXT.get("landing_benefit4_title","Dashboard + Excel"), TXT.get("landing_benefit4_body","")),
]
cols_b = [b1, b2, b3, b4]
for i, (col, (icono, tit, cuerpo)) in enumerate(zip(cols_b, benefits)):
    with col.container(border=True, key=f"card_benefit_{i}"):
        st.markdown(f"### {icono}")
        st.markdown(f"**{tit}**")
        st.caption(cuerpo)

# ------------------------------------------------------------------ Cómo funciona
st.subheader(TXT.get("landing_how_title","Cómo funciona"))
st.markdown(f"#### {TXT.get('landing_how_lead','')}")
st.caption(TXT.get("landing_how_sub",""))

pasos = [
    (":material/upload:", TXT.get("landing_step1_title","1 · Subís tus CSVs"), TXT.get("landing_step1_body","")),
    (":material/scatter_plot:", TXT.get("landing_step2_title","2 · Clasificamos"), TXT.get("landing_step2_body","")),
    (":material/trophy:", TXT.get("landing_step3_title","3 · Compiten modelos"), TXT.get("landing_step3_body","")),
    (":material/inventory_2:", TXT.get("landing_step4_title","4 · Traducimos a inventario"), TXT.get("landing_step4_body","")),
]
c1, c2, c3, c4 = st.columns(4)
for i, (col, (icono, tit, cuerpo)) in enumerate(zip([c1, c2, c3, c4], pasos)):
    with col.container(border=True, key=f"card_paso_{i}"):
        st.markdown(f"### {icono}")
        st.markdown(f"**{tit}**")
        st.caption(cuerpo)

# ------------------------------------------------------------------ Dashboard preview (debajo de Qué obtienes / Cómo funciona)
st.subheader(TXT.get("landing_dashboard_title","Así se ve el dashboard"))
st.caption(TXT.get("landing_dashboard_sub",""))

dashboard_path = core.BASE / "assets" / "dashboard.png"
quiebre_path = core.BASE / "assets" / "quiebre.png"
exceso_path = core.BASE / "assets" / "exceso.png"

if dashboard_path.exists():
    st.image(str(dashboard_path), use_container_width=True)
    st.caption(TXT.get("landing_dashboard_caption",""))
else:
    st.info(TXT.get("landing_dashboard_caption",""), icon=":material/image:")

g1, g2 = st.columns(2)
with g1:
    if quiebre_path.exists():
        st.image(str(quiebre_path), caption="Riesgo de quiebre" if TXT.get("tab_risk") else None, use_container_width=True)
with g2:
    if exceso_path.exists():
        st.image(str(exceso_path), caption="Sobre-stock" if TXT.get("tab_overstock") else None, use_container_width=True)

# ------------------------------------------------------------------ Trust + CTA final
with st.container(border=True, key="card_trust"):
    st.markdown(f"**{TXT.get('landing_trust_title','')}**")
    st.caption(TXT.get("landing_trust_body",""))

cta("cta_bottom")
st.caption(TXT.get("app_caption",""))
