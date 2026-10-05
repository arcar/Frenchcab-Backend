import pandas as pd
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ---------------------------------
# CONNEXION BASE ANALYTIQUEs
# ---------------------------------
DOSSIER_SCRIPT = Path(__file__).resolve().parent

DB_PATH = (DOSSIER_SCRIPT.parent/ "ETL"/ "frenchcab.db")

print("Base SQLite :", DB_PATH)

# ---------------------------------
# CHARGEMENT DES DONNEES DE LA BASE ANALYTIQUE
# ---------------------------------

def charger_donnees_analytiques(limit=None):
    connexion = sqlite3.connect(DB_PATH)

    requete = """
            SELECT
            fp.trip_duration_min,
            fp.trip_distance,

            dt.id_temps,
            dt.heure,
            dt.minute,
            dt.nom_jour,
            dt.est_weekend,
            dt.mois,

            fp.id_localisation_d,
            fp.id_localisation_a

            FROM Faits_Prediction fp

            LEFT JOIN Dim_Temps dt
                ON fp.id_temps_d = dt.id_temps
            """
    if limit is not None:
        requete += f" LIMIT {limit}"

    df = pd.read_sql_query(requete, connexion)

    connexion.close()

    return df

# ---------------------------------
# PREPARATION DATAFRAME
# ---------------------------------

def preparer_dataframe_ml(df):
    df_ml = df.copy()

    colonnes_ml = [
        "id_temps",
        "heure",
        "minute",
        "nom_jour",
        "est_weekend",
        "id_localisation_d",
        "id_localisation_a",
        "trip_duration_min",
        "trip_distance"
    ]

    df_ml = df_ml[colonnes_ml]

    df_ml = df_ml.dropna()

    return df_ml


if __name__ == "__main__":
    # ---------------------------------
    # Chargement
    # ---------------------------------
    df = charger_donnees_analytiques()

    # ---------------------------------
    # Préparation des données ML
    # ---------------------------------
    df_ml = preparer_dataframe_ml(df)

    # Encodage des variables catégorielles
    df_correlation = pd.get_dummies(
        df_ml,
        columns=[
            "nom_jour"
        ],
        drop_first=False
    )

    # ---------------------------------
    # Matrice de corrélation
    # ---------------------------------
    correlation = df_correlation.corr(numeric_only=True)

    print("Matrice de corrélation :")
    print(correlation)

    # ---------------------------------
    # Corrélation avec la durée du trajet
    # ---------------------------------
    correlation_duree = (
        correlation["trip_duration_min"]
        .sort_values(ascending=False)
    )

    print("\nCorrélation avec trip_duration_min :")
    print(correlation_duree)

    # ---------------------------------
    # Heatmap de corrélation
    # ---------------------------------
    plt.figure(figsize=(12, 8))

    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0
    )

    plt.title("Matrice de corrélation des variables")
    plt.tight_layout()
    plt.show()

# # ---------------------------------
# # DEFINIR lA CIBLE Y
# # ---------------------------------

# y = df_ml["trip_duration_min"]
