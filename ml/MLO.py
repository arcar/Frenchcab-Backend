
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error



DOSSIER_SCRIPT = Path(__file__).resolve().parent


MODEL_PATH = Path(os.getenv("MODEL_EVALUATION_PATH", "/ml/modele_candidat.pkl"))

# données de test  février 2026 (le modèle entraîné janvier 2026)
DONNEES_PAR_DEFAUT = Path(os.getenv("EVALUATION_DATA_PATH", "/raw_data/yellow_tripdata_2026-04.parquet"))

# Seuil de qualité au-delà de cette MAE (en minutes)
SEUIL_MAE_PAR_DEFAUT = 6.0

# nombre de trajets tirés au hasard pour l'évaluation
NB_LIGNES = 100_000

# Les colonnes utilisées pendant l'entraînement
FEATURES = [
    "nom_jour",
    "id_localisation_d",
    "id_localisation_a",
    "trip_distance",
    "heure",
    "minute",
    "est_weekend",
]

# ============================================================
# 1. IDENTIFICATION DU MODELE
# ============================================================

def identifier_modele(chemin_modele, modele):
    # empreinte SHA-256 du fichier , si le .pkl change, la version change
    sha256 = hashlib.sha256(chemin_modele.read_bytes()).hexdigest()

    #car la date d'entraînement n'est pas enregistrée dans le .pkl
    # on prend la date de dernière modification du fichier
    date_fichier = datetime.fromtimestamp(chemin_modele.stat().st_mtime)

    return {
        "fichier": chemin_modele.name,
        "version": sha256[:12],
        "date_modification_fichier": date_fichier.isoformat(timespec="seconds"),
        "algorithme": type(modele.named_steps["reg"]).__name__,
    }

# ============================================================
# 2. PREPARER UN NOUVEAU JEU DE DONNEE TEST
# ============================================================

def preparer_donnees_test(chemin_donnees, nb_lignes=NB_LIGNES):
    colonnes = [
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "trip_distance",
        "PULocationID",
        "DOLocationID",
    ]
    df = pd.read_parquet(chemin_donnees, columns=colonnes)

    # durée réelle en minutes comme dans transform.py
    df["trip_duration_min"] = (
        df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]
    ).dt.total_seconds() / 60

    # on retire les trajets aberrants
    df = df[
        (df["trip_duration_min"] > 0)
        & (df["trip_duration_min"] <= 300)
        & (df["trip_distance"] > 0)
        & (df["trip_distance"] <= 300)
    ].dropna()

    # echantillon aléatoire, toujours le même grâce à random_state
    if len(df) > nb_lignes:
        df = df.sample(n=nb_lignes, random_state=42)

    # mêmes features que l'entraînement
    depart = df["tpep_pickup_datetime"]
    X = pd.DataFrame({
        "nom_jour": depart.dt.day_name(),
        "id_localisation_d": df["PULocationID"].astype(int),
        "id_localisation_a": df["DOLocationID"].astype(int),
        "trip_distance": df["trip_distance"],
        "heure": depart.dt.hour,
        "minute": depart.dt.minute,
        "est_weekend": (depart.dt.dayofweek >= 5).astype(int),
    })[FEATURES]

    y = df["trip_duration_min"]

    return X, y

# ============================================================
# 3. EVALUER LE MODELE SUR CE NOUVEAU JEU DE DONNEE
# ============================================================

def evaluer(modele, X, y):
    y_pred = modele.predict(X)
    mae = round(float(mean_absolute_error(y, y_pred)), 2)
    return mae, y_pred



# ============================================================
# 4. PIPELINE DU FICHIER
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="évalue le modèle de durée de trajet")
    parser.add_argument("--donnees", default=DONNEES_PAR_DEFAUT, help="fichier parquet TLC de test")
    parser.add_argument("--seuil", type=float, default=SEUIL_MAE_PAR_DEFAUT, help="MAE max en minutes")
    args = parser.parse_args()

    modele = joblib.load(MODEL_PATH)
    X, y = preparer_donnees_test(args.donnees)

    mae, y_pred = evaluer(modele, X, y)

    resultat = {
        "modele": identifier_modele(MODEL_PATH, modele),
        "donnees_test": Path(args.donnees).name,
        "nb_trajets": len(X),
         "duree_moyenne_reelle_minutes": round(float(y.mean()), 2),
        "duree_moyenne_predite_minutes": round(float(y_pred.mean()), 2),
        "exemples": [
            {
                "duree_reelle_minutes": round(float(reel), 1),
                "duree_predite_minutes": round(float(predit), 1),
            }
            for reel, predit in zip(y[:5], y_pred[:5])
        ],
        "mae_minutes": mae,
        "seuil_mae_minutes": args.seuil,
        "statut": "OK" if mae <= args.seuil else "ECHEC",
    }

    texte = json.dumps(resultat, indent=2, ensure_ascii=False)
    print(texte)

    # Toujours enregistré dans ml/, quel que soit le dossier d'où on lance le script
    (DOSSIER_SCRIPT / "resultats.json").write_text(texte, encoding="utf-8")

    # code de sortie  0  succès, 1 = échec -> exploitable par la CI
    if mae > args.seuil:
        sys.exit(1)


if __name__ == "__main__":
    main()