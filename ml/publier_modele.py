
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


# ==========================================
# 1. CHEMINS DES FICHIERS
# ==========================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent

DOSSIER_ML = Path(os.getenv("ML_DIR", str(DOSSIER_SCRIPT)))

PRODUCTION = DOSSIER_ML / "modele_temps_trajet.pkl"
RESULTATS_PRODUCTION = DOSSIER_ML / "resultats.json"


# ==========================================
# 2. CALCUL DE LA VERSION DU MODELE
# ==========================================

def calculer_version(chemin_modele):
    sha256 = hashlib.sha256()

    with open(chemin_modele, "rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
            sha256.update(bloc)

    return sha256.hexdigest()[:12]


# ==========================================
# 3. ACTIVATION D'UNE VERSION
# ==========================================

def main():

    # Choisir explicitement V1 ou V2
    parser = argparse.ArgumentParser(
        description="Activer une version du modèle Frenchcab"
    )

    parser.add_argument(
        "--version",
        required=True,
        choices=["v1", "v2"],
        help="Version du modèle à activer"
    )

    args = parser.parse_args()

    # Fichiers correspondant à la version choisie
    candidat = DOSSIER_ML / f"modele_{args.version}.pkl"
    evaluation = DOSSIER_ML / f"resultats_{args.version}.json"

    # ======================================
    # VERIFICATION DES FICHIERS
    # ======================================

    if not candidat.is_file():
        sys.exit(
            f"ECHEC : modèle introuvable : {candidat}"
        )

    if not evaluation.is_file():
        sys.exit(
            f"ECHEC : évaluation introuvable : {evaluation}"
        )

    # ======================================
    # VERIFICATION DU MODELE EVALUE
    # ======================================

    rapport = json.loads(
        evaluation.read_text(encoding="utf-8")
    )

    version_candidat = calculer_version(candidat)

    version_evaluee = rapport["modele"]["version"]

    if version_candidat != version_evaluee:
        sys.exit(
            "ECHEC : le modèle sélectionné ne correspond "
            "pas au modèle évalué"
        )

    # ======================================
    # VERIFICATION DE LA QUALITE
    # ======================================

    if (
        rapport["statut"] != "OK"
        or rapport["mae_minutes"] > 6
    ):
        sys.exit(
            "ECHEC : le modèle ne respecte pas "
            "le seuil de qualité"
        )

    # ======================================
    # SAUVEGARDE DU MODELE PRECEDENT
    # ======================================

    precedent = DOSSIER_ML / "modele_precedent.pkl"
    resultats_precedents = DOSSIER_ML / "resultats_precedents.json"

    if PRODUCTION.is_file():
        shutil.copy2(PRODUCTION, precedent)

    if RESULTATS_PRODUCTION.is_file():
        shutil.copy2(
            RESULTATS_PRODUCTION,
            resultats_precedents
        )

    # ======================================
    # PUBLICATION DU MODELE SELECTIONNE
    # ======================================

    temporaire = DOSSIER_ML / "modele_production.tmp"

    shutil.copy2(candidat, temporaire)
    os.replace(temporaire, PRODUCTION)

    # Conserver le rapport du modèle actif
    shutil.copy2(
        evaluation,
        RESULTATS_PRODUCTION
    )

    print("Activation réussie")
    print("Version sélectionnée :", args.version)
    print("Empreinte du modèle :", version_candidat)
    print("MAE :", rapport["mae_minutes"], "minutes")
    print("Modèle actif :", PRODUCTION)
    print("Redémarrage du backend nécessaire")


if __name__ == "__main__":
    main()
