import sqlite3
from pathlib import Path
import pandas as pd
from Transform import df
import os

# ============================================================
# CONFIGURATION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent
DB_PATH = DOSSIER_SCRIPT / "frenchcab.db"

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
   
    try:
        curseur = connexion.cursor()
    
        # ------------------------------------------------
        # TABLE COURSES
        # ------------------------------------------------ 
        curseur.execute("""
                CREATE TABLE IF NOT EXISTS Courses (
                    VendorID TEXT PRIMARY KEY,
                    tpep_pickup_datetime DATETIME,
                    tpep_dropoff_datetime DATETIME,
                    passenger_count REAL,
                    trip_distance REAL,
                    RatecodeID REAL,
                    store_and_fwd_flag STRING,
                    PULocationID INT,
                    DOLocationID INT,
                    payment_type INT,
                    fare_amount REAL,
                    extra REAL,
                    mta_tax REAL,
                    tip_amount REAL,
                    tolls_amount REAL,
                    improvement_surcharge REAL,
                    total_amount REAL,
                    congestion_surcharge REAL,
                    Airport_fee REAL,
                    cbd_congestion_fee REAL,
                    trip_duration_min REAL,
                    pickup_hour INT,
                    pickup_weekday INT
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
# INSERTION DE LA TABLE COURSES
# ============================================================
def inserer_courses():

    connexion = sqlite3.connect(DB_PATH)

    try:
# recupération des éléments du dataframe
        courses = df.copy()

# Insertion des données récupérées
        df_courses_final = courses[
            [
                "VendorID",
                "tpep_pickup_datetime",
                "tpep_dropoff_datetime",
                "passenger_count",
                "trip_distance",
                "RatecodeID",
                "store_and_fwd_flag",
                "PULocationID",
                "DOLocationID",
                "payment_type",
                "fare_amount",
                "extra",
                "mta_tax",
                "tip_amount",
                "tolls_amount",
                "improvement_surcharge",
                "total_amount",
                "congestion_surcharge",
                "Airport_fee",
                "cbd_congestion_fee",
                "trip_duration_min",
                "pickup_hour",
                "pickup_weekday"
            ]
        ]
# Vérification
        print("Données qui vont être insérées :")
        print(df_courses_final.head())

        print(f"Nombre de courses : {len(df_courses_final)}")

        df_courses_final.to_sql(
            "courses",
            connexion,
            if_exists="append",
            index=False
        )

        connexion.commit()

        print(f"{len(df_courses_final)} lignes insérées dans la table courses.")

    except (sqlite3.Error, KeyError, ValueError) as erreur:

        print("Erreur lors de l'insertion des courses :",erreur)

        connexion.rollback()

    finally:

        connexion.close()

# ============================================================
# EXECUTION
# ============================================================
if __name__ == "__main__":
    initialiser_bdd()
    inserer_courses()
