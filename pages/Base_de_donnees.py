import streamlit as st
import base64
import os
from db import (
    recuperer_etudiants, recuperer_matieres, recuperer_notes,
    recuperer_notes_etudiant, recuperer_moyenne_generale,
    recuperer_moyenne_classe, recuperer_classes,
    recuperer_absences, recuperer_absences_etudiant,
    recuperer_predictions
)
from login import check_password
check_password()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE_DIR, "assets/style.css")) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

with open(os.path.join(BASE_DIR, "assets/logo.png"), "rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<div style="
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 0 .5rem 0;
    border-bottom: 2px solid;
    border-image: linear-gradient(90deg, #0B6E72, #D9534F) 1;
    margin-bottom: 1.5rem;
">
    <img src='data:image/png;base64,{logo_b64}' height='55'
         style='background:transparent; border-radius:0; box-shadow:none;'/>
    <div style='text-align:right;'>
        <h1 style='
            font-family: DM Sans, sans-serif;
            font-size: 1.6rem;
            font-weight: 800;
            margin: 0;
            letter-spacing: -.5px;
        '>
            <span style='color:#0B6E72;'>Base de</span>
            <span style='color:#D9534F;'> Données</span>
        </h1>
        <p style='font-size:.82rem; color:#607D7E; margin:0;'>
           Historique des étudiants, notes, absences et prédictions
        </p>
    </div>
</div>
""", unsafe_allow_html=True)


tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    ["Étudiants", "Matières", "Notes", "Évolution", "Classe", "Absences", "Prédictions"]
)

with tab1:
    st.dataframe(recuperer_etudiants())

with tab2:
    st.dataframe(recuperer_matieres())

with tab3:
    st.dataframe(recuperer_notes())

with tab4:
    st.subheader("Évolution des notes par étudiant")

    liste_etudiants = recuperer_etudiants()["nom"].tolist()

    if liste_etudiants:
        nom_choisi = st.selectbox("Choisir un étudiant", liste_etudiants)

        st.subheader("Moyenne générale par semestre")
        df_moyenne = recuperer_moyenne_generale(nom_choisi)
        if len(df_moyenne) > 1:
            st.line_chart(df_moyenne.set_index("date_evaluation")["moyenne"])
        else:
            st.info("Pas assez de relevés pour tracer une évolution (il faut au moins 2 dates différentes).")

        st.subheader("Détail par matière")
        df_evolution = recuperer_notes_etudiant(nom_choisi)

        if df_evolution.empty:
            st.info("Aucune note enregistrée pour cet étudiant.")
        else:
            st.dataframe(df_evolution)
    else:
        st.info("Aucun étudiant dans la base pour le moment.")


with tab5:
    st.subheader("Évolution de la moyenne par classe")

    liste_classes = recuperer_classes()

    if liste_classes:
        classe_choisie = st.selectbox("Choisir une classe", liste_classes)

        df_classe = recuperer_moyenne_classe(classe_choisie)

        if len(df_classe) > 1:
            st.line_chart(df_classe.set_index("date_evaluation")["moyenne_classe"])
            st.dataframe(df_classe)
        elif len(df_classe) == 1:
            st.info("Une seule date enregistrée pour l'instant — importe un second relevé à une date différente pour voir une évolution.")
    else:
        st.info("Aucune classe enregistrée dans la base pour le moment.")


with tab6:
    st.subheader("Absences par étudiant")

    liste_etudiants = recuperer_etudiants()["nom"].tolist()

    if liste_etudiants:
        nom_choisi = st.selectbox("Choisir un étudiant", liste_etudiants, key="select_absences")

        df_abs = recuperer_absences_etudiant(nom_choisi)

        if df_abs.empty:
            st.info("Aucune absence enregistrée pour cet étudiant.")
        else:
            st.dataframe(df_abs)
            if len(df_abs) > 1:
                st.line_chart(df_abs.set_index("date_releve")["nombre_absences"])
    else:
        st.info("Aucun étudiant dans la base pour le moment.")

    st.markdown("---")
    st.subheader("Toutes les absences")
    st.dataframe(recuperer_absences())


with tab7:
    st.subheader("Historique des résultats de prédiction")
    st.dataframe(recuperer_predictions())


if st.sidebar.button("Déconnexion"):
    st.session_state["mot_de_passe_correct"] = False
    st.rerun()
