import sqlite3
from pathlib import Path
import pandas as pd
from Transform import df
import os
import duckdb

# ============================================================
# CONFIGURATION
# ============================================================
DOSSIER_ZONE = Path(__file__).resolve().parent.parent
DOSSIER_SCRIPT = Path(__file__).resolve().parent
DB_PATH = DOSSIER_SCRIPT / "frenchcab.db"
ZONES_CSV = DOSSIER_ZONE / "raw_data" / "taxi_zone_lookup.csv"
# ============================================================
# CONNEXION SQLITE
# ============================================================

connexion = sqlite3.connect(DB_PATH)
curseur = connexion.cursor()

# ============================================================
# CRÉATION DES TABLES
# ============================================================

def initialiser_bdd():
    connexion = sqlite3.connect(DB_PATH)
    connexion.execute("DROP TABLE IF EXISTS Faits_Prediction")
    connexion.execute("DROP TABLE IF EXISTS Dim_Distance")
    connexion.execute("DROP TABLE IF EXISTS Dim_Temps")
    connexion.execute("DROP TABLE IF EXISTS Dim_Localisation")
    try:
        curseur = connexion.cursor()
    
        # ------------------------------------------------
        # TABLE DIM_TEMPS
        # ------------------------------------------------ 

        curseur.execute("PRAGMA foreign_keys = ON;")

        curseur.execute("""
                 CREATE TABLE IF NOT EXISTS Dim_Temps (
                        id_temps INTEGER PRIMARY KEY AUTOINCREMENT,
                        date_complete DATETIME,
                        annee INT,
                        mois INT,
                        jour DATE,
                        heure TIME,
                        minute TIME,
                        seconde TIME,
                        nom_jour TEXTE,
                        est_weekend BOOLEAN,
                        trimestre INT                                    
                            );
                        """)
        # ------------------------------------------------
        # TABLE DIM_LOCALISATION
        # ------------------------------------------------ 
    
        curseur.execute("""
                 CREATE TABLE IF NOT EXISTS Dim_Localisation (
                        id_localisation INTEGER PRIMARY KEY,
                        arrondissement VARCHAR,
                        zone           VARCHAR,
                        zone_service   VARCHAR                            
                        );
                        """)

         # ------------------------------------------------
        # TABLE DIM_DISTANCE
        # ------------------------------------------------
        curseur.execute("""
                 CREATE TABLE IF NOT EXISTS Dim_Distance (
                        id_localisation_d INTEGER,
                        id_localisation_a INTEGER,
                        distance_moyenne  REAL,
                        nb_trajets        INTEGER,

                        PRIMARY KEY (id_localisation_d, id_localisation_a),

                        FOREIGN KEY (id_localisation_d)
                            REFERENCES Dim_Localisation (id_localisation),

                        FOREIGN KEY (id_localisation_a)
                            REFERENCES Dim_Localisation (id_localisation)
                        );
                        """)
        # ------------------------------------------------
        # TABLE FAITS_PREDICTION
        # ------------------------------------------------ 

        curseur.execute("""
                 CREATE TABLE IF NOT EXISTS Faits_Prediction (
                        id_faits INTEGER PRIMARY KEY AUTOINCREMENT,
                        id_temps_d INT,
                        id_localisation_d INT,
                        id_temps_a INT,
                        id_localisation_a INT,
                        store_and_fwd_flag STRING,
                        trip_duration_min REAL,
                        trip_distance REAL,

                        FOREIGN KEY (id_temps_d) 
                            REFERENCES DIM_TEMPS (id_temps),

                        FOREIGN KEY (id_temps_a) 
                            REFERENCES DIM_TEMPS (id_temps),

                        FOREIGN KEY (id_localisation_d) 
                            REFERENCES DIM_LOCALISATION (id_localisation),

                        FOREIGN KEY (id_localisation_a) 
                            REFERENCES DIM_LOCALISATION (id_localisation)
                            );
                        """)
        
        # ------------------------------------------------
        # VALIDATION
        # ------------------------------------------------
        connexion.commit()

        print("Base de données initialisée avec succès.")

    except sqlite3.Error as erreur:
        print("Erreur SQLite :", erreur)
        connexion.rollback()

    finally:
        connexion.close()


