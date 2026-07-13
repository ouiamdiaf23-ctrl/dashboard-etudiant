import streamlit as st
from sqlalchemy import text


def get_connection():
    return st.connection("mysql", type="sql")


def ajouter_etudiant(nom, classe=None):
    conn = get_connection()
    classe = classe if classe else None
    with conn.session as session:
        existant = session.execute(
            text("SELECT id FROM etudiants WHERE nom = :nom"),
            {"nom": nom}
        ).fetchone()
        if existant is None:
            session.execute(
                text("INSERT INTO etudiants (nom, classe) VALUES (:nom, :classe);"),
                {"nom": nom, "classe": classe}
            )
        elif classe:
            session.execute(
                text("UPDATE etudiants SET classe = :classe WHERE id = :id"),
                {"classe": classe, "id": existant[0]}
            )
        session.commit()


def recuperer_classes():
    conn = get_connection()
    df = conn.query("SELECT DISTINCT classe FROM etudiants WHERE classe IS NOT NULL;", ttl=0)
    return df["classe"].tolist()


def ajouter_matiere(nom):
    conn = get_connection()
    with conn.session as session:
        existant = session.execute(
            text("SELECT id FROM matieres WHERE nom = :nom"),
            {"nom": nom}
        ).fetchone()

        if existant is None:
            session.execute(
                text("INSERT INTO matieres (nom) VALUES (:nom);"),
                {"nom": nom}
            )
        session.commit()


def recuperer_matieres():
    conn = get_connection()
    df = conn.query("SELECT * FROM matieres;", ttl=0)
    return df


def recuperer_etudiants():
    conn = get_connection()
    df = conn.query("SELECT * FROM etudiants;", ttl=0)
    return df


def ajouter_note(nom_etudiant, nom_matiere, valeur, date_evaluation=None):
    conn = get_connection()
    with conn.session as session:
        etudiant = session.execute(
            text("SELECT id FROM etudiants WHERE nom = :nom"),
            {"nom": nom_etudiant}
        ).fetchone()

        matiere = session.execute(
            text("SELECT id FROM matieres WHERE nom = :nom"),
            {"nom": nom_matiere}
        ).fetchone()

        if etudiant is None or matiere is None:
            raise ValueError("Étudiant ou matière introuvable dans la base.")

        etudiant_id = etudiant[0]
        matiere_id = matiere[0]

        existant = session.execute(
            text("""
                SELECT id FROM notes
                WHERE etudiant_id = :etudiant_id AND matiere_id = :matiere_id AND date_evaluation = :date_evaluation
            """),
            {"etudiant_id": etudiant_id, "matiere_id": matiere_id, "date_evaluation": date_evaluation}
        ).fetchone()

        if existant is None:
            session.execute(
                text("""
                    INSERT INTO notes (etudiant_id, matiere_id, valeur, date_evaluation)
                    VALUES (:etudiant_id, :matiere_id, :valeur, :date_evaluation);
                """),
                {
                    "etudiant_id": etudiant_id,
                    "matiere_id": matiere_id,
                    "valeur": valeur,
                    "date_evaluation": date_evaluation
                }
            )
        else:
            session.execute(
                text("UPDATE notes SET valeur = :valeur WHERE id = :id"),
                {"valeur": valeur, "id": existant[0]}
            )

        session.commit()


def recuperer_notes():
    conn = get_connection()
    df = conn.query("""
        SELECT
            e.nom AS etudiant,
            m.nom AS matiere,
            n.valeur,
            n.date_evaluation
        FROM notes n
        JOIN etudiants e ON n.etudiant_id = e.id
        JOIN matieres m ON n.matiere_id = m.id;
    """, ttl=0)
    return df


def recuperer_notes_etudiant(nom_etudiant):
    conn = get_connection()
    df = conn.query("""
        SELECT
            m.nom AS matiere,
            n.valeur,
            n.date_evaluation
        FROM notes n
        JOIN etudiants e ON n.etudiant_id = e.id
        JOIN matieres m ON n.matiere_id = m.id
        WHERE e.nom = :nom
        ORDER BY n.date_evaluation;
    """, params={"nom": nom_etudiant}, ttl=0)
    return df


def recuperer_moyenne_generale(nom_etudiant):
    conn = get_connection()
    df = conn.query("""
        SELECT
            n.date_evaluation,
            AVG(n.valeur) AS moyenne
        FROM notes n
        JOIN etudiants e ON n.etudiant_id = e.id
        WHERE e.nom = :nom
        GROUP BY n.date_evaluation
        ORDER BY n.date_evaluation;
    """, params={"nom": nom_etudiant}, ttl=0)
    return df


def recuperer_moyenne_classe(nom_classe):
    conn = get_connection()
    df = conn.query("""
        SELECT
            n.date_evaluation,
            AVG(n.valeur) AS moyenne_classe,
            COUNT(DISTINCT n.etudiant_id) AS nombre_etudiants
        FROM notes n
        JOIN etudiants e ON n.etudiant_id = e.id
        WHERE e.classe = :classe
        GROUP BY n.date_evaluation
        ORDER BY n.date_evaluation;
    """, params={"classe": nom_classe}, ttl=0)
    return df


