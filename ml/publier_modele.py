
import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path


# ============================================================
# 1. CONFIGURATION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent
DOSSIER_ML = Path(os.getenv("ML_DIR", str(DOSSIER_SCRIPT)))
MODELS_DIR = Path(
    os.getenv("MODELS_DIR", str(DOSSIER_ML / "modeles"))
)

RESULTATS = MODELS_DIR / "resultats_comparaison.json"
ETAT = MODELS_DIR / "version_active.json"

SEUIL_MAE = 6.0


# ============================================================
# 2. FONCTIONS UTILITAIRES
# ============================================================

def lire_json(chemin):
    if not chemin.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {chemin}")

    return json.loads(chemin.read_text(encoding="utf-8"))


def calculer_sha256(chemin):
    sha = hashlib.sha256()

    with open(chemin, "rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
            sha.update(bloc)

    return sha.hexdigest()


def chemin_version(version):
    if (
        not isinstance(version, str)
        or not re.fullmatch(r"v[1-9][0-9]*", version)
    ):
        raise ValueError("Version invalide : utiliser v1, v2, v3...")

    return MODELS_DIR / version / "model.pkl"


def enregistrer_etat(etat):
    """Enregistre le JSON sans créer de copie du modèle."""

    ETAT.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=ETAT.parent,
        suffix=".tmp",
        delete=False
    ) as fichier:
        temporaire = Path(fichier.name)
        json.dump(etat, fichier, indent=2, ensure_ascii=False)

    try:
        os.replace(temporaire, ETAT)
    finally:
        temporaire.unlink(missing_ok=True)


# ============================================================
# 3. VERIFICATION DU MODELE
# ============================================================

def verifier_version(version, rapport):
    modele = chemin_version(version)

    if not modele.is_file():
        raise FileNotFoundError(f"Modele introuvable : {modele}")

    evaluations = [
        rapport.get("actuelle"),
        rapport.get("candidate")
    ]

    evaluation = next(
        (
            item for item in evaluations
            if isinstance(item, dict)
            and item.get("version") == version
        ),
        None
    )

    if evaluation is None:
        raise ValueError(
            f"La version {version} n'a pas d'evaluation dans le rapport"
        )

    sha_reel = calculer_sha256(modele)
    sha_evalue = evaluation.get("sha256")

    if (
        not isinstance(sha_evalue, str)
        or not re.fullmatch(r"[0-9a-f]{12,64}", sha_evalue)
        or not sha_reel.startswith(sha_evalue)
    ):
        raise ValueError(
            f"Le modele {version} ne correspond pas au modele evalue"
        )

    mae = float(evaluation["mae_minutes"])

    if not math.isfinite(mae) or not 0 <= mae <= SEUIL_MAE:
        raise ValueError(
            f"Modele {version} refuse : MAE = {mae} minutes"
        )

    if float(rapport["seuil_mae_minutes"]) != SEUIL_MAE:
        raise ValueError("Seuil du rapport incompatible")

    if rapport.get("donnees_test") != "yellow_tripdata_2026-04.parquet":
        raise ValueError("Jeu d'evaluation non reconnu")

    return modele, sha_reel, mae


# ============================================================
# 4. IDENTIFICATION DE LA VERSION ACTIVE
# ============================================================

def identifier_version_active():
    if not ETAT.is_file():
        raise ValueError(
            "Aucune version active : initialiser V1 d'abord"
        )

    etat = lire_json(ETAT)
    version = etat.get("version")

    if not version:
        raise ValueError("Version active absente du fichier d'etat")

    modele = chemin_version(version)

    if not modele.is_file():
        raise FileNotFoundError(
            f"Modele actif introuvable : {modele}"
        )

    sha_reel = calculer_sha256(modele)

    if sha_reel != etat.get("sha256_actif"):
        raise ValueError(
            "Incoherence entre le modele actif et version_active.json"
        )

    return version


# ============================================================
# 5. ACTIVATION
# ============================================================

def activer_version(version, initialiser=False):
    rapport = lire_json(RESULTATS)

    # Contrôle qualité avant toute modification
    modele, sha, mae = verifier_version(version, rapport)

    if initialiser:
        if ETAT.exists():
            raise ValueError(
                "Initialisation refusee : une version active existe deja"
            )

        if version != "v1":
            raise ValueError(
                "La premiere initialisation doit utiliser v1"
            )

        version_precedente = None

    else:
        version_precedente = identifier_version_active()

        if version == version_precedente:
            print(f"La version {version} est deja active.")
            return

    nouvel_etat = {
        "version": version,
        "precedente": version_precedente,
        "sha256_actif": sha,
        "date_activation": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    # Seul le fichier JSON est modifié.
    enregistrer_etat(nouvel_etat)

    print("=== ACTIVATION REUSSIE ===")
    print("Version active :", version)
    print("Version precedente :", version_precedente)
    print("Fichier modele :", modele)
    print("SHA-256 :", sha[:12])
    print("MAE :", mae, "minutes")
    print("Redemarrer le backend pour charger le modele.")


# ============================================================
# 6. EXECUTION
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Activer une version du modele Frenchcab"
    )

    parser.add_argument(
        "--version",
        required=True,
        help="Version a activer : v1, v2..."
    )

    parser.add_argument(
        "--initialiser",
        action="store_true",
        help="Initialiser la premiere version active"
    )

    args = parser.parse_args()

    try:
        activer_version(
            args.version,
            initialiser=args.initialiser
        )
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
