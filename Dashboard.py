import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from fpdf import FPDF
import base64
import tempfile, os
from db import ajouter_etudiant, ajouter_matiere, ajouter_note ,ajouter_absence

from login import check_password
check_password()

BASE_DIR = os.path.dirname(__file__)

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
            <span style='color:#0B6E72;'>Dashboard</span>
            <span style='color:#D9534F;'> Statistique</span>
        </h1>
        <p style='font-size:.82rem; color:#607D7E; margin:0;'>
            Visualisation automatique des moyennes, absences et résultats
        </p>
    </div>
</div>
""", unsafe_allow_html=True)


choix = st.sidebar.selectbox("Choisir le type de donnees:", ['Moyennes', 'Absences'])
fichier = st.sidebar.file_uploader("Déposer le fichier", type=["csv", "xlsx"])

if fichier is None:
    st.markdown("""
    <div style='text-align:center; padding: 3rem 1rem; color: #607D7E;'>
        <h3 style='color: #0B6E72; margin-bottom: .5rem;'>Commencez par déposer un fichier</h3>
        <p style='font-size: .95rem;'>
            Utilisez le menu latéral pour choisir le type de données<br>
            et déposer votre fichier CSV ou Excel.
        </p>
    </div>
    """, unsafe_allow_html=True)

if fichier is not None:
    try:
        if fichier.name.endswith(".csv"):
            df = pd.read_csv(fichier)
        else:
            df = pd.read_excel(fichier)
    except Exception as e:
        st.error(f"Impossible de lire le fichier : {e}")
        st.stop()

    # L'admin choisit la colonne representant la valeur a analyser
    colonne_valeur = st.sidebar.selectbox("Quelle colonne représente les valeurs à analyser ?", df.columns)

    # L'admin choisit la colonne contenant les noms/identifiants
    colonne_nom = st.sidebar.selectbox("Quelle colonne représente les noms des étudiants ?", df.columns)

    if colonne_valeur == colonne_nom:
        st.sidebar.warning("Merci de choisir deux colonnes différentes pour les noms et les valeurs.")
        st.stop()

    if "dernier_choix" not in st.session_state:
        st.session_state["dernier_choix"] = choix

    if choix != st.session_state["dernier_choix"]:
        st.session_state["Afficher"] = False
        st.session_state["dernier_choix"] = choix

    if choix == "Moyennes":

        # les valeurs texte => NaN automatiquement
        df[colonne_valeur] = pd.to_numeric(df[colonne_valeur], errors='coerce')

        # Compter les cellules texte converties en NaN
        nbr_texte = df[colonne_valeur].isnull().sum()
        if nbr_texte > 0:
            st.sidebar.warning(f"{nbr_texte} cellule(s) contenant du texte détectée(s)")

        with st.sidebar.expander("Détails du nettoyage des données"):
            st.warning(f"{nbr_texte} valeur(s) manquante(s) détectée(s) dans la colonne « {colonne_valeur} »")

        # traitement des valeurs manquantes
        remplacer = ""
        if nbr_texte != 0:
            remplacer = st.sidebar.selectbox("Comment souhaitez-vous traiter les valeurs manquantes ?", ['La moyen', 'remplacer par 0', 'Supprimer la ligne'])

        if remplacer == "La moyen":
            df[colonne_valeur] = df[colonne_valeur].fillna(df[colonne_valeur].mean())

        elif remplacer == "remplacer par 0":
            df[colonne_valeur] = df[colonne_valeur].fillna(0)

        elif remplacer == "Supprimer la ligne":
            df = df.dropna(subset=[colonne_valeur])


        # Telecharger les donnees nettoyes
        st.write(
            "Le fichier ci-dessous contient les données nettoyées (valeurs aberrantes et manquantes traitées). Cliquez pour le télécharger :")

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Télécharger (format csv)",
            data=csv,
            file_name="moyennes.csv",
            mime="text/csv"
        )

        # Base de donnee
        date_eval = st.sidebar.date_input("Date de cette évaluation")
        classe_etudiants = st.sidebar.text_input("Classe (ex: DS3A)")

        if st.button("Enregistrer dans la base de données"):
            ajouter_matiere(colonne_valeur)
            for _, ligne in df.iterrows():
                nom_etudiant = ligne[colonne_nom]
                note = ligne[colonne_valeur]
                ajouter_etudiant(nom_etudiant, classe_etudiants)
                ajouter_note(nom_etudiant, colonne_valeur, note, date_eval)
            st.success(f"{len(df)} étudiant(s) enregistré(s) dans la base.")


        seuil = st.sidebar.number_input("Veuillez entrer le seuil de réussite: ", min_value=0.0)

        if "Afficher" not in st.session_state:
            st.session_state["Afficher"] = False

        if st.sidebar.button("Afficher"):
            st.session_state["Afficher"] = True

        if st.session_state["Afficher"]:

            # Filtre
            st.subheader("Filtrer par intervalle: ")
            min_val, max_val = st.slider(
                "",
                min_value=float(df[colonne_valeur].min()),
                max_value=float(df[colonne_valeur].max()),
                value=(float(df[colonne_valeur].min()), float(df[colonne_valeur].max()))
            )

            df = df[(df[colonne_valeur] >= min_val) & (df[colonne_valeur] <= max_val)]

            # Statistiques générales
            st.subheader("Statistiques Générales: ")
            col1, col2, col3 = st.columns(3)
            col1.metric("Nombre des étudiants", len(df))
            col2.metric("Moyenne générales", round(df[colonne_valeur].mean(), 2))
            col3.metric("Note maximale", round(df[colonne_valeur].max(), 2))

            # Histogramme
            st.subheader("Répartition des Valeurs:")
            fig1, ax = plt.subplots()
            ax.hist(df[colonne_valeur], bins=10, color='#0B6E72', edgecolor='white')
            ax.set_xlabel(colonne_valeur)
            ax.set_ylabel("Nombre d'étudiants")
            st.pyplot(fig1)

            # Telechargement d'histogramme
            buffer = io.BytesIO()
            fig1.savefig(buffer, format="png")
            st.download_button(
                label="Télécharger le graphe (format png)",
                data=buffer.getvalue(),
                file_name="Histogramme.png",
                mime="image/png"
            )

            # Classement
            st.subheader("Classement:")
            df_sorted = df.sort_values(by=colonne_valeur, ascending=False)
            fig2, ax2 = plt.subplots(figsize=(8, 6))
            ax2.barh(df_sorted[colonne_nom], df_sorted[colonne_valeur], color='#0B6E72', height=0.4)
            ax2.set_xlabel(colonne_valeur)
            ax2.invert_yaxis()
            fig2.tight_layout()
            st.pyplot(fig2)

            # Telechargement
            buffer = io.BytesIO()
            fig2.savefig(buffer, format="png")
            st.download_button(
                label="Télécharger le graphe (format png)",
                data=buffer.getvalue(),
                file_name="Classement.png",
                mime="image/png"
            )

            # échec et réussite
            st.subheader("Pourcentage de réussite et d'échec:")
            count = (df[colonne_valeur] >= seuil).map({True: "Réussite", False: "Échec"}).value_counts()
            color_map = {"Réussite": "#0B6E72", "Échec": "#E63946"}
            colors = [color_map[label] for label in count.index]
            fig3, ax = plt.subplots()
            ax.pie(count, labels=count.index, autopct='%1.1f%%',
                   colors=colors)
            st.pyplot(fig3)

            # Telechargement
            buffer = io.BytesIO()
            fig3.savefig(buffer, format="png")
            st.download_button(
                label="Télécharger le graphe (format png)",
                data=buffer.getvalue(),
                file_name="Echec_reussite.png",
                mime="image/png"
            )

            pdf = FPDF()
            pdf.set_auto_page_break(True, 15)
            pdf.add_page()

            pdf.set_fill_color(184, 187, 146)
            pdf.rect(0, 0, 210, 60, "F")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(base64.b64decode(logo_b64))
                tmp_logo = tmp.name
            pdf.image(tmp_logo, x=140, y=0, w=50)
            os.unlink(tmp_logo)

            pdf.set_draw_color(255, 255, 255)
            pdf.set_line_width(0.4)
            pdf.line(130, 8, 130, 52)

            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 30)
            pdf.set_xy(15, 12)
            pdf.multi_cell(110, 12, "Rapport\nStatistique")

            pdf.set_font("Helvetica", "", 13)
            pdf.set_xy(15, 40)
            pdf.cell(100, 8, "Dashboard d'analyse des notes")


            pdf.ln(35)
            pdf.set_text_color(40, 40, 40)
            pdf.set_font("Helvetica", "B", 20)
            pdf.cell(0, 12, "À propos du rapport", ln=True)
            pdf.ln(3)
            pdf.set_font("Helvetica", "", 11)
            texte = (
                "Ce rapport présente une analyse complète des résultats des étudiants. "
                "Il contient les statistiques générales, les indicateurs de performance "
                "ainsi que plusieurs visualisations permettant d'interpréter rapidement les données."
            )
            pdf.multi_cell(0, 7, texte)
            pdf.ln(10)


            y_boxes = pdf.get_y()

            pdf.set_fill_color(248, 245, 238)
            pdf.rect(15, y_boxes, 85, 35, "F")
            pdf.rect(110, y_boxes, 85, 35, "F")

            # Encadré gauche : Nombre étudiants
            pdf.set_xy(20, y_boxes + 5)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(75, 5, "NOMBRE D'ÉTUDIANTS", ln=True)
            pdf.set_xy(20, y_boxes + 12)
            pdf.set_font("Helvetica", "B", 22)
            pdf.set_text_color(11, 110, 114)
            pdf.cell(75, 10, str(len(df)), ln=True)
            pdf.set_xy(20, y_boxes + 24)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(75, 5, f"Colonne analysée : {colonne_valeur}")

            # Encadré droit : Moyenne générale
            pdf.set_xy(115, y_boxes + 5)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(75, 5, "MOYENNE GÉNÉRALE", ln=True)
            pdf.set_xy(115, y_boxes + 12)
            pdf.set_font("Helvetica", "B", 22)
            pdf.set_text_color(217, 83, 79)
            pdf.cell(75, 10, str(round(df[colonne_valeur].mean(), 2)), ln=True)
            pdf.set_xy(115, y_boxes + 24)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(75, 5, f"Note max : {df[colonne_valeur].max()} / Note min : {df[colonne_valeur].min()}")

            pdf.ln(45)

            pdf.set_text_color(40, 40, 40)
            pdf.set_font("Helvetica", "B", 18)
            pdf.cell(0, 10, "Statistiques générales", ln=True)
            pdf.set_draw_color(220, 220, 220)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.ln(8)

            # Tableau statistiques
            stats = [
                ("Nombre d'étudiants", str(len(df))),
                ("Moyenne générale", str(round(df[colonne_valeur].mean(), 2))),
                ("Note maximale", str(df[colonne_valeur].max())),
                ("Note minimale", str(round(df[colonne_valeur].min(), 2))),
                ("Écart-type", str(round(df[colonne_valeur].std(), 2))),
                ("Médiane", str(round(df[colonne_valeur].median(), 2))),
            ]

            for i, (label, value) in enumerate(stats):
                x = 15 if i % 2 == 0 else 110
                if i % 2 == 0 and i > 0:
                    pdf.ln(16)
                pdf.set_xy(x, pdf.get_y())
                pdf.set_fill_color(230, 244, 245)
                pdf.rect(x, pdf.get_y(), 88, 13, "F")
                pdf.set_xy(x + 3, pdf.get_y() + 2)
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(50, 4, label.upper())
                pdf.set_xy(x + 3, pdf.get_y() + 4)
                pdf.set_font("Helvetica", "B", 13)
                pdf.set_text_color(11, 110, 114)
                pdf.cell(50, 6, value)

            pdf.ln(20)

            pdf.add_page()

            pdf.set_fill_color(11, 110, 114)
            pdf.rect(0, 0, 210, 6, "F")
            pdf.ln(12)

            pdf.set_text_color(40, 40, 40)
            pdf.set_font("Helvetica", "B", 18)
            pdf.cell(0, 10, "Visualisations", ln=True)
            pdf.set_draw_color(220, 220, 220)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.ln(8)

            # Histogramme
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(0, 7, "Répartition des valeurs (Histogramme)", ln=True)
            pdf.ln(2)
            buffer_hist = io.BytesIO()
            fig1.savefig(buffer_hist, format="png", bbox_inches="tight", dpi=150)
            buffer_hist.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(buffer_hist.read())
                tmp_hist = tmp.name
            pdf.image(tmp_hist, x=15, w=180)
            os.unlink(tmp_hist)
            pdf.ln(8)

            # Classement — Page 3
            pdf.add_page()
            pdf.set_fill_color(11, 110, 114)
            pdf.rect(0, 0, 210, 6, "F")
            pdf.ln(12)

            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(0, 7, "Classement des étudiants", ln=True)
            pdf.ln(2)
            buffer_class = io.BytesIO()
            fig2.savefig(buffer_class, format="png", bbox_inches="tight", dpi=150)
            buffer_class.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(buffer_class.read())
                tmp_class = tmp.name
            pdf.image(tmp_class, x=15, w=180)
            os.unlink(tmp_class)
            pdf.ln(10)

            # Camembert
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, "Pourcentage de réussite et d'échec", ln=True)
            pdf.ln(2)
            buffer_reus = io.BytesIO()
            fig3.savefig(buffer_reus, format="png", bbox_inches="tight", dpi=150)
            buffer_reus.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(buffer_reus.read())
                tmp_reus = tmp.name
            pdf.image(tmp_reus, x=40, w=120)
            os.unlink(tmp_reus)

            pdf_bytes = bytes(pdf.output())
            st.download_button(
                label="Télécharger le rapport complet",
                data=pdf_bytes,
                file_name="rapport_moyennes.pdf",
                mime="application/pdf"
            )

            plt.close(fig1)
            plt.close(fig2)
            plt.close(fig3)

    if (choix == "Absences"):
        # les valeurs texte → NaN automatiquement
        df[colonne_valeur] = pd.to_numeric(df[colonne_valeur], errors='coerce')

        # Valeurs manquantes
        nbr_val_manq = df[colonne_valeur].isnull().sum()

        if nbr_val_manq != 0:
            df[colonne_valeur] = df[colonne_valeur].fillna(0)

        with st.sidebar.expander("Détails du nettoyage des données"):
            st.warning(f" {nbr_val_manq} valeur(s) manquante(s) détectée(s) pour les absences")
            st.info(" Les valeurs manquantes ont été remplacées par 0 (aucune absence enregistrée)")

        # Telecharger les donnees nettoyes
        st.write(
            "Le fichier ci-dessous contient les données nettoyées (valeurs aberrantes et manquantes traitées). Cliquez pour le télécharger :")

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Télécharger (format csv)",
            data=csv,
            file_name="absences.csv",
            mime="text/csv"
        )

        classe_etudiants = st.sidebar.text_input("Classe (ex: DS3A)", key="classe_absences")
        date_releve = st.sidebar.date_input("Date de ce relevé d'absences", key="date_absences")

        if st.button("Enregistrer les absences dans la base", key="enregistrer_absences"):
            for _, ligne in df.iterrows():
                nom_etudiant = ligne[colonne_nom]
                nb_absences = ligne[colonne_valeur]
                ajouter_etudiant(nom_etudiant, classe_etudiants)
                ajouter_absence(nom_etudiant, nb_absences, date_releve)
            st.success(f"{len(df)} étudiant(s) enregistré(s) dans la base.")

        # Affichage
        if "Afficher" not in st.session_state:
            st.session_state["Afficher"] = False

        if st.sidebar.button("Afficher"):
            st.session_state["Afficher"] = True

        if st.session_state["Afficher"]:

            # Filtre
            st.subheader("Filtrer par intervalle: ")
            min_val, max_val = st.slider(
                "",
                min_value=float(df[colonne_valeur].min()),
                max_value=float(df[colonne_valeur].max()),
                value=(float(df[colonne_valeur].min()), float(df[colonne_valeur].max()))
            )

            df = df[(df[colonne_valeur] >= min_val) & (df[colonne_valeur] <= max_val)]

            # Statistiques générales
            st.subheader("Statistiques générales:")
            col1, col2, col3 = st.columns(3)
            col1.metric("Nombre des étudiants", len(df))
            col2.metric("Moyenne d'absances", round(df[colonne_valeur].mean(), 2))

            # Histogramme
            st.subheader("Répartition des Valeurs:")
            fig1, ax = plt.subplots()
            ax.hist(df[colonne_valeur], bins=10, color='#0B6E72', edgecolor='white')
            ax.set_xlabel(colonne_valeur)
            ax.set_ylabel("Nombre d'étudiants")
            st.pyplot(fig1)

            # Telechargement
            buffer = io.BytesIO()
            fig1.savefig(buffer, format="png")
            st.download_button(
                label="Télécharger le graphe (format png)",
                data=buffer.getvalue(),
                file_name="Histogramme.png",
                mime="image/png"
            )

            # Classement
            st.subheader("Classement:")
            df_sorted = df.sort_values(by=colonne_valeur, ascending=False)
            fig2, ax2 = plt.subplots(figsize=(8, 6))
            ax2.barh(df_sorted[colonne_nom], df_sorted[colonne_valeur], color='#0B6E72', height=0.4)
            ax2.set_xlabel(colonne_valeur)
            ax2.invert_yaxis()
            fig2.tight_layout()
            st.pyplot(fig2)

            # Telechargement
            buffer = io.BytesIO()
            fig2.savefig(buffer, format="png")
            st.download_button(
                label="Télécharger le graphe (format png)",
                data=buffer.getvalue(),
                file_name="Classement.png",
                mime="image/png"
            )

            # Telecharger pdf - Absences
            pdf_abs = FPDF()
            pdf_abs.set_auto_page_break(True, 15)
            pdf_abs.add_page()

            # Header
            pdf_abs.set_fill_color(184, 187, 146)
            pdf_abs.rect(0, 0, 210, 60, "F")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(base64.b64decode(logo_b64))
                tmp_logo = tmp.name
            pdf_abs.image(tmp_logo, x=140, y=0, w=50)
            os.unlink(tmp_logo)
            pdf_abs.set_draw_color(255, 255, 255)
            pdf_abs.set_line_width(0.4)
            pdf_abs.line(130, 8, 130, 52)
            pdf_abs.set_text_color(255, 255, 255)
            pdf_abs.set_font("Helvetica", "B", 30)
            pdf_abs.set_xy(15, 12)
            pdf_abs.multi_cell(110, 12, "Rapport\nAbsences")
            pdf_abs.set_font("Helvetica", "", 13)
            pdf_abs.set_xy(15, 40)
            pdf_abs.cell(100, 8, "Analyse des absences des étudiants")

            # Encadres
            pdf_abs.ln(35)
            y_boxes = pdf_abs.get_y()
            pdf_abs.set_fill_color(248, 245, 238)
            pdf_abs.rect(15, y_boxes, 85, 35, "F")
            pdf_abs.rect(110, y_boxes, 85, 35, "F")

            pdf_abs.set_xy(20, y_boxes + 5)
            pdf_abs.set_font("Helvetica", "", 9)
            pdf_abs.set_text_color(100, 100, 100)
            pdf_abs.cell(75, 5, "NOMBRE D'ÉTUDIANTS", ln=True)
            pdf_abs.set_xy(20, y_boxes + 12)
            pdf_abs.set_font("Helvetica", "B", 22)
            pdf_abs.set_text_color(11, 110, 114)
            pdf_abs.cell(75, 10, str(len(df)), ln=True)

            pdf_abs.set_xy(115, y_boxes + 5)
            pdf_abs.set_font("Helvetica", "", 9)
            pdf_abs.set_text_color(100, 100, 100)
            pdf_abs.cell(75, 5, "MOYENNE D'ABSENCES", ln=True)
            pdf_abs.set_xy(115, y_boxes + 12)
            pdf_abs.set_font("Helvetica", "B", 22)
            pdf_abs.set_text_color(217, 83, 79)
            pdf_abs.cell(75, 10, str(round(df[colonne_valeur].mean(), 2)), ln=True)
            pdf_abs.ln(45)

            # Page 2 : Histogramme
            pdf_abs.add_page()
            pdf_abs.set_fill_color(11, 110, 114)
            pdf_abs.rect(0, 0, 210, 6, "F")
            pdf_abs.ln(12)
            pdf_abs.set_font("Helvetica", "B", 16)
            pdf_abs.set_text_color(40, 40, 40)
            pdf_abs.cell(0, 10, "Répartition des absences", ln=True)
            pdf_abs.set_draw_color(220, 220, 220)
            pdf_abs.line(15, pdf_abs.get_y(), 195, pdf_abs.get_y())
            pdf_abs.ln(8)
            buffer_h = io.BytesIO()
            fig1.savefig(buffer_h, format="png", bbox_inches="tight", dpi=150)
            buffer_h.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(buffer_h.read())
                tmp_h = tmp.name
            pdf_abs.image(tmp_h, x=15, w=180)
            os.unlink(tmp_h)

            # Page 3 : Classement
            pdf_abs.add_page()
            pdf_abs.set_fill_color(11, 110, 114)
            pdf_abs.rect(0, 0, 210, 6, "F")
            pdf_abs.ln(12)
            pdf_abs.set_font("Helvetica", "B", 16)
            pdf_abs.set_text_color(40, 40, 40)
            pdf_abs.cell(0, 10, "Classement des étudiants", ln=True)
            pdf_abs.set_draw_color(220, 220, 220)
            pdf_abs.line(15, pdf_abs.get_y(), 195, pdf_abs.get_y())
            pdf_abs.ln(8)
            buffer_c = io.BytesIO()
            fig2.savefig(buffer_c, format="png", bbox_inches="tight", dpi=150)
            buffer_c.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(buffer_c.read())
                tmp_c = tmp.name
            pdf_abs.image(tmp_c, x=15, w=180)
            os.unlink(tmp_c)

            pdf_bytes_abs = bytes(pdf_abs.output())
            st.download_button(
                label="Télécharger le rapport complet",
                data=pdf_bytes_abs,
                file_name="rapport_absences.pdf",
                mime="application/pdf"
            )

            plt.close(fig1)
            plt.close(fig2)


if st.sidebar.button("Déconnexion"):
    st.session_state["mot_de_passe_correct"] = False
    st.rerun()