def ajouter_absence(nom_etudiant, nombre_absences, date_releve=None):
    conn = get_connection()
    with conn.session as session:
        etudiant = session.execute(
            text("SELECT id FROM etudiants WHERE nom = :nom"),
            {"nom": nom_etudiant}
        ).fetchone()

        if etudiant is None:
            raise ValueError("Étudiant introuvable dans la base.")

        etudiant_id = etudiant[0]

        existant = session.execute(
            text("""
                SELECT id FROM absences
                WHERE etudiant_id = :etudiant_id AND date_releve = :date_releve
            """),
            {"etudiant_id": etudiant_id, "date_releve": date_releve}
        ).fetchone()

        if existant is None:
            session.execute(
                text("""
                    INSERT INTO absences (etudiant_id, nombre_absences, date_releve)
                    VALUES (:etudiant_id, :nombre_absences, :date_releve);
                """),
                {
                    "etudiant_id": etudiant_id,
                    "nombre_absences": nombre_absences,
                    "date_releve": date_releve
                }
            )
        else:
            session.execute(
                text("""
                    UPDATE absences
                    SET nombre_absences = :nombre_absences
                    WHERE id = :id
                """),
                {"nombre_absences": nombre_absences, "id": existant[0]}
            )

        session.commit()


def recuperer_absences():
    conn = get_connection()
    df = conn.query("""
        SELECT
            e.nom AS etudiant,
            e.classe,
            a.nombre_absences,
            a.date_releve
        FROM absences a
        JOIN etudiants e ON a.etudiant_id = e.id;
    """, ttl=0)
    return df


def recuperer_absences_etudiant(nom_etudiant):
    conn = get_connection()
    df = conn.query("""
        SELECT
            a.nombre_absences,
            a.date_releve
        FROM absences a
        JOIN etudiants e ON a.etudiant_id = e.id
        WHERE e.nom = :nom
        ORDER BY a.date_releve;
    """, params={"nom": nom_etudiant}, ttl=0)
    return df


def recuperer_dates_classe(nom_classe):
    conn = get_connection()
    df = conn.query("""
        SELECT DISTINCT n.date_evaluation
        FROM notes n
        JOIN etudiants e ON n.etudiant_id = e.id
        WHERE e.classe = :classe
        ORDER BY n.date_evaluation;
    """, params={"classe": nom_classe}, ttl=0)
    return df["date_evaluation"].tolist()


def recuperer_donnees_prediction(nom_classe, date_eval):
    conn = get_connection()

    df_notes = conn.query("""
        SELECT e.nom AS Nom, m.nom AS matiere, n.valeur
        FROM notes n
        JOIN etudiants e ON n.etudiant_id = e.id
        JOIN matieres m ON n.matiere_id = m.id
        WHERE e.classe = :classe AND n.date_evaluation = :date_eval;
    """, params={"classe": nom_classe, "date_eval": date_eval}, ttl=0)

    df_absences = conn.query("""
        SELECT e.nom AS Nom, a.nombre_absences AS Absences
        FROM absences a
        JOIN etudiants e ON a.etudiant_id = e.id
        WHERE e.classe = :classe AND a.date_releve = :date_eval;
    """, params={"classe": nom_classe, "date_eval": date_eval}, ttl=0)

    if df_notes.empty:
        return df_notes

    df_pivot = df_notes.pivot(index="Nom", columns="matiere", values="valeur").reset_index()

    if not df_absences.empty:
        df_pivot = df_pivot.merge(df_absences, on="Nom", how="left")

    return df_pivot


def ajouter_prediction(nom_etudiant, date_eval, moyenne, statut):
    conn = get_connection()
    with conn.session as session:
        etudiant = session.execute(
            text("SELECT id FROM etudiants WHERE nom = :nom"),
            {"nom": nom_etudiant}
        ).fetchone()

        if etudiant is None:
            raise ValueError("Étudiant introuvable dans la base.")

        etudiant_id = etudiant[0]

        existant = session.execute(
            text("""
                SELECT id FROM predictions
                WHERE etudiant_id = :etudiant_id AND date_evaluation = :date_eval
            """),
            {"etudiant_id": etudiant_id, "date_eval": date_eval}
        ).fetchone()

        if existant is None:
            session.execute(
                text("""
                    INSERT INTO predictions (etudiant_id, date_evaluation, moyenne, statut)
                    VALUES (:etudiant_id, :date_eval, :moyenne, :statut);
                """),
                {"etudiant_id": etudiant_id, "date_eval": date_eval, "moyenne": moyenne, "statut": statut}
            )
        else:
            session.execute(
                text("UPDATE predictions SET moyenne = :moyenne, statut = :statut WHERE id = :id"),
                {"moyenne": moyenne, "statut": statut, "id": existant[0]}
            )

        session.commit()


def recuperer_predictions():
    conn = get_connection()
    df = conn.query("""
        SELECT e.nom AS etudiant, e.classe, p.date_evaluation, p.moyenne, p.statut
        FROM predictions p
        JOIN etudiants e ON p.etudiant_id = e.id
        ORDER BY p.date_evaluation;
    """, ttl=0)
    return df


