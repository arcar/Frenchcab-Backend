
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from ml.publier_modele import (
    DOSSIER_ML,
    ETAT,
    PRODUCTION,
    RESULTATS,
    calculer_sha256,
    chemin_version,
    enregistrer_etat,
    lire_json,
    remplacer_fichier,
    verifier_version,
)


def rollback():

    # ==========================================
    # 1. LIRE LA VERSION ACTIVE ET PRECEDENTE
    # ==========================================

    if not ETAT.is_file():
        raise FileNotFoundError(
            "Aucune version active enregistree"
        )

    etat = lire_json(ETAT)

    version_actuelle = etat.get("version")
    version_precedente = etat.get("precedente")

    if not version_precedente:
        raise ValueError(
            "Aucune version precedente disponible"
        )

    # ==========================================
    # 2. VERIFIER LE MODELE ACTUEL
    # ==========================================

    if not PRODUCTION.is_file():
        raise FileNotFoundError(
            "Modele de production introuvable"
        )

    sha_actuel = calculer_sha256(PRODUCTION)

    if sha_actuel != etat.get("sha256_actif"):
        raise ValueError(
            "Le modele de production ne correspond "
            "pas a la version active enregistree"
        )

    fichier_actuel = chemin_version(version_actuelle)

    if (
        not fichier_actuel.is_file()
        or calculer_sha256(fichier_actuel) != sha_actuel
    ):
        raise ValueError(
            "La version active ne correspond pas "
            "au modele de production"
        )

    # ==========================================
    # 3. VERIFIER LA VERSION A RESTAURER
    # ==========================================

    rapport = lire_json(RESULTATS)

    fichier_precedent, sha_precedent, mae = verifier_version(
        version_precedente,
        rapport
    )

    # ==========================================
    # 4. PREPARER LE NOUVEL ETAT
    # ==========================================

    nouvel_etat = {
        "version": version_precedente,
        "precedente": version_actuelle,
        "sha256_actif": sha_precedent,
        "date_activation": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    # ==========================================
    # 5. RESTAURER LE MODELE
    # ==========================================

    with tempfile.TemporaryDirectory(dir=DOSSIER_ML) as dossier:
        secours = Path(dossier)

        sauvegarde_modele = secours / "production.pkl"
        sauvegarde_etat = secours / "etat.json"

        shutil.copy2(PRODUCTION, sauvegarde_modele)
        shutil.copy2(ETAT, sauvegarde_etat)

        try:
            remplacer_fichier(fichier_precedent, PRODUCTION)
            enregistrer_etat(nouvel_etat)

        except Exception:
            remplacer_fichier(sauvegarde_modele, PRODUCTION)
            remplacer_fichier(sauvegarde_etat, ETAT)
            raise

    print("=== ROLLBACK REUSSI ===")
    print("Version restauree :", version_precedente)
    print("Version precedente :", version_actuelle)
    print("SHA-256 :", sha_precedent[:12])
    print("MAE :", mae, "minutes")
    print("Redemarrage du backend necessaire")


def main():
    try:
        rollback()
    except (
        FileNotFoundError,
        ValueError,
        KeyError,
        OSError,
        json.JSONDecodeError
    ) as erreur:
        sys.exit(f"ECHEC : {erreur}")


if __name__ == "__main__":
    main()
