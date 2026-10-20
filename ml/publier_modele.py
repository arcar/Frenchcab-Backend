
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path


# ============================================================
# 1. CONFIGURATION - DEV ET PRODUCTION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent
DOSSIER_ML = Path(os.getenv("ML_DIR", str(DOSSIER_SCRIPT)))
MODELS_DIR = Path(
    os.getenv("MODELS_DIR", str(DOSSIER_ML / "modeles"))
)

PRODUCTION = DOSSIER_ML / "modele_temps_trajet.pkl"
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
    if not re.fullmatch(r"v[1-9][0-9]*", version):
        raise ValueError("Version invalide : utiliser v1, v2, v3...")

    return MODELS_DIR / version / "model.pkl"


def remplacer_fichier(source, destination):
    """Remplace un fichier en preparant une copie temporaire."""
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        suffix=".tmp",
        delete=False
    ) as fichier:
        temporaire = Path(fichier.name)

    try:
        shutil.copy2(source, temporaire)
        os.replace(temporaire, destination)
    finally:
        temporaire.unlink(missing_ok=True)


def enregistrer_etat(etat):
    """Enregistre le fichier JSON via un fichier temporaire."""
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
# 3. VERIFIER QUE LA VERSION A ETE EVALUEE
# ============================================================

def verifier_version(version, rapport):
    modele = chemin_version(version)

    if not modele.is_file():
        raise FileNotFoundError(f"Modele introuvable : {modele}")

    # Format produit par MLO.py :
    # "actuelle" et "candidate"
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
            f"La version {version} n'a pas d'evaluation "
            "dans resultats_comparaison.json"
        )

    sha_reel = calculer_sha256(modele)
    sha_evalue = evaluation.get("sha256")

    # Le MLO.py actuel enregistre 12 caracteres SHA-256.
    if (
        not isinstance(sha_evalue, str)
        or not re.fullmatch(r"[0-9a-f]{12,64}", sha_evalue)
        or not sha_reel.startswith(sha_evalue)
    ):
        raise ValueError(
            f"Le modele {version} ne correspond pas "
            "au modele evalue"
        )

    mae = float(evaluation["mae_minutes"])

    if not (0 <= mae <= SEUIL_MAE):
        raise ValueError(
            f"Modele {version} refuse : MAE = {mae} minutes"
        )

    # Le rapport doit avoir utilise notre seuil
    # et les donnees d'evaluation attendues.
    if float(rapport["seuil_mae_minutes"]) != SEUIL_MAE:
        raise ValueError("Seuil du rapport incompatible")

    if rapport.get("donnees_test") != "yellow_tripdata_2026-04.parquet":
        raise ValueError("Jeu d'evaluation non reconnu")

    return modele, sha_reel, mae


# ============================================================
# 4. IDENTIFIER LA VERSION ACTUELLE
# ============================================================

def identifier_version_active():
    if not PRODUCTION.is_file():
        raise FileNotFoundError(
            "Modele de production introuvable"
        )

    sha_production = calculer_sha256(PRODUCTION)

    # Cas normal : une activation a deja eu lieu
    if ETAT.is_file():
        etat = lire_json(ETAT)
        version = etat.get("version")

        if not version:
            raise ValueError("Version active absente de l'etat")

        fichier = chemin_version(version)

        if (
            not fichier.is_file()
            or calculer_sha256(fichier) != sha_production
        ):
            raise ValueError(
                "Incoherence entre le modele actif "
                "et version_active.json"
            )

        return version

    # Premiere activation : retrouver la version
    # correspondant au modele deja en production.
    if MODELS_DIR.is_dir():
        for dossier in MODELS_DIR.iterdir():
            if dossier.is_dir() and re.fullmatch(
                r"v[1-9][0-9]*", dossier.name
            ):
                fichier = chemin_version(dossier.name)

                if (
                    fichier.is_file()
                    and calculer_sha256(fichier) == sha_production
                ):
                    return dossier.name

    raise ValueError(
        "Impossible d'identifier la version en production. "
        "Activation refusee pour proteger le modele existant."
    )


# ============================================================
# 5. ACTIVER UNE VERSION
# ============================================================

def activer_version(version):
    rapport = lire_json(RESULTATS)

    modele, sha, mae = verifier_version(version, rapport)
    version_actuelle = identifier_version_active()

    if version == version_actuelle:
        print(f"La version {version} est deja active.")
        return

    nouvel_etat = {
        "version": version,
        "precedente": version_actuelle,
        "sha256_actif": sha,
        "date_activation": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    # Sauvegardes temporaires en cas d'erreur Python
    with tempfile.TemporaryDirectory(dir=DOSSIER_ML) as dossier:
        secours = Path(dossier)

        sauvegarde_modele = secours / "production.pkl"
        sauvegarde_etat = secours / "etat.json"

        shutil.copy2(PRODUCTION, sauvegarde_modele)

        if ETAT.exists():
            shutil.copy2(ETAT, sauvegarde_etat)

        try:
            remplacer_fichier(modele, PRODUCTION)
            enregistrer_etat(nouvel_etat)

        except Exception:
            remplacer_fichier(sauvegarde_modele, PRODUCTION)

            if sauvegarde_etat.exists():
                remplacer_fichier(sauvegarde_etat, ETAT)
            else:
                ETAT.unlink(missing_ok=True)

            raise

    print("=== ACTIVATION REUSSIE ===")
    print("Version active :", version)
    print("Version precedente :", version_actuelle)
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
        help="Version a activer : v1, v2, v3..."
    )

    args = parser.parse_args()

    try:
        activer_version(args.version)
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
