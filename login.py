import streamlit as st
import hashlib
import base64
import os

AUTH_DIR = os.path.dirname(os.path.abspath(__file__))

st.write("Secrets :", st.secrets)
st.write("Keys :", list(st.secrets.keys()))

if "app_password_hash" not in st.secrets:
    st.error("app_password_hash introuvable")
    st.stop()

def _charger_assets():
    with open(os.path.join(AUTH_DIR, "assets/style.css")) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    with open(os.path.join(AUTH_DIR, "assets/logo.png"), "rb") as f:
        return base64.b64encode(f.read()).decode()


def check_password():
    if st.session_state.get("mot_de_passe_correct", False):
        return

    logo_b64 = _charger_assets()

    st.markdown("""
        <style>
        [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none !important; }
        .block-container { padding-top: 5rem; max-width: 480px; }
        </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"""
        <div style="text-align:center; padding: 1rem 0 .5rem 0;">
            <img src='data:image/png;base64,{logo_b64}' height='60'
                 style='background:transparent; box-shadow:none; margin-bottom: 1rem;'/>
            <h1 style="font-family:'DM Sans', sans-serif; font-size:1.4rem; font-weight:800; margin:0;">
                <span style="color:#0B6E72;">Espace</span>
                <span style="color:#D9534F;"> Sécurisé</span>
            </h1>
            <p style="font-size:.85rem; color:#607D7E; margin-top:.3rem;">
                Connectez-vous pour accéder au Dashboard Statistique
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            mot_de_passe = st.text_input(
                "Mot de passe",
                type="password",
                placeholder="Entrez votre mot de passe"
            )
            valider = st.form_submit_button("Se connecter", use_container_width=True)

        if valider:
            saisi_hash = hashlib.sha256(mot_de_passe.encode()).hexdigest()
            if saisi_hash == st.secrets["app_password_hash"]:
                st.session_state["mot_de_passe_correct"] = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")

    st.stop()