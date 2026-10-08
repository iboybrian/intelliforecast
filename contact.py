"""Formulario de acceso beta y de feedback.

La entrega no tiene credenciales en el código. En `.streamlit/secrets.toml`
(en Streamlit Cloud, la UI de Secrets):

    [contact]
    email = "equipo@ejemplo.com"          # fallback visible si no hay webhook
    webhook_url = "https://..."           # opcional. POST JSON. HTTPS
                                          # (http solo en localhost, para probar)

Sin webhook, el visitante ve el email y un mailto con lo que escribió.
Sin email ni webhook, un aviso pide configurar secrets — no se inventa una dirección.
Cada envío válido se agrega además a contact_submissions.jsonl (gitignoreado):
sirve para probar en local; en Community Cloud ese archivo no le llega a nadie.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import streamlit as st

import core

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

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


def entregar(payload: dict) -> dict:
    """{'status': 'delivered'|'fallback'|'unconfigured', 'email': str}."""
    _append_local(payload)
    url = webhook_url()
    email = email_contacto()
    if url and _url_permitida(url):
        try:
            if _post(url, payload):
                return {"status": "delivered", "email": email}
        except Exception:
            pass
        return {"status": "fallback" if email else "unconfigured", "email": email, "reason": "failed"}
    if email:
        return {"status": "fallback", "email": email, "reason": "missing"}
    return {"status": "unconfigured", "email": ""}


def _texto(payload: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in payload.items() if v not in ("", None))


def _mailto(email: str, payload: dict) -> str:
    asunto = "IntelliForecast beta" if payload.get("kind") == "beta_access" else "IntelliForecast feedback"
    return "mailto:" + email + "?" + urllib.parse.urlencode({"subject": asunto, "body": _texto(payload)})


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
