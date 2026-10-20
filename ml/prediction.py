
import os
import json
from pathlib import Path

import joblib
import pandas as pd
import hashlib


# ============================================================
# CONFIGURATION - LOCAL ET DOCKER
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent

DOSSIER_ML = Path(
    os.getenv("ML_DIR", str(DOSSIER_SCRIPT))
)

MODEL_PATH = Path(
    os.getenv(
        "MODEL_PATH",
        str(DOSSIER_ML / "modele_temps_trajet.pkl")
    )
)

VERSION_ACTIVE_PATH = DOSSIER_ML / "version_active.json"



# ============================================================
# CHARGEMENT DU MODELE ET DE SA VERSION
# ============================================================

modele = joblib.load(MODEL_PATH)

VERSION_MODELE_CHARGE = "non_identifiee"

if VERSION_ACTIVE_PATH.is_file():

    with open(VERSION_ACTIVE_PATH, "r", encoding="utf-8") as fichier:
        etat = json.load(fichier)

    # Calculer l'empreinte du fichier charge
    sha = hashlib.sha256()

    with open(MODEL_PATH, "rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
            sha.update(bloc)

    # Verifier que le modele correspond a la version active
    if sha.hexdigest() != etat["sha256_actif"]:
        raise ValueError(
            "Le modele charge ne correspond pas a la version active"
        )

    VERSION_MODELE_CHARGE = etat["version_active"]


def obtenir_version_modele():
    return VERSION_MODELE_CHARGE


# ============================================================
# INFORMATIONS DU MODELE
# ============================================================

def obtenir_version_modele():
    return VERSION_MODELE_CHARGE


# ============================================================
# FONCTION DE PREDICTION
# ============================================================

def predire_temps_trajet(
    trip_distance,
    heure,
    minute,
    mois,
    est_weekend,
    nom_jour,
    id_localisation_d,
    id_localisation_a
):

    donnees = pd.DataFrame([
        {
            "nom_jour": nom_jour,
            "id_localisation_d": id_localisation_d,
            "id_localisation_a": id_localisation_a,
            "trip_distance": trip_distance,
            "heure": heure,
            "minute": minute,
            "est_weekend": int(est_weekend),
            "mois": mois
        }
    ])

    prediction = modele.predict(donnees)

    temps_estime = prediction[0]

    return float(temps_estime)


# ============================================================
# TEST LOCAL
# ============================================================

if __name__ == "__main__":

    print("Version du modele charge :", obtenir_version_modele())

    resultat = predire_temps_trajet(
        trip_distance=5.2,
        heure=14,
        minute=30,
        mois=1,
        est_weekend=0,
        nom_jour="Friday",
        id_localisation_d=132,
        id_localisation_a=161
    )

    print(f"Temps de trajet estimé : {resultat:.2f} minutes")
