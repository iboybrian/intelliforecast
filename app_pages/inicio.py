"""Landing comercial liviana.

No carga parquets ni plotea con datos reales: todo es estático + screenshots
de assets/. El trabajo pesado (core.load -> resultados.parquet) solo ocurre
en app_pages/forecast.py cuando el usuario navega al forecast. Así el inicio
carga instantáneo.
"""

import base64

import streamlit as st

import core
from core import ACCENT_CYAN, ACCENT_ORANGE, BG_DARK, BG_PANEL, H

# contrapeso del "collapsed" de forecast.py: sin esto el sidebar queda cerrado al volver al
# inicio, porque el estado se hereda de la ultima llamada a set_page_config.
st.set_page_config(initial_sidebar_state="expanded")

TXT = core.txt()

PAGINA_FORECAST = "app_pages/forecast.py"

# Pegar acá el embed URL del Google Form (pestaña "<>" del botón Enviar) una vez creado —
# ver plan/prerequisito. Vacío = el diálogo de Contact Sales muestra un aviso en vez de romper.
GOOGLE_FORM_URL = ""

# bandas de secciones: azul propio (no el de la paleta del resto del sitio), blanco y gris
SECT_BLUE = "#0F4C81"
SECT_WHITE = "#FFFFFF"
SECT_GRAY = "#E9EDF2"


@st.cache_data
def _img_b64(nombre: str) -> str:
    data = (core.BASE / "assets" / nombre).read_bytes()
    return base64.b64encode(data).decode()


HERO_B64 = _img_b64("herosection.jpg")

