import streamlit as st
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score
import seaborn as sns
from sklearn.cluster import KMeans
import base64
import io
import tempfile
import os
from fpdf import FPDF


with open("assets/style.css") as f:
  st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

with open("assets/logo.png", "rb") as f:
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
            <span style='color:#0B6E72;'>Analyse Prédictive des</span>
            <span style='color:#D9534F;'>Performances Étudiantes</span>
        </h1>
        <p style='font-size:.82rem; color:#607D7E; margin:0;'>
           Détection des étudiants à risque  •  Analyse des performances  •  Aide à la décision pédagogique
        </p>
    </div>
</div>
""", unsafe_allow_html=True)



fichier1 = st.sidebar.file_uploader(
        "Déposer le fichier des notes: ",
        type=["csv", "xlsx"],
        key="fichier_notes"
    )

if fichier1 is None:
    st.markdown("""
    <div style='text-align:center; padding: 3rem 1rem; color: #607D7E;'>
        <h3 style='color: #0B6E72; margin-bottom: .5rem;'>Commencez par déposer un fichier</h3>
        <p style='font-size: .95rem;'>
            Utilisez le menu latéral pour choisir le type de données<br>
            et déposer votre fichier CSV ou Excel.
        </p>
    </div>
    """, unsafe_allow_html=True)

avec_absences = st.sidebar.checkbox("J'ai un fichier d'absences")
if "dernier_mode" not in st.session_state:
    st.session_state["dernier_mode"] = avec_absences

if avec_absences != st.session_state["dernier_mode"]:
    st.session_state["Afficher_pred"] = False
    st.session_state["dernier_mode"] = avec_absences

if avec_absences:
  fichier2 = st.sidebar.file_uploader(
        "Déposer le fichier des absences: ",
        type=["csv", "xlsx"],
        key="fichier_absences"
      )

  if fichier1 is not None and fichier2 is not None:

    if fichier1.name.endswith(".csv"):
        df1 = pd.read_csv(fichier1)
    else:
        df1 = pd.read_excel(fichier1)

    if fichier2.name.endswith(".csv"):
        df2 = pd.read_csv(fichier2)
    else:
        df2 = pd.read_excel(fichier2)

    col_nom_df1 = st.sidebar.selectbox(
        "Choisir la colonne des noms dans le fichier notes :",
        df1.columns
    )
    col_nom_df2 = st.sidebar.selectbox(
        "Choisir la colonne des noms dans le fichier absences :",
        df2.columns
    )

    #Fusion
    df = pd.merge(df1, df2, left_on=col_nom_df1, right_on=col_nom_df2)
    #st.dataframe(df)

    col_abs = st.sidebar.selectbox(
        "Choisir la colonne qui représente l'absence :",
        df.columns
    )

    cols_notes = st.sidebar.multiselect(
        "Choisir les colonnes qui représentent les notes:",
        df.columns
    )

    seuil = st.sidebar.number_input("Veuillez entrer le seuil de réussite: ")
    seuil_abs = st.sidebar.number_input("Veuillez entrer le seuil d'absence: ")

    if "Afficher_pred" not in st.session_state:
        st.session_state["Afficher_pred"] = False

    if st.sidebar.button("Afficher"):
        st.session_state["Afficher_pred"] = True

    if cols_notes and seuil and seuil_abs and st.session_state["Afficher_pred"]:

      df["Moyenne"] = df[cols_notes].mean(axis=1)

      y = ((df["Moyenne"] >= seuil) & (df[col_abs] <= seuil_abs)).astype(int)
      #st.dataframe(y)
      X = df[cols_notes + [col_abs]]

      # Entrainement de modele
      X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

      model = LogisticRegression()
      model.fit(X_train, y_train)

      # Prédiction
      y_pred = model.predict(X)

      tab1, tab2, tab3, tab4 = st.tabs([
          "Résultats",
          "Corrélation",
          "Performances",
          "Risques"
      ])

      with tab1:
        df_resultats = pd.DataFrame({
              "Nom": df[col_nom_df1],
              **{col: df[col] for col in cols_notes},
              "Moyenne": df["Moyenne"],
              "Absences": df[col_abs],
              "Prédiction": ["Réussite" if p == 1 else "Échec" for p in y_pred]
        })

        st.dataframe(df_resultats)

        st.subheader(" Étudiants à risque d'échec :")
        df_risque = df_resultats[df_resultats["Prédiction"] == "Échec"]
        st.dataframe(df_risque)

        precision = accuracy_score(y, y_pred)
        st.metric("Précision du modèle", f"{round(precision * 100, 2)} %")

      with tab2:
        st.subheader("Corrélation entre absences et notes par matière")

        with st.expander("Comment lire ce graphique ?"):
            st.write("""
            **La heatmap de corrélation** montre la relation entre chaque paire de colonnes :

          🔴 **Proche de +1** → Forte corrélation positive : quand l'une augmente, l'autre augmente aussi

          🔵 **Proche de -1** → Forte corrélation négative : quand l'une augmente, l'autre diminue

          ⬜ **Proche de 0** → Pas de corrélation : les deux colonnes sont indépendantes

          **Exemple concret :**
          Si la case "Absences / Maths" affiche **-0.8**, cela signifie que plus un étudiant est absent, 
          moins sa note en Maths est bonne. C'est une forte corrélation négative !

          **Ce qu'il faut regarder :**
          → Les cases entre **Absences** et chaque matière
          → Plus la valeur est proche de **-1**, plus les absences impactent cette matière
          """)

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(
          df[cols_notes + [col_abs]].corr(),
          annot=True,
          cmap="coolwarm",
          ax=ax
        )
        st.pyplot(fig)

        #Telecharger
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png")
        st.download_button(
            label="Télécharger le graphe (format png)",
            data=buffer.getvalue(),
            file_name="Heatmap.png",
            mime="image/png"
        )

      with tab3:
        st.subheader("Comparaison des moyennes par matière")

        moyennes_par_matiere = df[cols_notes].mean()
        matiere_faible = moyennes_par_matiere.idxmin()

        st.metric("Matière la plus faible", matiere_faible,
                f"{round(moyennes_par_matiere[matiere_faible], 2)}/20")

        #hist
        fig1, ax = plt.subplots()
        ax.barh(moyennes_par_matiere.index, moyennes_par_matiere.values, color='#0B6E72', height=0.2)
        ax.set_xlabel("Moyenne")
        ax.axvline(x=seuil, color='red', linestyle='--', label=f'Seuil ({seuil})')
        ax.legend()
        fig1.tight_layout()
        st.pyplot(fig1)

        buffer = io.BytesIO()
        fig1.savefig(buffer, format="png")
        st.download_button(
            label="Télécharger le graphe (format png)",
            data=buffer.getvalue(),
            file_name="Histogramme1.png",
            mime="image/png"
        )


        echecs_par_matiere = (df[cols_notes] < seuil).sum()
        matiere_plus_dechec = echecs_par_matiere.idxmax()
        st.metric("Matière avec le plus d'échecs", matiere_plus_dechec,
              f"{echecs_par_matiere[matiere_plus_dechec]} étudiants en échec")

        #hist
        fig2, ax = plt.subplots()
        ax.barh(echecs_par_matiere.index, echecs_par_matiere.values, color='#E63946', height=0.2)
        ax.set_xlabel("Nombre d'échecs")
        fig2.tight_layout()
        st.pyplot(fig2)

        buffer = io.BytesIO()
        fig2.savefig(buffer, format="png")
        st.download_button(
            label="Télécharger le graphe (format png)",
            data=buffer.getvalue(),
            file_name="Histogramme2.png",
            mime="image/png"
        )


      with tab4:
        st.subheader("Étudiants à double risque")
        df_double_risque = df[
          (df["Moyenne"] < seuil) & (df[col_abs] > seuil_abs)
          ][[col_nom_df1, "Moyenne", col_abs]]

        st.metric("Nombre d'étudiants à risque", len(df_double_risque))
        st.dataframe(df_double_risque)

        if len(df_double_risque) > 0:
            st.error(f" {len(df_double_risque)} étudiant(s) nécessitent une intervention !")
        else:
            st.success("Aucun étudiant à double risque détecté !")

        st.markdown("---")
        st.subheader("Rapport complet:")

        pdf_complet = FPDF()
        pdf_complet.set_auto_page_break(True, 15)
        pdf_complet.add_page()

        # ── Header ──────────────────────────────────────────
        pdf_complet.set_fill_color(184, 187, 146)
        pdf_complet.rect(0, 0, 210, 60, "F")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(base64.b64decode(logo_b64))
            tmp_logo = tmp.name
        pdf_complet.image(tmp_logo, x=140, y=0, w=50)
        os.unlink(tmp_logo)
        pdf_complet.set_draw_color(255, 255, 255)
        pdf_complet.set_line_width(0.4)
        pdf_complet.line(130, 8, 130, 52)
        pdf_complet.set_text_color(255, 255, 255)
        pdf_complet.set_font("Helvetica", "B", 30)
        pdf_complet.set_xy(15, 12)
        pdf_complet.multi_cell(110, 12, "Rapport\nPrédictif")
        pdf_complet.set_font("Helvetica", "", 13)
        pdf_complet.set_xy(15, 40)
        pdf_complet.cell(100, 8, f"Seuil notes : {seuil}/20 | Seuil absences : {seuil_abs}")

        # ── Encadrés statistiques ────────────────────────────
        pdf_complet.ln(35)
        y_boxes = pdf_complet.get_y()
        pdf_complet.set_fill_color(248, 245, 238)
        pdf_complet.rect(15, y_boxes, 85, 35, "F")
        pdf_complet.rect(110, y_boxes, 85, 35, "F")
        nb_reussite = len(df_resultats[df_resultats["Prédiction"] == "Réussite"])
        nb_echec = len(df_resultats[df_resultats["Prédiction"] == "Échec"])

        pdf_complet.set_xy(20, y_boxes + 5)
        pdf_complet.set_font("Helvetica", "", 9)
        pdf_complet.set_text_color(100, 100, 100)
        pdf_complet.cell(75, 5, "NOMBRE D'ÉTUDIANTS", ln=True)
        pdf_complet.set_xy(20, y_boxes + 12)
        pdf_complet.set_font("Helvetica", "B", 22)
        pdf_complet.set_text_color(11, 110, 114)
        pdf_complet.cell(75, 10, str(len(df)), ln=True)
        pdf_complet.set_xy(20, y_boxes + 24)
        pdf_complet.set_font("Helvetica", "", 9)
        pdf_complet.set_text_color(100, 100, 100)
        pdf_complet.cell(75, 5, f"Réussite : {nb_reussite} | Échec : {nb_echec}")

        pdf_complet.set_xy(115, y_boxes + 5)
        pdf_complet.set_font("Helvetica", "", 9)
        pdf_complet.set_text_color(100, 100, 100)
        pdf_complet.cell(75, 5, "MOYENNE GÉNÉRALE", ln=True)
        pdf_complet.set_xy(115, y_boxes + 12)
        pdf_complet.set_font("Helvetica", "B", 22)
        pdf_complet.set_text_color(217, 83, 79)
        pdf_complet.cell(75, 10, str(round(df["Moyenne"].mean(), 2)), ln=True)
        pdf_complet.set_xy(115, y_boxes + 24)
        pdf_complet.set_font("Helvetica", "", 9)
        pdf_complet.set_text_color(100, 100, 100)
        pdf_complet.cell(75, 5, f"Seuil : {seuil}/20")
        pdf_complet.ln(45)

        # ── Description ──────────────────────────────────────
        pdf_complet.set_text_color(40, 40, 40)
        pdf_complet.set_font("Helvetica", "B", 20)
        pdf_complet.cell(0, 12, "À propos du rapport", ln=True)
        pdf_complet.ln(3)
        pdf_complet.set_font("Helvetica", "", 11)
        pdf_complet.multi_cell(0, 7,
                               "Ce rapport présente une analyse prédictive des performances étudiantes "
                               "basée sur les notes par matière. Il inclut les résultats individuels, "
                               "les performances par matière et la classification des étudiants par profil."
                               )
        pdf_complet.ln(10)

        # ── Page 2 : Résultats ────────────────────────────────
        pdf_complet.add_page()
        pdf_complet.set_fill_color(11, 110, 114)
        pdf_complet.rect(0, 0, 210, 6, "F")
        pdf_complet.ln(12)
        pdf_complet.set_text_color(40, 40, 40)
        pdf_complet.set_font("Helvetica", "B", 16)
        pdf_complet.cell(0, 10, "Résultats & Prédiction", ln=True)
        pdf_complet.set_draw_color(220, 220, 220)
        pdf_complet.line(15, pdf_complet.get_y(), 195, pdf_complet.get_y())
        pdf_complet.ln(8)

        colonnes_res = list(df_resultats.columns)
        largeur_col = 180 // len(colonnes_res)
        pdf_complet.set_fill_color(11, 110, 114)
        pdf_complet.set_text_color(255, 255, 255)
        pdf_complet.set_font("Helvetica", "B", 8)
        for col in colonnes_res:
            pdf_complet.cell(largeur_col, 8, str(col)[:15], border=1, fill=True)
        pdf_complet.ln()
        pdf_complet.set_font("Helvetica", "", 8)
        for i, row in df_resultats.iterrows():
            if row.get("Prédiction") == "Réussite":
                pdf_complet.set_fill_color(230, 244, 245)
                pdf_complet.set_text_color(11, 110, 114)
            else:
                pdf_complet.set_fill_color(255, 240, 240)
                pdf_complet.set_text_color(217, 83, 79)
            for val in row:
                pdf_complet.cell(largeur_col, 7,
                                 str(round(val, 2) if isinstance(val, float) else val)[:15],
                                 border=1, fill=True)
            pdf_complet.ln()

        # ── Page 3 : Performances par matière ────────────────
        pdf_complet.add_page()
        pdf_complet.set_fill_color(11, 110, 114)
        pdf_complet.rect(0, 0, 210, 6, "F")
        pdf_complet.ln(12)
        pdf_complet.set_text_color(40, 40, 40)
        pdf_complet.set_font("Helvetica", "B", 16)
        pdf_complet.cell(0, 10, "Performances par matière", ln=True)
        pdf_complet.set_draw_color(220, 220, 220)
        pdf_complet.line(15, pdf_complet.get_y(), 195, pdf_complet.get_y())
        pdf_complet.ln(8)

        buffer_m = io.BytesIO()
        fig1.savefig(buffer_m, format="png", bbox_inches="tight", dpi=150)
        buffer_m.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(buffer_m.read())
            tmp_m = tmp.name
        pdf_complet.set_font("Helvetica", "B", 11)
        pdf_complet.set_text_color(50, 50, 50)
        pdf_complet.cell(0, 7, "Moyenne par matière", ln=True)
        pdf_complet.image(tmp_m, x=15, w=180)
        os.unlink(tmp_m)
        pdf_complet.ln(8)

        buffer_e = io.BytesIO()
        fig2.savefig(buffer_e, format="png", bbox_inches="tight", dpi=150)
        buffer_e.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(buffer_e.read())
            tmp_e = tmp.name
        pdf_complet.set_font("Helvetica", "B", 11)
        pdf_complet.cell(0, 7, "Nombre d'échecs par matière", ln=True)
        pdf_complet.image(tmp_e, x=15, w=180)
        os.unlink(tmp_e)

        # ── Page 4 : Corrélation ─────────────────────────────
        pdf_complet.add_page()
        pdf_complet.set_fill_color(11, 110, 114)
        pdf_complet.rect(0, 0, 210, 6, "F")
        pdf_complet.ln(12)
        pdf_complet.set_text_color(40, 40, 40)
        pdf_complet.set_font("Helvetica", "B", 16)
        pdf_complet.cell(0, 10, "Corrélation absences / notes", ln=True)
        pdf_complet.set_draw_color(220, 220, 220)
        pdf_complet.line(15, pdf_complet.get_y(), 195, pdf_complet.get_y())
        pdf_complet.ln(8)

        # Sauvegarder la heatmap
        fig_heatmap, ax_h = plt.subplots(figsize=(10, 6))
        import seaborn as sns

        sns.heatmap(df[cols_notes + [col_abs]].corr(), annot=True, cmap="RdYlGn", ax=ax_h)
        buffer_heat = io.BytesIO()
        fig_heatmap.savefig(buffer_heat, format="png", bbox_inches="tight", dpi=150)
        buffer_heat.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(buffer_heat.read())
            tmp_heat = tmp.name
        pdf_complet.image(tmp_heat, x=15, w=180)
        os.unlink(tmp_heat)
        plt.close(fig_heatmap)

        # ── Page 5 : Étudiants à double risque ───────────────
        pdf_complet.add_page()
        pdf_complet.set_fill_color(11, 110, 114)
        pdf_complet.rect(0, 0, 210, 6, "F")
        pdf_complet.ln(12)
        pdf_complet.set_text_color(40, 40, 40)
        pdf_complet.set_font("Helvetica", "B", 16)
        pdf_complet.cell(0, 10, "Étudiants à double risque", ln=True)
        pdf_complet.set_draw_color(220, 220, 220)
        pdf_complet.line(15, pdf_complet.get_y(), 195, pdf_complet.get_y())
        pdf_complet.ln(8)

        if len(df_double_risque) > 0:
            cols_risque = list(df_double_risque.columns)
            larg_r = 180 // len(cols_risque)
            pdf_complet.set_fill_color(11, 110, 114)
            pdf_complet.set_text_color(255, 255, 255)
            pdf_complet.set_font("Helvetica", "B", 9)
            for col in cols_risque:
                pdf_complet.cell(larg_r, 8, str(col)[:20], border=1, fill=True)
            pdf_complet.ln()
            pdf_complet.set_font("Helvetica", "", 9)
            for i, row in df_double_risque.iterrows():
                pdf_complet.set_fill_color(255, 240, 240)
                pdf_complet.set_text_color(217, 83, 79)
                for val in row:
                    pdf_complet.cell(larg_r, 7,
                                     str(round(val, 2) if isinstance(val, float) else val)[:20],
                                     border=1, fill=True)
                    pdf_complet.ln()
        else:
            pdf_complet.set_font("Helvetica", "", 11)
            pdf_complet.set_text_color(11, 110, 114)
            pdf_complet.cell(0, 10, "Aucun étudiant à double risque détecté.", ln=True)

        pdf_bytes_complet = bytes(pdf_complet.output())
        st.download_button(
            label="Télécharger le rapport complet (PDF)",
            data=pdf_bytes_complet,
            file_name="rapport_predictif_avec_absences.pdf",
            mime="application/pdf"
        )

else:
  if fichier1 is not None:
    if fichier1.name.endswith(".csv"):
      df = pd.read_csv(fichier1)
    else:
      df = pd.read_excel(fichier1)

    colonne_nom = st.sidebar.selectbox("Quelle colonne représente les noms des étudiants ?", df.columns)

    cols_notes = st.sidebar.multiselect(
        "Choisir les colonnes qui représentent les notes:",
        df.columns
    )

    seuil = st.sidebar.number_input(
    "Veuillez entrer le seuil de réussite: ",
    min_value=0.0,
    max_value=20.0,
    value=10.0
    )

    if "Afficher_pred" not in st.session_state:
        st.session_state["Afficher_pred"] = False

    if st.sidebar.button("Afficher"):
        st.session_state["Afficher_pred"] = True

    if cols_notes and seuil and st.session_state["Afficher_pred"]:
      df["Moyenne"] = df[cols_notes].mean(axis=1)

      y = (df["Moyenne"] >= seuil).astype(int)
      X = df[cols_notes]

      df["Statut"] = (df["Moyenne"] >= seuil).map({True: "Réussite", False: "Échec"})

      tab1, tab2, tab3 = st.tabs([
        "Résultats & Prédiction",
        "Performances par matière",
        "Classification par groupes"
        ])

      with tab1:
        df_resultats = pd.DataFrame({
              "Nom": df[colonne_nom],
              **{col: df[col] for col in cols_notes},
              "Moyenne": df["Moyenne"],
              "Statut": df["Statut"],
        })

        st.dataframe(df_resultats)


        pdf_res = FPDF()
        pdf_res.set_auto_page_break(True, 15)
        pdf_res.add_page()

        # ====================================================
        # ====================================================
        pdf_res.set_fill_color(184, 187, 146)
        pdf_res.rect(0, 0, 210, 60, "F")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(base64.b64decode(logo_b64))
            tmp_logo = tmp.name
        pdf_res.image(tmp_logo, x=140, y=12, w=50)
        os.unlink(tmp_logo)

        pdf_res.set_draw_color(255, 255, 255)
        pdf_res.set_line_width(0.4)
        pdf_res.line(130, 8, 130, 52)

        pdf_res.set_text_color(255, 255, 255)
        pdf_res.set_font("Helvetica", "B", 30)
        pdf_res.set_xy(15, 12)
        pdf_res.multi_cell(110, 12, "Résultats\ndes Étudiants")

        pdf_res.set_font("Helvetica", "", 13)
        pdf_res.set_xy(15, 40)
        pdf_res.cell(100, 8, f"Seuil de réussite : {seuil}/20")

        # ====================================================
        # Statistiques rapides dans encadrés
        # ====================================================
        pdf_res.ln(35)
        y_boxes = pdf_res.get_y()

        pdf_res.set_fill_color(248, 245, 238)
        pdf_res.rect(15, y_boxes, 85, 35, "F")
        pdf_res.rect(110, y_boxes, 85, 35, "F")

        nb_reussite = len(df_resultats[df_resultats.get("Statut", df_resultats.get("Prédiction", "")) == "Réussite"])

        # Encadré gauche
        pdf_res.set_xy(20, y_boxes + 5)
        pdf_res.set_font("Helvetica", "", 9)
        pdf_res.set_text_color(100, 100, 100)
        pdf_res.cell(75, 5, "NOMBRE D'ÉTUDIANTS", ln=True)
        pdf_res.set_xy(20, y_boxes + 12)
        pdf_res.set_font("Helvetica", "B", 22)
        pdf_res.set_text_color(11, 110, 114)
        pdf_res.cell(75, 10, str(len(df_resultats)), ln=True)

        # Encadré droit
        pdf_res.set_xy(115, y_boxes + 5)
        pdf_res.set_font("Helvetica", "", 9)
        pdf_res.set_text_color(100, 100, 100)
        pdf_res.cell(75, 5, "MOYENNE GÉNÉRALE", ln=True)
        pdf_res.set_xy(115, y_boxes + 12)
        pdf_res.set_font("Helvetica", "B", 22)
        pdf_res.set_text_color(217, 83, 79)
        pdf_res.cell(75, 10, str(round(df_resultats["Moyenne"].mean(), 2)), ln=True)

        pdf_res.ln(45)

        # ====================================================
        # Tableau des résultats
        # ====================================================
        pdf_res.set_text_color(40, 40, 40)
        pdf_res.set_font("Helvetica", "B", 18)
        pdf_res.cell(0, 10, "Détail des résultats", ln=True)
        pdf_res.set_draw_color(220, 220, 220)
        pdf_res.line(15, pdf_res.get_y(), 195, pdf_res.get_y())
        pdf_res.ln(8)

        # En-tête tableau
        colonnes = list(df_resultats.columns)
        largeur_col = 180 // len(colonnes)

        pdf_res.set_fill_color(11, 110, 114)
        pdf_res.set_text_color(255, 255, 255)
        pdf_res.set_font("Helvetica", "B", 8)
        for col in colonnes:
            pdf_res.cell(largeur_col, 8, str(col)[:15], border=1, fill=True)
        pdf_res.ln()

        # Lignes tableau
        pdf_res.set_font("Helvetica", "", 8)
        for i, row in df_resultats.iterrows():
            statut = row.get("Statut", row.get("Prédiction", ""))
            if statut == "Réussite":
                pdf_res.set_fill_color(230, 244, 245)
                pdf_res.set_text_color(11, 110, 114)
            else:
                pdf_res.set_fill_color(255, 240, 240)
                pdf_res.set_text_color(217, 83, 79)
            for val in row:
                pdf_res.cell(largeur_col, 7,
                             str(round(val, 2) if isinstance(val, float) else val)[:15],
                             border=1, fill=True)
            pdf_res.ln()

        pdf_bytes_res = bytes(pdf_res.output())

        st.download_button(
            label="Télécharger en PDF",
            data=pdf_bytes_res,
            file_name="resultats_etudiants.pdf",
            mime="application/pdf"
        )


      with tab2:
        st.subheader("Comparaison des moyennes par matière: ")

        moyennes_par_matiere = df[cols_notes].mean()
        matiere_faible = moyennes_par_matiere.idxmin()

        st.metric("Matière la plus faible", matiere_faible,
                    f"{round(moyennes_par_matiere[matiere_faible], 2)}/20")

        fig1, ax = plt.subplots()
        fig1.patch.set_alpha(0)
        ax.set_facecolor("none")
        ax.barh(moyennes_par_matiere.index, moyennes_par_matiere.values, color='#0B6E72', height=0.2)
        ax.set_xlabel("Moyenne")
        ax.axvline(x=seuil, color='red', linestyle='--', label=f'Seuil ({seuil})')
        ax.legend()
        fig1.tight_layout()
        st.pyplot(fig1)

        # Telechargement
        buffer1 = io.BytesIO()
        fig1.savefig(buffer1, format="png")
        st.download_button(
            label="Télécharger le graphe (format png)",
            data=buffer1.getvalue(),
            file_name="Histogramme1.png",
            mime="image/png"
        )

        echecs_par_matiere = (df[cols_notes] < seuil).sum()
        matiere_plus_dechec = echecs_par_matiere.idxmax()
        st.metric("Matière avec le plus d'échecs", matiere_plus_dechec,
                    f"{echecs_par_matiere[matiere_plus_dechec]} étudiants en échec")

        fig2, ax = plt.subplots()
        fig2.patch.set_alpha(0)
        ax.set_facecolor("none")
        ax.barh(echecs_par_matiere.index, echecs_par_matiere.values, color='#0B6E72', height=0.2)
        ax.set_xlabel("Nombre d'échecs")
        fig2.tight_layout()
        st.pyplot(fig2)

        # Telechargement
        buffer2 = io.BytesIO()
        fig2.savefig(buffer1, format="png")
        st.download_button(
            label="Télécharger le graphe (format png)",
            data=buffer2.getvalue(),
            file_name="Histogramme2.png",
            mime="image/png"
        )


      with tab3:
          kmeans = KMeans(n_clusters=3, random_state=42)
          kmeans.fit(df[["Moyenne"]])
          df["Groupe"] = kmeans.labels_

          moyennes_groupes = df.groupby("Groupe")["Moyenne"].mean().sort_values()

          labels = {
              moyennes_groupes.index[0]: "En difficulté",
              moyennes_groupes.index[1]: "Moyen",
              moyennes_groupes.index[2]: "Excellent"
          }

          df["Profil"] = df["Groupe"].map(labels)

          st.dataframe(df[[colonne_nom, "Moyenne", "Profil"]])

          count = df["Profil"].value_counts()

          color_map = {
              "Excellent": '#0B6E72',
              "Moyen": '#F4A261',
              "En difficulté": '#E63946'
          }
          colors = [color_map[label] for label in count.index]

          fig3, ax = plt.subplots()
          fig3.patch.set_alpha(0)
          ax.set_facecolor("none")
          ax.pie(count, labels=count.index, autopct='%1.1f%%', colors=colors)
          st.pyplot(fig3)

          # Telechargement
          buffer3 = io.BytesIO()
          fig3.savefig(buffer3, format="png")
          st.download_button(
              label="Télécharger le graphe (format png)",
              data=buffer3.getvalue(),
              file_name="Classement.png",
              mime="image/png"
          )

          # Statistiques par groupe
          st.subheader("Statistiques par groupe: ")
          st.dataframe(df.groupby("Profil")["Moyenne"].agg(['mean', 'count', 'min', 'max'])
                       .rename(columns={'mean': 'Moyenne', 'count': 'Nombre',
                                        'min': 'Min', 'max': 'Max'}))

          st.markdown("---")
          st.subheader("Rapport complet:")

          pdf_complet = FPDF()
          pdf_complet.set_auto_page_break(True, 15)
          pdf_complet.add_page()

          # ── Header ──────────────────────────────────────────
          pdf_complet.set_fill_color(184, 187, 146)
          pdf_complet.rect(0, 0, 210, 60, "F")
          with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
              tmp.write(base64.b64decode(logo_b64))
              tmp_logo = tmp.name
          pdf_complet.image(tmp_logo, x=140, y=0, w=50)
          os.unlink(tmp_logo)
          pdf_complet.set_draw_color(255, 255, 255)
          pdf_complet.set_line_width(0.4)
          pdf_complet.line(130, 8, 130, 52)
          pdf_complet.set_text_color(255, 255, 255)
          pdf_complet.set_font("Helvetica", "B", 30)
          pdf_complet.set_xy(15, 12)
          pdf_complet.multi_cell(110, 12, "Rapport\nPrédictif")
          pdf_complet.set_font("Helvetica", "", 13)
          pdf_complet.set_xy(15, 40)
          pdf_complet.cell(100, 8, f"Seuil de réussite : {seuil}/20")

          # ── Encadrés statistiques ────────────────────────────
          pdf_complet.ln(35)
          y_boxes = pdf_complet.get_y()
          pdf_complet.set_fill_color(248, 245, 238)
          pdf_complet.rect(15, y_boxes, 85, 35, "F")
          pdf_complet.rect(110, y_boxes, 85, 35, "F")
          nb_reussite = len(df[df["Statut"] == "Réussite"])
          nb_echec = len(df[df["Statut"] == "Échec"])

          pdf_complet.set_xy(20, y_boxes + 5)
          pdf_complet.set_font("Helvetica", "", 9)
          pdf_complet.set_text_color(100, 100, 100)
          pdf_complet.cell(75, 5, "NOMBRE D'ÉTUDIANTS", ln=True)
          pdf_complet.set_xy(20, y_boxes + 12)
          pdf_complet.set_font("Helvetica", "B", 22)
          pdf_complet.set_text_color(11, 110, 114)
          pdf_complet.cell(75, 10, str(len(df)), ln=True)
          pdf_complet.set_xy(20, y_boxes + 24)
          pdf_complet.set_font("Helvetica", "", 9)
          pdf_complet.set_text_color(100, 100, 100)
          pdf_complet.cell(75, 5, f"Réussite : {nb_reussite} | Échec : {nb_echec}")

          pdf_complet.set_xy(115, y_boxes + 5)
          pdf_complet.set_font("Helvetica", "", 9)
          pdf_complet.set_text_color(100, 100, 100)
          pdf_complet.cell(75, 5, "MOYENNE GÉNÉRALE", ln=True)
          pdf_complet.set_xy(115, y_boxes + 12)
          pdf_complet.set_font("Helvetica", "B", 22)
          pdf_complet.set_text_color(217, 83, 79)
          pdf_complet.cell(75, 10, str(round(df["Moyenne"].mean(), 2)), ln=True)
          pdf_complet.set_xy(115, y_boxes + 24)
          pdf_complet.set_font("Helvetica", "", 9)
          pdf_complet.set_text_color(100, 100, 100)
          pdf_complet.cell(75, 5, f"Seuil : {seuil}/20")
          pdf_complet.ln(45)

          # ── Description ──────────────────────────────────────
          pdf_complet.set_text_color(40, 40, 40)
          pdf_complet.set_font("Helvetica", "B", 20)
          pdf_complet.cell(0, 12, "À propos du rapport", ln=True)
          pdf_complet.ln(3)
          pdf_complet.set_font("Helvetica", "", 11)
          pdf_complet.multi_cell(0, 7,
                                 "Ce rapport présente une analyse prédictive des performances étudiantes "
                                 "basée sur les notes par matière. Il inclut les résultats individuels, "
                                 "les performances par matière et la classification des étudiants par profil."
                                 )
          pdf_complet.ln(10)

          # ── Page 2 : Résultats ────────────────────────────────
          pdf_complet.add_page()
          pdf_complet.set_fill_color(11, 110, 114)
          pdf_complet.rect(0, 0, 210, 6, "F")
          pdf_complet.ln(12)
          pdf_complet.set_text_color(40, 40, 40)
          pdf_complet.set_font("Helvetica", "B", 16)
          pdf_complet.cell(0, 10, "Résultats & Prédiction", ln=True)
          pdf_complet.set_draw_color(220, 220, 220)
          pdf_complet.line(15, pdf_complet.get_y(), 195, pdf_complet.get_y())
          pdf_complet.ln(8)

          colonnes_res = list(df_resultats.columns)
          largeur_col = 180 // len(colonnes_res)
          pdf_complet.set_fill_color(11, 110, 114)
          pdf_complet.set_text_color(255, 255, 255)
          pdf_complet.set_font("Helvetica", "B", 8)
          for col in colonnes_res:
              pdf_complet.cell(largeur_col, 8, str(col)[:15], border=1, fill=True)
          pdf_complet.ln()
          pdf_complet.set_font("Helvetica", "", 8)
          for i, row in df_resultats.iterrows():
              if row.get("Statut") == "Réussite":
                  pdf_complet.set_fill_color(230, 244, 245)
                  pdf_complet.set_text_color(11, 110, 114)
              else:
                  pdf_complet.set_fill_color(255, 240, 240)
                  pdf_complet.set_text_color(217, 83, 79)
              for val in row:
                  pdf_complet.cell(largeur_col, 7,
                                   str(round(val, 2) if isinstance(val, float) else val)[:15],
                                   border=1, fill=True)
              pdf_complet.ln()

          # ── Page 3 : Performances par matière ────────────────
          pdf_complet.add_page()
          pdf_complet.set_fill_color(11, 110, 114)
          pdf_complet.rect(0, 0, 210, 6, "F")
          pdf_complet.ln(12)
          pdf_complet.set_text_color(40, 40, 40)
          pdf_complet.set_font("Helvetica", "B", 16)
          pdf_complet.cell(0, 10, "Performances par matière", ln=True)
          pdf_complet.set_draw_color(220, 220, 220)
          pdf_complet.line(15, pdf_complet.get_y(), 195, pdf_complet.get_y())
          pdf_complet.ln(8)

          buffer_m = io.BytesIO()
          fig1.savefig(buffer_m, format="png", bbox_inches="tight", dpi=150)
          buffer_m.seek(0)
          with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
              tmp.write(buffer_m.read())
              tmp_m = tmp.name
          pdf_complet.set_font("Helvetica", "B", 11)
          pdf_complet.set_text_color(50, 50, 50)
          pdf_complet.cell(0, 7, "Moyenne par matière", ln=True)
          pdf_complet.image(tmp_m, x=15, w=180)
          os.unlink(tmp_m)
          pdf_complet.ln(8)

          buffer_e = io.BytesIO()
          fig2.savefig(buffer_e, format="png", bbox_inches="tight", dpi=150)
          buffer_e.seek(0)
          with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
              tmp.write(buffer_e.read())
              tmp_e = tmp.name
          pdf_complet.set_font("Helvetica", "B", 11)
          pdf_complet.cell(0, 7, "Nombre d'échecs par matière", ln=True)
          pdf_complet.image(tmp_e, x=15, w=180)
          os.unlink(tmp_e)

          # ── Page 4 : Classification K-Means ──────────────────
          pdf_complet.add_page()
          pdf_complet.set_fill_color(11, 110, 114)
          pdf_complet.rect(0, 0, 210, 6, "F")
          pdf_complet.ln(12)
          pdf_complet.set_text_color(40, 40, 40)
          pdf_complet.set_font("Helvetica", "B", 16)
          pdf_complet.cell(0, 10, "Classification par groupes: ", ln=True)
          pdf_complet.set_draw_color(220, 220, 220)
          pdf_complet.line(15, pdf_complet.get_y(), 195, pdf_complet.get_y())
          pdf_complet.ln(8)

          buffer_k = io.BytesIO()
          fig3.savefig(buffer_k, format="png", bbox_inches="tight", dpi=150)
          buffer_k.seek(0)
          with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
              tmp.write(buffer_k.read())
              tmp_k = tmp.name
          pdf_complet.image(tmp_k, x=40, w=120)
          os.unlink(tmp_k)
          pdf_complet.ln(8)

          # Tableau statistiques par groupe
          stats_groupe = df.groupby("Profil")["Moyenne"].agg(
              ['mean', 'count', 'min', 'max']
          ).rename(columns={
              'mean': 'Moyenne', 'count': 'Nombre', 'min': 'Min', 'max': 'Max'
          }).reset_index()

          pdf_complet.set_font("Helvetica", "B", 11)
          pdf_complet.set_text_color(50, 50, 50)
          pdf_complet.cell(0, 7, "Statistiques par groupe", ln=True)
          pdf_complet.ln(4)

          # En-tête tableau groupes
          cols_groupe = list(stats_groupe.columns)
          larg = 180 // len(cols_groupe)
          pdf_complet.set_fill_color(11, 110, 114)
          pdf_complet.set_text_color(255, 255, 255)
          pdf_complet.set_font("Helvetica", "B", 9)
          for col in cols_groupe:
              pdf_complet.cell(larg, 8, str(col), border=1, fill=True)
          pdf_complet.ln()

          # Lignes tableau groupes
          color_map_pdf = {
              "Excellent": (230, 244, 245),
              "Moyen": (255, 248, 225),
              "En difficulté": (255, 240, 240),
          }
          pdf_complet.set_font("Helvetica", "", 9)
          for i, row in stats_groupe.iterrows():
              profil = row["Profil"]
              r, g, b = color_map_pdf.get(profil, (248, 248, 248))
              pdf_complet.set_fill_color(r, g, b)
              pdf_complet.set_text_color(40, 40, 40)
              for val in row:
                  pdf_complet.cell(larg, 7,
                                   str(round(val, 2) if isinstance(val, float) else val),
                                   border=1, fill=True)
              pdf_complet.ln()

          pdf_bytes_complet = bytes(pdf_complet.output())
          st.download_button(
              label="Télécharger le rapport complet (PDF)",
              data=pdf_bytes_complet,
              file_name="rapport_predictif_sans_absences.pdf",
              mime="application/pdf"
          )