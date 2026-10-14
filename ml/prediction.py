import os
from pathlib import Path
import joblib
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent

# MODEL_PATH permet de placer le modèle ailleurs (ex : volume Docker sur la VM)
MODEL_PATH = Path(os.getenv("MODEL_PATH", DOSSIER_SCRIPT / "modele_temps_trajet.pkl"))


# ============================================================
# CHARGEMENT DU MODÈLE
# ============================================================

modele = joblib.load(MODEL_PATH)


# ============================================================
# FONCTION DE PRÉDICTION
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

    # Création d'une ligne avec les mêmes features
    # que celles utilisées pendant l'entraînement
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

    # Prédiction
    prediction = modele.predict(donnees)

    # predict() renvoie un tableau, on récupère la première valeur
    temps_estime = prediction[0]

    return float(temps_estime)


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

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