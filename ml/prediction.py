
import os
import json
import hashlib
from pathlib import Path

import joblib
import pandas as pd


# ============================================================
# CONFIGURATION - LOCAL ET PRODUCTION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent

DOSSIER_ML = Path(
    os.getenv("ML_DIR", str(DOSSIER_SCRIPT))
)

MODELS_DIR = Path(
    os.getenv("MODELS_DIR", str(DOSSIER_ML / "modeles"))
)

MODEL_PATH = Path(
    os.getenv(
        "MODEL_PATH",
        str(DOSSIER_ML / "modele_temps_trajet.pkl")
    )
)

VERSION_ACTIVE_PATH = MODELS_DIR / "version_active.json"


# ============================================================
# IDENTIFICATION DU MODELE
# ============================================================

def calculer_sha256(chemin):
    sha = hashlib.sha256()

    with open(chemin, "rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
            sha.update(bloc)

    return sha.hexdigest()


# ============================================================
# CHARGEMENT DU MODELE ET DE SA VERSION
# ============================================================

# On memorise la version au moment du chargement.
# Elle ne change pas tant que Python n'est pas recharge.

VERSION_MODELE_CHARGE = "non_identifiee"
SHA_MODELE_CHARGE = None

# Lire le modele une seule fois et calculer son empreinte
# a partir des memes octets.
donnees_modele = MODEL_PATH.read_bytes()

SHA_MODELE_CHARGE = hashlib.sha256(
    donnees_modele
).hexdigest()

# Controle de coherence avec le fichier d'etat
if VERSION_ACTIVE_PATH.is_file():

    with open(
        VERSION_ACTIVE_PATH,
        "r",
        encoding="utf-8"
    ) as fichier:
        etat = json.load(fichier)

    if SHA_MODELE_CHARGE != etat.get("sha256_actif"):
        raise ValueError(
            "Le modele de production ne correspond pas "
            "a la version active enregistree."
        )

    VERSION_MODELE_CHARGE = etat["version"]

# joblib charge le modele a partir des octets verifies
from io import BytesIO

modele = joblib.load(BytesIO(donnees_modele))


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

    return float(prediction[0])


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

    print(f"Temps de trajet estime : {resultat:.2f} minutes")
