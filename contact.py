"""Formulario de acceso beta y de feedback.

Cada envío va a las dos casillas de abajo. El envío automático usa el SMTP de
Zoho: la contraseña NO va en el código, va en secrets (Streamlit Cloud → Settings
→ Secrets):

    [contact]
    smtp_password = "..."          # contraseña de aplicación de Zoho
    # smtp_host = "smtp.zoho.com"  # default
    # smtp_port = 587
    # smtp_user = "brianiboy@intellivet.tech"

Sin esa contraseña el visitante igual puede escribir: el botón abre un mail a
las dos direcciones con lo que completó. Un webhook_url en secrets sigue siendo
un destino extra, opcional.
"""

import json
import re
import smtplib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage

import streamlit as st

import core

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Destino fijo del formulario. Zoho recibe, Gmail va en copia.
DESTINATARIOS = ("brianiboy@intellivet.tech", "brianjosue1900@gmail.com")

# Misma cantidad y el mismo orden en los dos idiomas: el índice es estable.
ROLES = {
    "es": ["Compras", "Planeamiento de demanda", "Operaciones", "Dirección", "Sistemas", "Otro"],
    "en": ["Buying", "Demand planning", "Operations", "Leadership", "IT", "Other"],
}
INDUSTRIAS = {
    "es": ["Retail", "Distribución mayorista", "Manufactura", "Consumo masivo", "Repuestos", "Salud", "Otro"],
    "en": ["Retail", "Wholesale distribution", "Manufacturing", "CPG", "Spare parts", "Health", "Other"],
}
N_SKUS = {
    "es": ["Menos de 100", "100 – 1.000", "1.000 – 10.000", "10.000 – 100.000", "Más de 100.000"],
    "en": ["Under 100", "100 – 1,000", "1,000 – 10,000", "10,000 – 100,000", "Over 100,000"],
}
N_CENTROS = {
    "es": ["1", "2 – 5", "6 – 20", "21 – 100", "Más de 100"],
    "en": ["1", "2 – 5", "6 – 20", "21 – 100", "Over 100"],
}


def email_valido(valor: str) -> bool:
    return bool(_EMAIL.match((valor or "").strip()))


def _bloque() -> dict:
    try:
        crudo = st.secrets.get("contact", {})
    except Exception:
        return {}
    return dict(crudo) if crudo else {}


def email_contacto() -> str:
    return str(_bloque().get("email") or "").strip()


def webhook_url() -> str:
    return str(_bloque().get("webhook_url") or "").strip()


def _url_permitida(url: str) -> bool:
    partes = urllib.parse.urlparse(url)
    host = (partes.hostname or "").lower()
    if partes.scheme == "https" and host:
        return True
    return partes.scheme == "http" and host in {"127.0.0.1", "localhost"}


