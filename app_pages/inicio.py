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
/* ---- barrido de brillo: solo los 2 CTA del hero y el CTA de cierre ----
   Selector por key explicito: con el prefijo generico `st-key-cta_` tambien
   caerian los botones de "Nuestras soluciones", que van planos. */
[class*="st-key-cta_hero_start"] button,
[class*="st-key-cta2_hero_contact"] button,
[class*="st-key-cta_bottom"] button,
[class*="st-key-cta_svc"] button {{
    position: relative;
    overflow: hidden;
    isolation: isolate;
    transition: box-shadow 0.35s ease, transform 0.2s ease;
}}
[class*="st-key-cta_hero_start"] button::before,
[class*="st-key-cta2_hero_contact"] button::before,
[class*="st-key-cta_bottom"] button::before,
[class*="st-key-cta_svc"] button::before {{
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(115deg,
        transparent 26%, rgba(255,255,255,0.55) 32%, rgba(255,255,255,0.55) 36%, transparent 42%,
        transparent 48%, rgba(255,255,255,0.55) 54%, rgba(255,255,255,0.55) 58%, transparent 64%);
    transform: translateX(-120%);
    pointer-events: none;
}}
/* el flip a naranja del hover generico pelea con el brillo: estos mantienen su color */
[class*="st-key-cta_hero_start"] button:hover,
[class*="st-key-cta_bottom"] button:hover,
[class*="st-key-cta_svc"] button:hover {{
    background-color: {ACCENT_CYAN} !important;
}}
[class*="st-key-cta_hero_start"] button:hover,
[class*="st-key-cta2_hero_contact"] button:hover {{
    box-shadow: 0 0 18px rgba(255,255,255,0.35), 0 0 4px rgba(255,255,255,0.6);
    transform: translateY(-1px);
}}
/* el glow blanco no se ve sobre banda clara: esos van con glow azul */
[class*="st-key-cta_bottom"] button:hover,
[class*="st-key-cta_svc"] button:hover {{
    box-shadow: 0 0 18px rgba(15,76,129,0.45), 0 0 4px rgba(15,76,129,0.6);
    transform: translateY(-1px);
}}
[class*="st-key-cta_hero_start"] button:hover::before,
[class*="st-key-cta2_hero_contact"] button:hover::before,
[class*="st-key-cta_bottom"] button:hover::before,
[class*="st-key-cta_svc"] button:hover::before {{
    animation: cta-sweep 1.94s linear infinite;
}}
@keyframes cta-sweep {{
    0% {{ transform: translateX(-120%); }}
    37.11% {{ transform: translateX(120%); }}
    74.23% {{ transform: translateX(-120%); }}
    100% {{ transform: translateX(-120%); }}
}}
/* sin esto el gradiente del barrido tapa el texto y el icono */
[class*="st-key-cta_hero_start"] button *,
[class*="st-key-cta2_hero_contact"] button *,
[class*="st-key-cta_bottom"] button *,
[class*="st-key-cta_svc"] button * {{
    position: relative;
    z-index: 1;
}}
/* fade-in de toda la pagina al cargar */
.stMainBlockContainer {{
    animation: page-fade-in 0.8s ease-out both;
}}
@keyframes page-fade-in {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to {{ opacity: 1; transform: none; }}
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
/* sin esto el boton estira para llenar la columna y queda mas alto que el otro.
   El flex centra la etiqueta: con height fija el texto queda pegado arriba. */
[class*="st-key-cta_svc"] button {{
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
}}
/* el label de Streamlit se estira a toda la altura y deja el texto pegado arriba:
   se centra en cada nivel (contenedor del markdown y el parrafo).
   OJO: nada de tags HTML en estos comentarios. Un tag literal (por ejemplo el de
   parrafo, entre angulos) hace que Streamlit descarte TODO el bloque de estilos
   y la landing queda sin CSS, sin error ni aviso. */
[class*="st-key-cta_svc"] button [data-testid="stMarkdownContainer"] {{
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    width: 100%;
}}
[class*="st-key-cta_svc"] button p {{
    margin: 0;
    line-height: 1.2;
    /* el min-height del cuerpo de la tarjeta (3.4rem) tambien caia sobre el label */
    min-height: 0 !important;
}}
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
    /* la foto del equipo llena la banda de arriba a abajo: la banda pierde el padding
       vertical, las columnas se estiran y la imagen recorta con object-fit */
    [class*="st-key-sect_white_team"] {{
        padding-top: 0;
        padding-bottom: 0;
        min-height: 460px;
    }}
    [class*="st-key-sect_white_team"] [data-testid="stHorizontalBlock"] {{
        min-height: 460px;
        align-items: stretch;
    }}
    /* el texto sigue centrado aunque su columna ahora se estire */
    [class*="st-key-sect_white_team"] [data-testid="stColumn"]:first-child [data-testid="stVerticalBlock"] {{
        height: 100%;
        justify-content: center;
    }}
    /* cadena flex, no `height: 100%`: contra un padre que solo tiene min-height el
       porcentaje cae a auto y ademas rompe el stretch de la columna */
    [class*="st-key-sect_white_team"] [data-testid="stColumn"]:last-child,
    [class*="st-key-sect_white_team"] [data-testid="stColumn"]:last-child [data-testid="stVerticalBlock"],
    [class*="st-key-sect_white_team"] [data-testid="stColumn"]:last-child [data-testid="stElementContainer"],
    [class*="st-key-sect_white_team"] [data-testid="stColumn"]:last-child [data-testid="stFullScreenFrame"],
    [class*="st-key-sect_white_team"] [data-testid="stColumn"]:last-child [data-testid="stFullScreenFrame"] > div,
    [class*="st-key-sect_white_team"] [data-testid="stColumn"]:last-child [data-testid="stImage"],
    [class*="st-key-sect_white_team"] [data-testid="stColumn"]:last-child [data-testid="stImageContainer"] {{
        display: flex;
        flex-direction: column;
        flex: 1 1 auto;
        min-height: 0;
    }}
    [class*="st-key-sect_white_team"] img {{
        flex: 1 1 auto;
        width: 100%;
        min-height: 0;
        object-fit: cover;
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
    # sin vertical_alignment: la columna tiene que estirarse para que la foto llene la banda;
    # el texto se centra por CSS
    side_txt, side_img = st.columns([1, 1])
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

    # capturas por idioma: las viejas estan en español, las nuevas en ingles
    if st.session_state.get("lang", "en") == "es":
        capturas = ("dashboard.png", "quiebre.png", "exceso.png")
    else:
        capturas = ("dashboardenglish.png", "stockouts.png", "overstock.png")
    dashboard_path, quiebre_path, exceso_path = (core.BASE / "assets" / n for n in capturas)

    if dashboard_path.exists():
        st.image(str(dashboard_path), use_container_width=True)
        st.caption(TXT.get("landing_dashboard_caption", ""))
    else:
        st.info(TXT.get("landing_dashboard_caption", ""), icon=":material/image:")

    g1, g2 = st.columns(2)
    with g1:
        if quiebre_path.exists():
            st.image(str(quiebre_path), caption=TXT.get("tab_risk"), use_container_width=True)
    with g2:
        if exceso_path.exists():
            st.image(str(exceso_path), caption=TXT.get("tab_overstock"), use_container_width=True)

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
