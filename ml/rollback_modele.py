
import json
import sys

from publier_modele import (
    DOSSIER_ML,
    ETAT,
    PRODUCTION,
    RESULTATS,
    calculer_sha256,
    enregistrer_etat,
    lire_json,
    remplacer_fichier,
    verifier_version,
)


def restaurer_version_precedente():

    # ==========================================
    # 1. LECTURE DE L'ETAT ACTUEL
    # ==========================================

    if not ETAT.is_file():
        raise FileNotFoundError(
            "Aucun fichier version_active.json disponible"
        )

    etat = lire_json(ETAT)

    version_actuelle = etat.get("version_active")
    version_precedente = etat.get("version_precedente")

    if not version_precedente:
        raise ValueError(
            "Aucune version precedente disponible pour le rollback"
        )

    if version_actuelle == version_precedente:
        raise ValueError(
            "Les versions active et precedente sont identiques"
        )

    # ==========================================
    # 2. CONTROLE DU MODELE ACTUEL
    # ==========================================

    if not PRODUCTION.is_file():
        raise FileNotFoundError(
            "Le modele de production est introuvable"
        )

    sha_production = calculer_sha256(PRODUCTION)

    if sha_production != etat.get("sha256_actif"):
        raise ValueError(
            "Le fichier de production ne correspond pas "
            "a la version active enregistree"
        )

    # ==========================================
    # 3. VERIFICATION DE LA VERSION PRECEDENTE
    # ==========================================

    rapport = lire_json(RESULTATS)

    chemin_precedent, sha_precedent, mae = verifier_version(
        version_precedente,
        rapport
    )

    # ==========================================
    # 4. PREPARATION DU NOUVEL ETAT
    # ==========================================

    nouvel_etat = {
        "version_active": version_precedente,
        "version_precedente": version_actuelle,
        "sha256_actif": sha_precedent
    }

    # ==========================================
    # 5. RESTAURATION DU MODELE
    # ==========================================

    # On utilise un verrou pour eviter qu'une
    # activation et un rollback se chevauchent.
    # Le verrou commun sera ajoute aux deux scripts
    # lors de l'etape de securisation.

    import shutil
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory(dir=DOSSIER_ML) as sauvegarde:
        dossier_secours = Path(sauvegarde)

        ancien_modele = dossier_secours / "production.pkl"
        ancien_etat = dossier_secours / "etat.json"

        shutil.copy2(PRODUCTION, ancien_modele)
        shutil.copy2(ETAT, ancien_etat)

        try:
            remplacer_fichier(chemin_precedent, PRODUCTION)
            enregistrer_etat(nouvel_etat)

        except Exception:
            remplacer_fichier(ancien_modele, PRODUCTION)
            remplacer_fichier(ancien_etat, ETAT)
            raise

    # ==========================================
    # 6. CONFIRMATION
    # ==========================================

    print("=== ROLLBACK REUSSI ===")
    print("Version restauree :", version_precedente)
    print("Version precedente :", version_actuelle)
    print("SHA-256 :", sha_precedent[:12])
    print("MAE :", mae, "minutes")
    print("Redemarrage du backend necessaire")


def main():
    try:
        restaurer_version_precedente()

    except (
        FileNotFoundError,
        KeyError,
        ValueError,
        OSError,
        json.JSONDecodeError
    ) as erreur:
        sys.exit(f"ECHEC : {erreur}")


if __name__ == "__main__":
    main()
