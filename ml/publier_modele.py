import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

DOSSIER_ML = Path(os.getenv("ML_DIR", "/ml"))

CANDIDAT = DOSSIER_ML / "modele_candidat.pkl"
EVALUATION = DOSSIER_ML / "resultats_candidat.json"

PRODUCTION = DOSSIER_ML / "modele_temps_trajet.pkl"
RESULTATS_PRODUCTION = DOSSIER_ML / "resultats.json"


def main():

    if not CANDIDAT.is_file():
        sys.exit("ECHEC : modèle candidat introuvable")

    if not EVALUATION.is_file():
        sys.exit("ECHEC : évaluation du candidat introuvable")

    rapport = json.loads(EVALUATION.read_text(encoding="utf-8"))

    version_candidat = hashlib.sha256(
        CANDIDAT.read_bytes()
    ).hexdigest()[:12]

    version_evaluee = rapport["modele"]["version"]

    if version_candidat != version_evaluee:
        sys.exit("ECHEC : le candidat ne correspond pas au modèle évalué")

    if (
        rapport["statut"] != "OK"
        or rapport["mae_minutes"] > 6
    ):
        sys.exit("ECHEC : le modèle candidat ne respecte pas le seuil de qualité")

    # Préparer le nouveau modèle sans écraser directement
    # celui actuellement en production
    temporaire = DOSSIER_ML / "modele_production.tmp"

    shutil.copy2(CANDIDAT, temporaire)
    os.replace(temporaire, PRODUCTION)

    # Conserver le rapport correspondant au modèle publié
    shutil.copy2(EVALUATION, RESULTATS_PRODUCTION)

    print("Publication réussie")
    print("Version :", version_candidat)
    print("MAE :", rapport["mae_minutes"], "minutes")


if __name__ == "__main__":
    main()