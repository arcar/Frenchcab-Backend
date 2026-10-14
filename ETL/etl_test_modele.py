
from pathlib import Path

import pandas as pd
import requests


# ============================================================
# CONFIGURATION
# ============================================================

DOSSIER_BACKEND = Path(__file__).resolve().parents[1]
DOSSIER_DATA = DOSSIER_BACKEND / "raw_data"

# Exemple : mois différent de janvier 2026 (Données entrainement)
YEAR = 2026
MONTH = 1

NOM_FICHIER = f"yellow_tripdata_{YEAR}-{MONTH:02d}.parquet"

URL = (
    "https://d37ci6vzurychx.cloudfront.net/trip-data/"
    f"{NOM_FICHIER}"
)

FICHIER_PARQUET = DOSSIER_DATA / NOM_FICHIER
FICHIER_CSV = DOSSIER_DATA / "yellow_tripdata_test_propre.csv"


# ============================================================
# EXTRACT : TÉLÉCHARGEMENT DES DONNÉES
# ============================================================

def extract():
    DOSSIER_DATA.mkdir(parents=True, exist_ok=True)

    if not FICHIER_PARQUET.exists():
        print(f"Téléchargement de {NOM_FICHIER}...")

        response = requests.get(URL, timeout=180)
        response.raise_for_status()

        FICHIER_PARQUET.write_bytes(response.content)

        print("Téléchargement terminé !")
    else:
        print("Fichier Parquet déjà présent.")

    df = pd.read_parquet(FICHIER_PARQUET)

    print(f"Données extraites : {df.shape}")

    return df


# ============================================================
# TRANSFORM : NETTOYAGE DES DONNÉES
# ============================================================

def transform(df):
    df = df.copy()

    colonnes_requises = [
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "trip_distance",
        "fare_amount",
        "total_amount",
        "PULocationID",
        "DOLocationID",
    ]

    manquantes = [
        col for col in colonnes_requises
        if col not in df.columns
    ]

    if manquantes:
        raise ValueError(
            f"Colonnes TLC manquantes : {manquantes}"
        )

    # Conversion des dates
    for col in [
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
    ]:
        df[col] = pd.to_datetime(
            df[col], errors="coerce"
        )

    # Conversion des colonnes numériques
    colonnes_numeriques = [
        "trip_distance",
        "fare_amount",
        "total_amount",
        "PULocationID",
        "DOLocationID",
    ]

    for col in colonnes_numeriques:
        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        )

    # Supprimer les doublons
    df = df.drop_duplicates()

    # Calcul de la durée réelle en minutes
    df["trip_duration_min"] = (
        df["tpep_dropoff_datetime"]
        - df["tpep_pickup_datetime"]
    ).dt.total_seconds() / 60

    # Même logique de nettoyage que dans Transform.py
    df = df.dropna(
        subset=colonnes_requises
        + ["trip_duration_min"]
    )

    df = df[
        (df["tpep_pickup_datetime"].dt.year == YEAR)
        & (df["tpep_pickup_datetime"].dt.month == MONTH)
        & (
            df["tpep_dropoff_datetime"]
            > df["tpep_pickup_datetime"]
        )
        & (df["trip_duration_min"] <= 300)
        & (df["trip_distance"] > 0)
        & (df["trip_distance"] <= 300)
        & (df["fare_amount"] > 0)
        & (df["total_amount"] > 0)
        & (df["total_amount"] <= 1000)
    ].copy()

    # Variables temporelles calculées
    df["pickup_hour"] = (
        df["tpep_pickup_datetime"].dt.hour
    )

    df["pickup_weekday"] = (
        df["tpep_pickup_datetime"].dt.dayofweek
    )

    print(f"Données après nettoyage : {df.shape}")

    return df.reset_index(drop=True)


# ============================================================
# LOAD : ENREGISTREMENT DU CSV DE TEST
# ============================================================

def load(df):
    df.to_csv(FICHIER_CSV, index=False)

    print(f"CSV de test enregistré : {FICHIER_CSV}")
    print(f"Nombre de courses : {len(df)}")


# ============================================================
# EXÉCUTION DE L'ETL
# ============================================================

if __name__ == "__main__":
    donnees_brutes = extract()
    donnees_propres = transform(donnees_brutes)
    load(donnees_propres)

    print("ETL de test terminé avec succès.")
