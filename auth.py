"""Login por perfil — puerta de entrada al dashboard.

Los perfiles viven en `.streamlit/secrets.toml` (ya gitignoreado; en Streamlit Cloud
es la UI de Secrets, que es donde se crean/borran sin tocar codigo):

    [users.premiumpet]
    hash = "scrypt$16384$8$1$<salt_b64>$<hash_b64>"   # generado con: python auth.py nuevo premiumpet
    url  = "app_pages/forecast.py"                     # o "https://otro-demo.streamlit.app"

La contrasena NUNCA se guarda: solo el derivado scrypt con salt por usuario, comparado
con hmac.compare_digest. `url` es el destino propio de cada perfil: una ruta de pagina
(st.switch_page) o un link externo (boton de continuar).

Self-check:  python auth.py --check
"""

import base64
import hashlib
import hmac
import secrets as _secrets
import sys
import time

import streamlit as st

import core

# scrypt: n=2**14 -> ~16 MB y ~0.1 s por intento. Subir n encarece el ataque offline
# si alguna vez se filtra el secrets.toml (y tambien el login, ojo).
SCRYPT = {"n": 2**14, "r": 8, "p": 1}
DKLEN = 32
MAX_INTENTOS = 5          # por sesion: frena fuerza bruta casual, no a alguien que reconecta
BLOQUEO_SEG = 60
DESTINO_DEFAULT = "app_pages/forecast.py"

_b64 = lambda b: base64.b64encode(b).decode()
_ub64 = base64.b64decode


def hash_password(pw: str, salt: bytes | None = None) -> str:
    salt = salt or _secrets.token_bytes(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, dklen=DKLEN, **SCRYPT)
    return f"scrypt${SCRYPT['n']}${SCRYPT['r']}${SCRYPT['p']}${_b64(salt)}${_b64(dk)}"


def verify(pw: str, guardado: str) -> bool:
    """Compara sin ramificar por el resultado: cualquier hash mal formado es simplemente False."""
    try:
        alg, n, r, p, salt, esperado = guardado.split("$")
        if alg != "scrypt":
            return False
        esperado = _ub64(esperado)
        dk = hashlib.scrypt(pw.encode(), salt=_ub64(salt), n=int(n), r=int(r), p=int(p),
                            dklen=len(esperado))
    except Exception:
        return False
    return hmac.compare_digest(dk, esperado)


# se quema el mismo tiempo con un usuario inexistente que con uno real: sin esto, la
# latencia de la respuesta dice si el usuario existe (enumeracion de perfiles).
_DUMMY = hash_password(_b64(_secrets.token_bytes(16)))


def perfiles() -> dict:
    """{usuario: {hash, url}} desde secrets. Sin secrets.toml -> {} (la app no revienta)."""
    try:
        return dict(st.secrets.get("users", {}))
    except Exception:
        return {}


def autenticar(usuario: str, password: str) -> dict | None:
    perfil = perfiles().get(usuario.strip())
    if perfil is None:
        verify(password, _DUMMY)
        return None
    return dict(perfil) if verify(password, perfil.get("hash", "")) else None


# --------------------------------------------------------------------- sesion
# ponytail: la sesion vive en st.session_state, o sea que un F5 obliga a entrar de nuevo.
# Si molesta, guardar un token firmado en cookie (st.context.cookies es de solo lectura:
# haria falta un componente) o pasar a st.login() con un proveedor OIDC.
def ok() -> bool:
    return bool(st.session_state.get("auth_user"))


def destino() -> str:
    return st.session_state.get("auth_destino") or DESTINO_DEFAULT


def logout():
    for k in ("auth_user", "auth_destino", "mostrar_login"):
        st.session_state.pop(k, None)


