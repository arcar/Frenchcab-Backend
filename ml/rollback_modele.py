
import json
import sys
from datetime import datetime

from ml import publier_modele


# ============================================================
# 1. ROLLBACK DU MODELE
# ============================================================

def rollback():
    # Lire l'état actuel
    etat = publier_modele.lire_json(publier_modele.ETAT)

    version_actuelle = etat.get("version")
    version_precedente = etat.get("precedente")

    if not version_actuelle:
        raise ValueError("Aucune version active identifiee")

    if not version_precedente:
        raise ValueError(
            "Rollback impossible : aucune version precedente"
        )

    if version_actuelle == version_precedente:
        raise ValueError(
            "Rollback impossible : les deux versions sont identiques"
        )

    # Vérifier la cohérence de la version actuellement active
    version_verifiee = publier_modele.identifier_version_active()

    if version_verifiee != version_actuelle:
        raise ValueError(
            "Incoherence entre la version active et le fichier d'etat"
        )

    # Lire le rapport de comparaison
    rapport = publier_modele.lire_json(publier_modele.RESULTATS)

    # Vérifier le modèle à restaurer
    modele, sha, mae = publier_modele.verifier_version(
        version_precedente,
        rapport
    )

    # Préparer le nouvel état
    nouvel_etat = {
        "version": version_precedente,
        "precedente": version_actuelle,
        "sha256_actif": sha,
        "date_activation": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    # Aucun fichier .pkl n'est déplacé ou copié.
    # Seul le fichier JSON change.
    publier_modele.enregistrer_etat(nouvel_etat)

    print("=== ROLLBACK REUSSI ===")
    print("Version restauree :", version_precedente)
    print("Ancienne version active :", version_actuelle)
    print("Fichier modele :", modele)
    print("SHA-256 :", sha[:12])
    print("MAE :", mae, "minutes")
    print("Redemarrer le backend pour charger le modele.")

    return version_precedente


# ============================================================
# 2. EXECUTION
# ============================================================

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
        sys.exit(f"ECHEC ROLLBACK : {erreur}")


if __name__ == "__main__":
    main()