# ============================================================
# INSERTION DE LA TABLE DIM_TEMPS
# ============================================================

def inserer_dim_temps(df):
    connexion = sqlite3.connect(DB_PATH)

    try:
    # traitement des doublons entre pickup et dropoff

        pickup = df[["tpep_pickup_datetime"]].copy()
        pickup.columns = ["date_complete"]

        dropoff = df[["tpep_dropoff_datetime"]].copy()
        dropoff.columns = ["date_complete"]

        df_temps = pd.concat([pickup, dropoff])

        df_temps = df_temps.drop_duplicates()

        df_temps["annee"] = df_temps["date_complete"].dt.year
        df_temps["mois"] = df_temps["date_complete"].dt.month
        df_temps["jour"] = df_temps["date_complete"].dt.day
        df_temps["nom_jour"] = df_temps["date_complete"].dt.day_name()
        df_temps["heure"] = df_temps["date_complete"].dt.hour
        df_temps["minute"] = df_temps["date_complete"].dt.minute
        df_temps["seconde"] = df_temps["date_complete"].dt.second

        df_temps["est_weekend"] = (
            df_temps["date_complete"].dt.dayofweek >= 5
        ).astype(int)

        df_temps["trimestre"] = (
            df_temps["date_complete"].dt.quarter
        )

        print("Données qui vont être insérées :")
        print(df_temps.head())

        df_temps.to_sql(
            "Dim_Temps",
            connexion,
            if_exists="append",
            index=False
        )

        connexion.commit()

    finally:
        connexion.close()

# ============================================================
# INSERTION DE LA TABLE DIM_LOCALISATION
# ============================================================
def inserer_dim_localisation(db_path=DB_PATH, zones_csv=ZONES_CSV, trajets_csv=None):

    con = duckdb.connect(str(db_path))
    
    # connexion.execute(f"""
    #     CREATE OR REPLACE TEMP VIEW trajets_src AS
    #     SELECT * REPLACE (
    #         CAST(tpep_pickup_datetime  AS TIMESTAMP) AS tpep_pickup_datetime,
    #         CAST(tpep_dropoff_datetime AS TIMESTAMP) AS tpep_dropoff_datetime
    #     )
    #     FROM read_csv_auto('{trajets}')
        # """)
    

    for nom, chemin in [("zones", zones_csv), ]:
            if chemin is None or not Path(chemin).exists():
                raise FileNotFoundError(f"Fichier {nom} introuvable : {chemin}")
    zones = Path(zones_csv).as_posix()
    # trajets = Path(trajets_csv).as_posix()
    con.execute(f"""
        INSERT INTO Dim_Localisation
        SELECT LocationID,
               COALESCE(Borough, 'Inconnu'),
               COALESCE(Zone, 'Inconnu'),
            COALESCE(service_zone, 'Inconnu')
        FROM read_csv_auto('{zones}')
        """)

    con.close()
    
# ============================================================
# INSERTION DE LA TABLE DIM_DISTANCE
# ============================================================
def inserer_dim_distance(df):
    connexion = sqlite3.connect(DB_PATH)

    try:
        # Tous les ID présents dans Dim_Localisation
        ids = pd.read_sql_query(
            "SELECT id_localisation FROM Dim_Localisation",
            connexion
        )["id_localisation"]

        # Toutes les combinaisons départ / arrivée
        couples = pd.MultiIndex.from_product(
            [ids, ids],
            names=["id_localisation_d", "id_localisation_a"]
        ).to_frame(index=False)

        # Distance moyenne réelle par couple, à partir des trajets
        moyennes = (
            df.groupby(["PULocationID", "DOLocationID"])["trip_distance"]
              .agg(distance_moyenne="mean", nb_trajets="count")
              .reset_index()
              .rename(columns={
                  "PULocationID": "id_localisation_d",
                  "DOLocationID": "id_localisation_a",
              })
        )

        # Jointure : les couples sans trajet restent à NaN
        df_distance = couples.merge(
            moyennes,
            on=["id_localisation_d", "id_localisation_a"],
            how="left"
        )
        df_distance["nb_trajets"] = df_distance["nb_trajets"].fillna(0).astype(int)

        print("Données qui vont être insérées :")
        print(df_distance.head())
        print(f"{len(df_distance)} couples, "
              f"{df_distance['distance_moyenne'].isna().sum()} sans trajet (NaN)")

        df_distance.to_sql(
            "Dim_Distance",
            connexion,
            if_exists="append",
            index=False
        )
        connexion.commit()

    except (sqlite3.Error, KeyError) as erreur:
        print("Erreur lors de l'insertion de Dim_Distance :", erreur)
        connexion.rollback()

    finally:
        connexion.close()
