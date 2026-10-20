
import hashlib
import json
import os
import re
from pathlib import Path

import joblib
import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent

DOSSIER_ML = Path(
    os.getenv("ML_DIR", str(DOSSIER_SCRIPT))
)

MODELS_DIR = Path(
    os.getenv("MODELS_DIR", str(DOSSIER_ML / "modeles"))
)

VERSION_ACTIVE_PATH = MODELS_DIR / "version_active.json"


# ============================================================
# 2. IDENTIFICATION DE LA VERSION ACTIVE
# ============================================================

if not VERSION_ACTIVE_PATH.is_file():
    raise FileNotFoundError(
        "Aucune version active : initialiser V1 avant "
        "d'effectuer des predictions."
    )

with open(VERSION_ACTIVE_PATH, "r", encoding="utf-8") as fichier:
    etat = json.load(fichier)

VERSION_MODELE_CHARGE = etat["version"]

if not re.fullmatch(r"v[1-9][0-9]*", VERSION_MODELE_CHARGE):
    raise ValueError("Version du modele invalide")

MODEL_PATH = MODELS_DIR / VERSION_MODELE_CHARGE / "model.pkl"

if not MODEL_PATH.is_file():
    raise FileNotFoundError(
        f"Modele actif introuvable : {MODEL_PATH}"
    )


# ============================================================
# 3. CONTROLE DU SHA-256
# ============================================================

def calculer_sha256(chemin):
    sha = hashlib.sha256()

    with open(chemin, "rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
            sha.update(bloc)

    return sha.hexdigest()


SHA_MODELE_CHARGE = calculer_sha256(MODEL_PATH)

if SHA_MODELE_CHARGE != etat.get("sha256_actif"):
    raise ValueError(
        "Le modele charge ne correspond pas "
        "au SHA-256 de version_active.json"
    )


# ============================================================
# 4. CHARGEMENT DU MODELE
# ============================================================

modele = joblib.load(MODEL_PATH)


def obtenir_version_modele():
    return VERSION_MODELE_CHARGE


# ============================================================
# 5. PREDICTION
# ============================================================

def predire_temps_trajet(
    trip_distance,
    heure,
    minute,
    mois,
    est_weekend,
    nom_jour,
    id_localisation_d,
    id_localisation_a,
):
    """
    Prédit la durée d'un trajet en minutes.

    Le paramètre mois est conservé pour rester compatible
    avec main.py, mais il n'est pas utilisé par le modèle actuel.
    """

    donnees = pd.DataFrame([{
        "nom_jour": nom_jour,
        "id_localisation_d": id_localisation_d,
        "id_localisation_a": id_localisation_a,
        "trip_distance": trip_distance,
        "heure": heure,
        "minute": minute,
        "est_weekend": int(est_weekend),
    }])

    prediction = modele.predict(donnees)

    return float(prediction[0])
