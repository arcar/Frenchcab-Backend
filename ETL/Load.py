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
    
        curseur.execute("""
                 CREATE TABLE IF NOT EXISTS Dim_Localisation (
                                    id_localisation INTEGER PRIMARY KEY                            
                                    );
                        """)

        curseur.execute("""
                 CREATE TABLE IF NOT EXISTS Faits_Prediction (
                                    id_faits INTEGER PRIMARY KEY AUTOINCREMENT,
                                    id_temps_d INT,
                                    id_localisation_d INT,
                                    id_temps_a INT,
                                    id_localisation_a INT,
                                    store_and_fwd_flag STRING,
                                    trip_duration_min REAL,

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
# INSERTION DE LA TABLE COURSES
# ============================================================
# def inserer_courses():

#     connexion = sqlite3.connect(DB_PATH)

#     try:
# # recupération des éléments du dataframe
#         courses = df.copy()

# # Insertion des données récupérées
#         df_courses_final = courses[
#             [
#                 "VendorID",
#                 "tpep_pickup_datetime",
#                 "tpep_dropoff_datetime",
#                 "passenger_count",
#                 "trip_distance",
#                 "RatecodeID",
#                 "store_and_fwd_flag",
#                 "PULocationID",
#                 "DOLocationID",
#                 "payment_type",
#                 "fare_amount",
#                 "extra",
#                 "mta_tax",
#                 "tip_amount",
#                 "tolls_amount",
#                 "improvement_surcharge",
#                 "total_amount",
#                 "congestion_surcharge",
#                 "Airport_fee",
#                 "cbd_congestion_fee",
#                 "trip_duration_min",
#                 "pickup_hour",
#                 "pickup_weekday"
#             ]
#         ]
# # Vérification
#         print("Données qui vont être insérées :")
#         print(df_courses_final.head())

        df_courses_final.to_sql(
            "Courses",
            connexion,
            if_exists="append",
            index=False
        )
        print(f"Nombre de courses : {len(df_courses_final)}")

#         connexion.commit()

#         print(f"{len(df_courses_final)} lignes insérées dans la table courses.")

#     except (sqlite3.Error, KeyError, ValueError) as erreur:

#         print("Erreur lors de l'insertion des courses :",erreur)

#         connexion.rollback()

#     finally:

#         connexion.close()

# ============================================================
# EXECUTION
# ============================================================
if __name__ == "__main__":
    initialiser_bdd()
    # inserer_courses()