def ir_a_destino():
    """Ruta interna -> switch_page. Link externo -> boton (una redireccion automatica
    necesitaria JS, que Streamlit sanea)."""
    url = destino()
    if url.startswith("http"):
        TXT = core.txt()
        st.success(TXT["auth_bienvenida"].format(u=st.session_state["auth_user"]))
        st.link_button(TXT["auth_continuar"], url, type="primary", use_container_width=True)
    else:
        st.switch_page(url)


# --------------------------------------------------------------------- UI
def login_form(key: str = "login") -> bool:
    """Dibuja el formulario. -> True solo en el rerun en que el login fue correcto."""
    TXT = core.txt()
    if not perfiles():
        st.error(TXT["auth_sin_perfiles"])
        st.code("python auth.py nuevo <usuario>")
        return False

    resta = st.session_state.get("auth_bloqueo", 0) - time.time()
    if resta > 0:
        st.error(TXT["auth_bloqueado"].format(s=int(resta) + 1))
        return False

    with st.form(key):
        st.markdown(f"#### {TXT['auth_titulo']}")
        usuario = st.text_input(TXT["auth_usuario"], autocomplete="username")
        password = st.text_input(TXT["auth_password"], type="password", autocomplete="current-password")
        enviar = st.form_submit_button(TXT["auth_entrar"], type="primary", use_container_width=True)
    if not enviar:
        return False

    perfil = autenticar(usuario, password)
    if perfil is None:
        intentos = st.session_state.get("auth_intentos", 0) + 1
        st.session_state["auth_intentos"] = intentos
        if intentos >= MAX_INTENTOS:
            st.session_state["auth_bloqueo"] = time.time() + BLOQUEO_SEG
            st.session_state["auth_intentos"] = 0
        st.error(TXT["auth_error"])           # mismo mensaje para usuario y clave malos
        return False

    st.session_state["auth_intentos"] = 0
    st.session_state["auth_user"] = usuario.strip()
    st.session_state["auth_destino"] = perfil.get("url", DESTINO_DEFAULT)
    return True


def pantalla_login():
    """Version pagina completa del formulario (la usa el guard de app.py cuando alguien
    entra a /forecast por URL directa, sin pasar por el dialogo de la landing)."""
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        if login_form("login_pagina"):
            ir_a_destino()


def sidebar_sesion():
    TXT = core.txt()
    if ok():
        st.sidebar.caption(TXT["auth_sesion"].format(u=st.session_state["auth_user"]))
        if st.sidebar.button(TXT["auth_salir"], key="btn_logout"):
            logout()
            st.rerun()


# --------------------------------------------------------------------- CLI
def _check():
    h = hash_password("correcto caballo bateria grapa")
    assert verify("correcto caballo bateria grapa", h)
    assert not verify("Correcto caballo bateria grapa", h)
    assert not verify("", h)
    assert not verify("correcto caballo bateria grapa", h[:-4] + "AAAA")   # hash alterado
    assert not verify("x", "md5$1$2$3$4$5")                                # algoritmo ajeno
    assert not verify("x", "basura")
    assert hash_password("misma") != hash_password("misma")                # salt por hash
    print("auth.py OK")


if __name__ == "__main__":
    if "--check" in sys.argv:
        _check()
    elif len(sys.argv) >= 3 and sys.argv[1] == "nuevo":
        import getpass

        usuario = sys.argv[2]
        url = sys.argv[3] if len(sys.argv) > 3 else DESTINO_DEFAULT
        pw = getpass.getpass(f"Contrasena para '{usuario}': ")
        if pw != getpass.getpass("Repetir: "):
            sys.exit("no coinciden")
        if len(pw) < 10:
            sys.exit("minimo 10 caracteres")
        print(f'\nPegar en .streamlit/secrets.toml (o en Secrets de Streamlit Cloud):\n\n'
              f'[users.{usuario}]\nhash = "{hash_password(pw)}"\nurl  = "{url}"')
    else:
        sys.exit("uso: python auth.py nuevo <usuario> [url] | python auth.py --check")