st.html(f"""
<style>
/* el @import va primero si o si: CSS ignora los que aparecen despues de una regla */
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@48,400,1,0');
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
[class*="st-key-cta2_"] button {{
    background-color: transparent !important;
    color: #FFFFFF !important;
    border: 2px solid #FFFFFF !important;
    font-weight: 700;
    padding: 0.6rem 1.75rem;
    font-size: 1.02rem;
}}
[class*="st-key-cta2_"] button:hover {{
    background-color: rgba(255,255,255,0.15) !important;
    border-color: {ACCENT_CYAN} !important;
}}
[class*="st-key-cta2_"] button * {{
    color: #FFFFFF !important;
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
[class*="st-key-hero_section"] {{
    background-image: url("data:image/jpeg;base64,{HERO_B64}");
    background-size: cover;
    background-position: center;
    min-height: 560px;
    padding: 4rem 2.5rem;
    justify-content: center;
}}
/* bandas alternadas: azul opaco / blanco / gris. El color va siempre; el full-bleed
   solo arriba de 992px (abajo Streamlit achica su padding lateral a 16px). */
[class*="st-key-sect_blue"] {{ background-color: {SECT_BLUE}; }}
[class*="st-key-sect_white"] {{ background-color: {SECT_WHITE}; }}
[class*="st-key-sect_gray"] {{ background-color: {SECT_GRAY}; }}
[class*="st-key-sect_"] {{ padding: 3rem 2.5rem; }}
/* sobre banda clara el texto blanco global desaparece. El .stApp de prefijo es para
   ganarle en especificidad al `.stApp p, .stApp h1...` de core.inject_css(). */
.stApp [class*="st-key-sect_white"] *,
.stApp [class*="st-key-sect_gray"] * {{
    color: {BG_DARK} !important;
}}
/* el fondo oscuro del `code` inline se come su propio texto ya oscurecido */
.stApp [class*="st-key-sect_white"] code,
.stApp [class*="st-key-sect_gray"] code {{
    background-color: rgba(14,27,46,0.07) !important;
}}
[class*="st-key-sect_white"] [class*="st-key-card_"] {{
    background-color: #F4F7FA;
    border: 1px solid rgba(14,27,46,0.14) !important;
}}
[class*="st-key-sect_gray"] [class*="st-key-card_"] {{
    background-color: #FFFFFF;
    border: 1px solid rgba(14,27,46,0.10) !important;
}}
/* sin gap entre bandas: los colores tienen que tocarse */
.stMainBlockContainer > [data-testid="stVerticalBlock"] {{
    gap: 0 !important;
}}
/* la foto va sin tinte, asi que el texto se sostiene con sombra propia */
[class*="st-key-hero_section"] h1,
[class*="st-key-hero_section"] p,
[class*="st-key-hero_section"] .badge {{
    text-shadow: 0 2px 10px rgba(0,0,0,0.9), 0 0 24px rgba(0,0,0,0.6);
}}
/* el gris del caption se pierde sobre la foto */
[class*="st-key-hero_section"] [data-testid="stCaptionContainer"] p {{
    color: rgba(255,255,255,0.85) !important;
}}
.hero-nota {{
    display: inline-block;
    background: rgba(14,27,46,0.72);
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 8px;
    padding: 6px 14px;
    margin-top: 0.5rem;
    font-size: 0.9rem;
    color: #FFFFFF !important;
}}
/* botones del hero uno abajo del otro, mismo ancho */
[class*="st-key-cta_hero_start"] button,
[class*="st-key-cta2_hero_contact"] button {{
    width: 260px;
    justify-content: center;
}}
/* ---- Nuestras soluciones: titulo centrado, icono arriba, boton ancho ---- */
.svc-titulo {{
    text-align: center;
    margin: 0 0 0.4rem;
    font-size: 2.2rem;
}}
.svc-titulo::after {{
    content: "";
    display: block;
    width: 120px;
    height: 3px;
    margin: 0.7rem auto 0;
    background: {SECT_BLUE};
}}
.svc-sub {{ text-align: center; margin: 0 0 2.5rem; opacity: 0.75; }}
.stApp [class*="st-key-svc_"] * {{ text-align: center; }}
[class*="st-key-svc_"] {{ padding: 0 1.5rem; }}
/* min-height para que titulo y cuerpo ocupen lo mismo en las dos tarjetas y los
   botones queden a la misma altura aunque un titulo use dos lineas */
[class*="st-key-svc_"] h3 {{ font-size: 1.6rem; margin-bottom: 0.6rem; min-height: 4.4rem; }}
[class*="st-key-svc_"] [data-testid="stMarkdownContainer"] p {{ min-height: 3.4rem; }}
/* sin esto el boton estira para llenar la columna y queda mas alto que el otro */
[class*="st-key-cta_svc"] button {{ height: 52px; }}
.svc-icon {{
    position: relative;
    height: 110px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1rem;
}}
.svc-icon .material-symbols-rounded {{
    position: relative;
    font-family: 'Material Symbols Rounded' !important;
    font-size: 76px;
    line-height: 1;
    color: {SECT_BLUE} !important;
    font-variation-settings: 'FILL' 1;
}}
.svc-icon .svc-trend {{
    position: absolute;
    font-size: 118px;
    opacity: 0.28;
}}
/* full-bleed: anula el padding del contenedor principal (80px laterales, 96px arriba)
   para que la foto llegue a los bordes. Solo en anchos donde ese padding existe. */
@media (min-width: 992px) {{
    [class*="st-key-hero_section"],
    [class*="st-key-sect_"] {{
        margin-left: -5rem !important;
        margin-right: -5rem !important;
        /* es flex item y Streamlit le fuerza width:100%: el margen negativo lo corre,
           el width con !important lo estira hasta los bordes */
        width: calc(100% + 10rem) !important;
        max-width: none !important;
    }}
    [class*="st-key-sect_"] {{
        padding: 3.5rem 5rem;
    }}
    /* la ultima banda se come el padding-bottom del contenedor (160px) para que no
       quede una franja del fondo del sitio abajo de todo */
    [class*="st-key-sect_gray_trust"] {{
        margin-bottom: -10rem !important;
        padding-bottom: 13rem;
    }}
    [class*="st-key-hero_section"] {{
        margin-top: -7rem !important;
        min-height: 100vh;
        padding: 7rem 5rem 4rem;
    }}
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


@st.dialog(TXT.get("landing_contact_title", "Hablemos"))
def dialog_contact_sales():
    if GOOGLE_FORM_URL:
        st.components.v1.iframe(GOOGLE_FORM_URL, height=640, scrolling=True)
    else:
        st.caption(TXT.get("landing_contact_pending", ""))


def cta(key):
    if st.button(TXT.get("landing_cta", "Ver forecast ahora"), key=key, icon=":material/arrow_forward:"):
        dialog_forecast()


def cta_contact(key):
    if st.button(TXT.get("landing_hero_cta_contact", "Contact sales"), key=key):
        dialog_contact_sales()


# ------------------------------------------------------------------ Hero
with st.container(key="hero_section"):
    st.markdown(f"<span class='badge'>{TXT.get('landing_hero_badge', '')}</span>", unsafe_allow_html=True)
    st.title(TXT.get("landing_hero_title", "Forecast de Demanda"))
    sub = TXT.get("landing_hero_sub", "")
    st.markdown(sub.format(h=H) if "{h}" in sub else sub)
    # sin columnas: uno abajo del otro
    if st.button(TXT.get("landing_hero_cta_start", "Empezar a pronosticar"),
                 key="cta_hero_start", icon=":material/arrow_forward:"):
        dialog_forecast()
    cta_contact("cta2_hero_contact")
    st.markdown(
        f"<span class='hero-nota'>{TXT.get('landing_cta_sub', '')}</span>",
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------------ Por qué IntelliForecast (banda azul)
with st.container(key="sect_blue_why"):
    st.subheader(TXT.get("landing_why_title", "Por qué IntelliForecast"))

    why = [
        (":material/warning:", TXT.get("landing_why_r1_title", ""), TXT.get("landing_why_r1_body", "")),
        (":material/stacks:", TXT.get("landing_why_r2_title", ""), TXT.get("landing_why_r2_body", "")),
        (":material/schedule:", TXT.get("landing_why_r3_title", ""), TXT.get("landing_why_r3_body", "")),
    ]
    for i, (col, (icono, tit, cuerpo)) in enumerate(zip(st.columns(3), why)):
        with col.container(border=True, key=f"card_why_{i}"):
            st.markdown(f"### {icono}")
            st.markdown(f"**{tit}**")
            st.caption(cuerpo)

# ------------------------------------------------------------------ Cómo funciona (banda blanca)
with st.container(key="sect_white_how"):
    st.subheader(TXT.get("landing_how_title", "Cómo funciona"))
    st.markdown(f"#### {TXT.get('landing_how_lead', '')}")
    st.caption(TXT.get("landing_how_sub", ""))

    pasos = [
        (":material/upload:", TXT.get("landing_step1_title", "1 · Subís tus CSVs"), TXT.get("landing_step1_body", "")),
        (":material/scatter_plot:", TXT.get("landing_step2_title", "2 · Clasificamos"), TXT.get("landing_step2_body", "")),
        (":material/trophy:", TXT.get("landing_step3_title", "3 · Compiten modelos"), TXT.get("landing_step3_body", "")),
        (":material/inventory_2:", TXT.get("landing_step4_title", "4 · Traducimos a inventario"), TXT.get("landing_step4_body", "")),
    ]
    for i, (col, (icono, tit, cuerpo)) in enumerate(zip(st.columns(4), pasos)):
        with col.container(border=True, key=f"card_paso_{i}"):
            st.markdown(f"### {icono}")
            st.markdown(f"**{tit}**")
            st.caption(cuerpo)

# ------------------------------------------------------------------ Qué obtienes (banda gris)
with st.container(key="sect_gray_what"):
    st.subheader(TXT.get("landing_benefits_title", "Qué obtienes"))
    st.caption(TXT.get("landing_benefits_sub", ""))

    benefits = [
        (":material/query_stats:", TXT.get("landing_benefit1_title", "Forecast por SKU y centro"), TXT.get("landing_benefit1_body", "")),
        (":material/notification_important:", TXT.get("landing_benefit2_title", "Alertas de quiebre"), TXT.get("landing_benefit2_body", "")),
        (":material/savings:", TXT.get("landing_benefit3_title", "Sobre-stock visible"), TXT.get("landing_benefit3_body", "")),
        (":material/dashboard:", TXT.get("landing_benefit4_title", "Dashboard + Excel"), TXT.get("landing_benefit4_body", "")),
    ]
    b1, b2 = st.columns(2)
    b3, b4 = st.columns(2)
    for i, (col, (icono, tit, cuerpo)) in enumerate(zip([b1, b2, b3, b4], benefits)):
        with col.container(border=True, key=f"card_benefit_{i}"):
            st.markdown(f"### {icono}")
            st.markdown(f"**{tit}**")
            st.caption(cuerpo)

# ------------------------------------------------------------------ Equipo (banda blanca)
with st.container(key="sect_white_team"):
    side_txt, side_img = st.columns([1, 1], vertical_alignment="center")
    with side_txt:
        st.markdown(f"#### {TXT.get('landing_what_side_title', '')}")
        st.markdown(f"- {TXT.get('landing_what_side_b1', '')}")
        st.markdown(f"- {TXT.get('landing_what_side_b2', '')}")
        st.markdown(f"- {TXT.get('landing_what_side_b3', '')}")
    with side_img:
        st.image(str(core.BASE / "assets" / "teamworking.jpg"), use_container_width=True)

# ------------------------------------------------------------------ Dashboard preview (banda azul)
with st.container(key="sect_blue_dashboard"):
    st.subheader(TXT.get("landing_dashboard_title", "Así se ve el dashboard"))
    st.caption(TXT.get("landing_dashboard_sub", ""))

    dashboard_path = core.BASE / "assets" / "dashboard.png"
    quiebre_path = core.BASE / "assets" / "quiebre.png"
    exceso_path = core.BASE / "assets" / "exceso.png"

    if dashboard_path.exists():
        st.image(str(dashboard_path), use_container_width=True)
        st.caption(TXT.get("landing_dashboard_caption", ""))
    else:
        st.info(TXT.get("landing_dashboard_caption", ""), icon=":material/image:")

    g1, g2 = st.columns(2)
    with g1:
        if quiebre_path.exists():
            st.image(str(quiebre_path), caption="Riesgo de quiebre" if TXT.get("tab_risk") else None, use_container_width=True)
    with g2:
        if exceso_path.exists():
            st.image(str(exceso_path), caption="Sobre-stock" if TXT.get("tab_overstock") else None, use_container_width=True)

# ------------------------------------------------------------------ Servicios (banda blanca)
# iconos con glifos de Material Symbols: Streamlit sanitiza el <svg> inline, no lo dibuja
ICONO_BARRAS = """
<div class="svc-icon"><span class="material-symbols-rounded">bar_chart</span></div>
"""

# cerebro con la flecha de tendencia por detras
ICONO_CEREBRO = """
<div class="svc-icon">
  <span class="material-symbols-rounded svc-trend">trending_up</span>
  <span class="material-symbols-rounded">neurology</span>
</div>
"""


def servicio(col, key, icono, titulo, cuerpo, cta_label, on_click):
    with col.container(key=key):
        st.html(icono)
        st.markdown(f"### {titulo}")
        st.markdown(cuerpo)
        if st.button(cta_label, key=f"cta_{key}", use_container_width=True):
            on_click()


with st.container(key="sect_white_services"):
    st.html(f"<h2 class='svc-titulo'>{TXT.get('landing_services_title', 'Nuestras soluciones')}</h2>")
    st.html(f"<p class='svc-sub'>{TXT.get('landing_services_sub', '')}</p>")

    s1, s2 = st.columns(2)
    servicio(s1, "svc_pro", ICONO_BARRAS,
             TXT.get("landing_service_pro_title", ""),
             TXT.get("landing_service_pro_body", ""),
             TXT.get("landing_service_pro_cta", "Empezar"), dialog_forecast)
    servicio(s2, "svc_inhouse", ICONO_CEREBRO,
             TXT.get("landing_service_inhouse_title", ""),
             TXT.get("landing_service_inhouse_body", ""),
             TXT.get("landing_service_inhouse_cta", "Hablar con ventas"), dialog_contact_sales)

# ------------------------------------------------------------------ Trust + CTA final (banda gris)
with st.container(key="sect_gray_trust"):
    with st.container(border=True, key="card_trust"):
        st.markdown(f"**{TXT.get('landing_trust_title', '')}**")
        st.caption(TXT.get("landing_trust_body", ""))

    cta("cta_bottom")
    st.caption(TXT.get("app_caption", ""))