class _SinSeguirRedirect(urllib.request.HTTPRedirectHandler):
    """Apps Script responde 302 después de aceptar el POST. Seguirlo convierte
    el POST en GET y urllib lo cuenta como error, aunque la fila ya se escribió."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _post(url: str, payload: dict) -> bool:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    opener = urllib.request.build_opener(_SinSeguirRedirect)
    try:
        with opener.open(req, timeout=12) as resp:
            return 200 <= getattr(resp, "status", 200) < 400
    except urllib.error.HTTPError as exc:
        return 200 <= exc.code < 400


def _append_local(payload: dict):
    try:
        with (core.BASE / "contact_submissions.jsonl").open("a", encoding="utf-8") as out:
            out.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _smtp():
    bloque = _bloque()
    return {
        "host": str(bloque.get("smtp_host") or "smtp.zoho.com"),
        "port": int(bloque.get("smtp_port") or 587),
        "user": str(bloque.get("smtp_user") or DESTINATARIOS[0]),
        "password": str(bloque.get("smtp_password") or ""),
    }


def _enviar_smtp(payload: dict):
    """Manda el mismo texto a Zoho y, en copia, a Gmail. Reply-To es quien escribió."""
    cfg = _smtp()
    if not cfg["password"]:
        return False
    asunto = ("IntelliForecast — pedido de acceso" if payload.get("kind") == "beta_access"
              else "IntelliForecast — comentarios")
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = cfg["user"]
    msg["To"] = DESTINATARIOS[0]
    msg["Cc"] = DESTINATARIOS[1]
    if payload.get("email"):
        msg["Reply-To"] = payload["email"]
    msg.set_content(_texto(payload))
    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=20) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(cfg["user"], cfg["password"])
        smtp.send_message(msg)
    return True


def entregar(payload: dict) -> dict:
    """{'status': 'delivered'|'fallback', 'email': str, 'reason': optional}."""
    _append_local(payload)
    email = ", ".join(DESTINATARIOS)
    if _smtp()["password"]:
        try:
            if _enviar_smtp(payload):
                return {"status": "delivered", "email": email}
        except Exception:
            return {"status": "fallback", "email": email, "reason": "failed"}
    url = webhook_url()
    if url and _url_permitida(url):
        try:
            if _post(url, payload):
                return {"status": "delivered", "email": email}
        except Exception:
            pass
    return {"status": "fallback", "email": email, "reason": "missing"}


def _texto(payload: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in payload.items() if v not in ("", None))


def _mailto(email: str, payload: dict) -> str:
    asunto = "IntelliForecast beta" if payload.get("kind") == "beta_access" else "IntelliForecast feedback"
    # las dos casillas van en Para. El espacio después de la coma lo rompe algunos clientes.
    destino = ",".join(parte.strip() for parte in email.split(","))
    return "mailto:" + destino + "?" + urllib.parse.urlencode({"subject": asunto, "body": _texto(payload)})


def mostrar_resultado(resultado: dict, payload: dict):
    TXT = core.txt()
    if resultado["status"] == "delivered":
        st.success(TXT["form_ok"])
        return
    if resultado["status"] == "fallback" and resultado.get("email"):
        clave = "form_fallback_fail" if resultado.get("reason") == "failed" else "form_fallback"
        st.warning(TXT[clave].format(email=resultado["email"]))
        st.link_button(TXT["form_mailto"], _mailto(resultado["email"], payload))
        st.code(_texto(payload))
        return
    st.error(TXT["form_unconfigured"])
    st.code(_texto(payload))


def _base(kind: str) -> dict:
    return {
        "kind": kind,
        "submitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lang": st.session_state.get("lang", "en"),
        "modo": "demo" if core.es_demo() else ("cliente" if st.session_state.get("auth_user") else "visita"),
    }


def _opciones(tabla: dict) -> list[str]:
    lang = st.session_state.get("lang", "en")
    return tabla.get(lang) or tabla["en"]


def formulario_acceso():
    """Pedido de acceso beta / contacto. Lo abren la landing y el aviso de carga del demo."""
    TXT = core.txt()
    st.caption(TXT["form_intro"])
    st.caption(TXT["form_goes_to"])
    with st.form("form_acceso"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input(TXT["form_nombre"])
        email = c2.text_input(TXT["form_email"])
        empresa = c1.text_input(TXT["form_empresa"])
        rol = c2.selectbox(TXT["form_rol"], _opciones(ROLES))
        industria = c1.selectbox(TXT["form_industria"], _opciones(INDUSTRIAS))
        n_skus = c2.selectbox(TXT["form_skus"], _opciones(N_SKUS))
        n_centros = c1.selectbox(TXT["form_centros"], _opciones(N_CENTROS))
        mensaje = st.text_area(TXT["form_mensaje"])
        enviar = st.form_submit_button(TXT["form_enviar"], type="primary", use_container_width=True)
    if enviar:
        if not all(s.strip() for s in (nombre, email, empresa)):
            st.session_state.pop("contact_result_beta", None)
            st.error(TXT["form_error_required"])
            return
        if not email_valido(email):
            st.session_state.pop("contact_result_beta", None)
            st.error(TXT["form_error_email"])
            return
        payload = _base("beta_access") | {
            "nombre": nombre.strip(),
            "email": email.strip(),
            "empresa": empresa.strip(),
            "rol": rol,
            "industria": industria,
            "n_skus": n_skus,
            "n_centros": n_centros,
            "mensaje": mensaje.strip(),
        }
        st.session_state["contact_result_beta"] = (entregar(payload), payload)
    guardado = st.session_state.get("contact_result_beta")
    if guardado:
        mostrar_resultado(*guardado)


def formulario_feedback():
    TXT = core.txt()
    st.caption(TXT["feedback_hint"])
    st.caption(TXT["form_goes_to"])
    with st.form("form_feedback"):
        funciono = st.text_area(TXT["feedback_worked"])
        no_funciono = st.text_area(TXT["feedback_didnt"])
        email = st.text_input(TXT["feedback_email"])
        enviar = st.form_submit_button(TXT["feedback_send"], type="primary", use_container_width=True)
    if enviar:
        if not (funciono.strip() or no_funciono.strip()):
            st.session_state.pop("contact_result_feedback", None)
            st.error(TXT["feedback_need_one"])
            return
        if email.strip() and not email_valido(email):
            st.session_state.pop("contact_result_feedback", None)
            st.error(TXT["form_error_email"])
            return
        payload = _base("feedback") | {
            "email": email.strip(),
            "que_funciono": funciono.strip(),
            "que_no_funciono": no_funciono.strip(),
            "vista": st.session_state.get("forecast_view") or "hub",
        }
        st.session_state["contact_result_feedback"] = (entregar(payload), payload)
    guardado = st.session_state.get("contact_result_feedback")
    if guardado:
        mostrar_resultado(*guardado)
