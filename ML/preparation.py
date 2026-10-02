import pandas as pd
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# ---------------------------------
# CONNEXION BASE ANALYTIQUEs
# ---------------------------------


dossier_script = Path(__file__).resolve().parent

chemin_bdd = dossier_script / "frenchcab.db"

print("Base SQLite :", chemin_bdd)

DATABASE_PATH = "frenchcab.db"

connexion = sqlite3.connect(chemin_bdd)
curseur = connexion.cursor()


# ---------------------------------
# CHARGEMENT DES DONNEES DE LA BASE ANALYTIQUE
# ---------------------------------

def charger_donnees_analytiques():
    connexion = sqlite3.connect(chemin_bdd)

    requete = """
    SELECT
        fp.trip_duration_min,
        fp.passenger_count,
        fp.trip_distance,
        fp.store_and_fwd_flag,

        dt.heure,
        dt.minute,
        dt.nom_jour,
        dt.est_weekend,
        dt.mois,

        fp.ID_Location_pickup,
        fp.ID_Location_dropoff

        FROM Faits_Prediction fp

        LEFT JOIN Dim_Temps dt
        ON fp.ID_temps_pickup = dt.ID_temps;
    """

    df = pd.read_sql_query(requete, connexion)

    connexion.close()

    return df

# ---------------------------------
# PREPARATION DATAFRAME
# ---------------------------------

def preparer_dataframe_ml(df):
    df_ml = df.copy()

    colonnes_ml = [
        "ID_temps",
        "ID_Location",
        "store_and_fwd_flag",
        "trip_duration_min",
        "passenger_count",
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
            "store_and_fwd_flag",
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
