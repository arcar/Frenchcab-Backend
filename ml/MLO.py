
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


MODELS_DIR = Path(os.getenv("MODELS_DIR", str(DOSSIER_SCRIPT / "modeles")))
FICHIER_ACTIVE = MODELS_DIR / "version_active.json"

# données de test : avril 2026 (non vues à l'entraînement)
DONNEES_PAR_DEFAUT = Path(os.getenv("EVALUATION_DATA_PATH", str(DOSSIER_SCRIPT.parent / "raw_data" / "yellow_tripdata_2026-04.parquet")))

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

def lister_versions():
    if not MODELS_DIR.exists():
        return []
    versions = [d.name for d in MODELS_DIR.iterdir() if d.is_dir() and d.name.startswith("v") and d.name[1:].isdigit()]
    return sorted(versions, key=lambda v: int(v[1:]))


def lire_etat_actif():
    if FICHIER_ACTIVE.exists():
        return json.loads(FICHIER_ACTIVE.read_text(encoding="utf-8"))
    return {"version": None, "precedente": None}


def charger_version(version):
    dossier = MODELS_DIR / version
    if not (dossier / "model.pkl").exists():
        sys.exit(f"Version introuvable : {dossier}")
    modele = joblib.load(dossier / "model.pkl")
    metadata = json.loads((dossier / "metadata.json").read_text(encoding="utf-8"))
    return modele, metadata


def identifier_modele(version, metadata):
    chemin = MODELS_DIR / version / "model.pkl"
    return {
        "version": version,
        "algorithme": metadata["algorithme"],
        "date_entrainement": metadata["date_entrainement"],
        "sha256": hashlib.sha256(chemin.read_bytes()).hexdigest()[:12],
    }


def evaluer_version(version, X, y):
    modele, metadata = charger_version(version)
    mae, _ = evaluer(modele, X[metadata["features"]], y)
    return {**identifier_modele(version, metadata), "mae_minutes": mae}



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
    df["trip_duration_min"] = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds() / 60

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
    mae = float(mean_absolute_error(y, y_pred))
    return mae, y_pred



# ============================================================
# 4. PIPELINE DU FICHIER
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Évalue et compare deux versions du modèle")
    parser.add_argument("--actuelle", help="version de référence (défaut : version active)")
    parser.add_argument("--candidate", help="version candidate (défaut : la plus récente)")
    parser.add_argument("--donnees", default=DONNEES_PAR_DEFAUT)
    parser.add_argument("--seuil", type=float, default=SEUIL_MAE_PAR_DEFAUT)
    args = parser.parse_args()

    # ---------- Choix des versions ----------
    versions = lister_versions()
    if not versions:
        sys.exit(f"Aucune version trouvée dans {MODELS_DIR}")

    candidate = args.candidate or versions[-1]

    autres = [v for v in versions if v != candidate]
    actuelle = args.actuelle or lire_etat_actif()["version"] or (autres[-1] if autres else None)

    if not actuelle:
        sys.exit("Une seule version disponible : entraînez-en une autre pour comparer.")
    if actuelle == candidate:
        sys.exit(f"Les deux versions sont identiques ({actuelle}).")

    # ---------- Évaluation sur le MÊME jeu ----------
    X, y = preparer_donnees_test(args.donnees)

    resultats = {}
    for role, version in [("actuelle", actuelle), ("candidate", candidate)]:
        res = evaluer_version(version, X, y)
        res["conforme"] = res["mae_minutes"] <= args.seuil
        resultats[role] = res

    # ---------- Affichage lisible ----------
    print(f"\nComparaison sur {len(X)} trajets ({Path(args.donnees).name})")
    print(f"Seuil de qualité : MAE ≤ {args.seuil} min\n")
    print(f"{'Rôle':<11}{'Version':<9}{'Algorithme':<24}{'MAE (min)':>10}  Statut")
    for role, res in resultats.items():
        statut = "CONFORME" if res["conforme"] else "NON CONFORME"
        print(f"{role.capitalize():<11}{res['version']:<9}{res['algorithme']:<24}"
              f"{res['mae_minutes']:>10.2f}  {statut}")

    ecart = resultats["candidate"]["mae_minutes"] - resultats["actuelle"]["mae_minutes"]
    print(f"\nÉcart candidate - actuelle : {ecart:+.2f} min")

        # ---------- Sauvegarde du rapport ----------
    rapport = {
        "date_evaluation": datetime.now().isoformat(timespec="seconds"),
        "donnees_test": Path(args.donnees).name,
        "nb_trajets": len(X),
        "seuil_mae_minutes": args.seuil,
        **resultats,
    }

    texte = json.dumps(rapport, indent=2, ensure_ascii=False)

    # 1. Dernier rapport (lu par publier_modele.py)
    chemin_resultats = Path(os.getenv(
        "RESULTATS_PATH", str(MODELS_DIR / "resultats_comparaison.json")
    ))
    chemin_resultats.write_text(texte, encoding="utf-8")

    # 2. Copie datée dans l'historique
    dossier_historique = MODELS_DIR / "historique_rapports"
    dossier_historique.mkdir(parents=True, exist_ok=True)

    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom = f"{horodatage}_{actuelle}_vs_{candidate}.json"
    (dossier_historique / nom).write_text(texte, encoding="utf-8")

    print(f"Rapport : {chemin_resultats}")
    print(f"Historique : {dossier_historique / nom}")

    print("\nComparaison terminée.")

if __name__ == "__main__":
    main()