# ============================================================
# INSERTION DE LA TABLE FAITS_PREDICTION
# ============================================================
def inserer_faits_prediction():

    connexion = sqlite3.connect(DB_PATH)

    try:
        # ------------------------------------------------
        # Récupération de la dimension temps depuis la BDD
        # ------------------------------------------------
        df_temps_bdd = pd.read_sql_query(
            """
            SELECT id_temps, date_complete
            FROM Dim_Temps
            """,
            connexion
        )

        # Conversion en datetime pour garantir le même type
        df_temps_bdd["date_complete"] = pd.to_datetime(
            df_temps_bdd["date_complete"]
        )

        # ------------------------------------------------
        # Copie du dataframe source
        # ------------------------------------------------
        df_faits = df.copy()

        # ------------------------------------------------
        # Jointure pour récupérer id_temps_d
        # ------------------------------------------------
        df_faits = df_faits.merge(
            df_temps_bdd,
            left_on="tpep_pickup_datetime",
            right_on="date_complete",
            how="left"
        )

        df_faits = df_faits.rename(
            columns={"id_temps": "id_temps_d"}
        )

        df_faits = df_faits.drop(
            columns=["date_complete"]
        )

        # ------------------------------------------------
        # Jointure pour récupérer id_temps_a
        # ------------------------------------------------
        df_faits = df_faits.merge(
            df_temps_bdd,
            left_on="tpep_dropoff_datetime",
            right_on="date_complete",
            how="left"
        )

        df_faits = df_faits.rename(
            columns={"id_temps": "id_temps_a"}
        )

        df_faits = df_faits.drop(
            columns=["date_complete"]
        )

        # ------------------------------------------------
        # Localisations
        # ------------------------------------------------
        df_faits["id_localisation_d"] = (
            df_faits["PULocationID"]
        )

        df_faits["id_localisation_a"] = (
            df_faits["DOLocationID"]
        )

        # ------------------------------------------------
        # Sélection finale des colonnes
        # ------------------------------------------------
        df_faits_final = df_faits[
            [
                "id_temps_d",
                "id_localisation_d",
                "id_temps_a",
                "id_localisation_a",
                "store_and_fwd_flag",
                "trip_duration_min",
                "trip_distance"
            ]
        ]

        # ------------------------------------------------
        # Suppression des lignes incomplètes
        # ------------------------------------------------
        df_faits_final = df_faits_final.dropna()

        # ------------------------------------------------
        # Vérification
        # ------------------------------------------------
        print("Données qui vont être insérées :")
        print(df_faits_final.head())

        print(f"Nombre de faits : {len(df_faits_final)}")

        # ------------------------------------------------
        # Insertion dans la table
        # ------------------------------------------------
        df_faits_final.to_sql(
            "Faits_Prediction",
            connexion,
            if_exists="append",
            index=False
        )

        connexion.commit()

        print(
            f"{len(df_faits_final)} lignes insérées "
            "dans Faits_Prediction."
        )

    except (sqlite3.Error, KeyError, ValueError) as erreur:

        print("Erreur lors de l'insertion " "des faits :",erreur)

        connexion.rollback()

    finally:
        connexion.close()


# ============================================================
# EXECUTION
# ============================================================
if __name__ == "__main__":

    initialiser_bdd()
    inserer_dim_temps(df)
    inserer_dim_localisation()
    inserer_dim_distance(df)
    inserer_faits_prediction()
