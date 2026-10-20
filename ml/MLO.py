
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


def activer(version, precedente):
    FICHIER_ACTIVE.write_text(json.dumps({
        "version": version,
        "precedente": precedente,
        "date_activation": datetime.now().isoformat(timespec="seconds"),}, indent=2), encoding="utf-8")
    print(f"\nVersion active : {version} (précédente : {precedente})")

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
    mae = round(float(mean_absolute_error(y, y_pred)), 2)
    return mae, y_pred



# ============================================================
# 4. PIPELINE DU FICHIER
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Compare et active les versions du modèle")
    parser.add_argument("--candidate", help="version candidate (défaut : la plus récente)")
    parser.add_argument("--donnees", default=DONNEES_PAR_DEFAUT)
    parser.add_argument("--seuil", type=float, default=SEUIL_MAE_PAR_DEFAUT)
    parser.add_argument("--activer", action="store_true", help="applique la décision")
    parser.add_argument("--rollback", action="store_true", help="revient à la version précédente")
    args = parser.parse_args()

    etat = lire_etat_actif()

    # ---------- Retour arrière ----------
    if args.rollback:
        if not etat["precedente"]:
            sys.exit("Aucune version précédente enregistrée.")
        if not (MODELS_DIR / etat["precedente"] / "model.pkl").exists():
            sys.exit(f"La version {etat['precedente']} n'existe plus.")
        activer(etat["precedente"], etat["version"])
        return

    # ---------- Choix des versions ----------
    versions = lister_versions()
    if not versions:
        sys.exit(f"Aucune version trouvée dans {MODELS_DIR}")

    actuelle = etat["version"]
    candidate = args.candidate or versions[-1]

    # ---------- Évaluation sur le MÊME jeu ----------
    X, y = preparer_donnees_test(args.donnees)

    res_candidate = evaluer_version(candidate, X, y)
    res_actuelle = (
        evaluer_version(actuelle, X, y)
        if actuelle and actuelle != candidate else None
    )

    # ---------- Décision ----------
    mae_c = res_candidate["mae_minutes"]
    conforme = mae_c <= args.seuil

    if not conforme:
        decision = actuelle
        raison = f"{candidate} dépasse le seuil ({mae_c} > {args.seuil} min)"
    elif candidate == actuelle:
        decision = actuelle
        raison = f"{candidate} est déjà la version active"
    elif res_actuelle is None:
        decision = candidate
        raison = f"aucune version active, {candidate} respecte le seuil"
    elif mae_c < res_actuelle["mae_minutes"]:
        decision = candidate
        raison = f"{candidate} respecte le seuil et fait mieux que {actuelle}"
    else:
        decision = actuelle
        raison = f"{candidate} respecte le seuil mais ne fait pas mieux que {actuelle}"

    # ---------- Affichage lisible ----------
    print(f"\nComparaison sur {len(X)} trajets ({Path(args.donnees).name})\n")
    print(f"{'Rôle':<11}{'Version':<9}{'Algorithme':<24}{'MAE (min)':>10}")
    if res_actuelle:
        print(f"{'Actuelle':<11}{actuelle:<9}{res_actuelle['algorithme']:<24}" f"{res_actuelle['mae_minutes']:>10.2f}")
    print(f"{'Candidate':<11}{candidate:<9}{res_candidate['algorithme']:<24}{mae_c:>10.2f}")
    print(f"\nSeuil : {args.seuil} min → {'CONFORME' if conforme else 'NON CONFORME'}")
    print(f"Décision : {decision} ({raison})")

    # ---------- Sauvegarde du rapport ----------
    resultat = {
        "date_evaluation": datetime.now().isoformat(timespec="seconds"),
        "donnees_test": Path(args.donnees).name,
        "nb_trajets": len(X),
        "seuil_mae_minutes": args.seuil,
        "actuelle": res_actuelle,
        "candidate": {**res_candidate, "conforme": conforme},
        "decision": decision,
        "raison": raison,
    }
    chemin_resultats = Path(os.getenv(
        "RESULTATS_PATH", str(MODELS_DIR / "resultats_comparaison.json")
    ))
    chemin_resultats.write_text(
        json.dumps(resultat, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ---------- Activation (seulement si demandée) ----------
    if args.activer and decision and decision != actuelle:
        activer(decision, actuelle)
    elif args.activer:
        print("\nRien à activer, la version active reste inchangée.")

    # 0 = candidate conforme, 1 = échec -> exploitable par la CI
    sys.exit(0 if conforme else 1)


if __name__ == "__main__":
    main()