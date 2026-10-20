
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


# Chemins compatibles local et Docker
DOSSIER_SCRIPT = Path(__file__).resolve().parent
DOSSIER_ML = Path(os.getenv("ML_DIR", str(DOSSIER_SCRIPT)))

PRODUCTION = DOSSIER_ML / "modele_temps_trajet.pkl"
RESULTATS_PRODUCTION = DOSSIER_ML / "resultats.json"

PRECEDENT = DOSSIER_ML / "modele_precedent.pkl"
RESULTATS_PRECEDENTS = DOSSIER_ML / "resultats_precedents.json"


def calculer_version(chemin):
    sha256 = hashlib.sha256()

    with open(chemin, "rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
            sha256.update(bloc)

    return sha256.hexdigest()[:12]


def main():

    if not PRECEDENT.is_file():
        sys.exit("ECHEC : aucun modèle précédent disponible")

    if not RESULTATS_PRECEDENTS.is_file():
        sys.exit("ECHEC : rapport du modèle précédent introuvable")

    rapport = json.loads(
        RESULTATS_PRECEDENTS.read_text(encoding="utf-8")
    )

    version_precedente = calculer_version(PRECEDENT)

    if version_precedente != rapport["modele"]["version"]:
        sys.exit(
            "ECHEC : le modèle précédent ne correspond "
            "pas au rapport enregistré"
        )

    if (
        rapport["statut"] != "OK"
        or rapport["mae_minutes"] > 6
    ):
        sys.exit(
            "ECHEC : le modèle précédent ne respecte "
            "pas le seuil de qualité"
        )

    # Restaurer le modèle précédent
    temporaire = DOSSIER_ML / "modele_restauration.tmp"
    shutil.copy2(PRECEDENT, temporaire)
    os.replace(temporaire, PRODUCTION)

    shutil.copy2(
        RESULTATS_PRECEDENTS,
        RESULTATS_PRODUCTION
    )

    print("Rollback réussi")
    print("Version restaurée :", version_precedente)
    print("MAE :", rapport["mae_minutes"], "minutes")
    print("Redémarrage du backend nécessaire")


if __name__ == "__main__":
    main()
