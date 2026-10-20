
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path


# ============================================================
# CONFIGURATION - LOCAL ET DOCKER
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent

DOSSIER_ML = Path(
    os.getenv("ML_DIR", str(DOSSIER_SCRIPT))
)

DOSSIER_MODELES = Path(
    os.getenv("MODELS_DIR", str(DOSSIER_ML / "modeles"))
)

RESULTATS = DOSSIER_ML / "resultats.json"
PRODUCTION = DOSSIER_ML / "modele_temps_trajet.pkl"
ETAT = DOSSIER_ML / "version_active.json"

SEUIL_MAE = 6.0


# ============================================================
# OUTILS
# ============================================================

def calculer_sha256(chemin):
    sha = hashlib.sha256()

    with open(chemin, "rb") as fichier:
        for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
            sha.update(bloc)

    return sha.hexdigest()


def lire_json(chemin):
    if not chemin.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {chemin}")

    with open(chemin, "r", encoding="utf-8") as fichier:
        return json.load(fichier)


def remplacer_fichier(source, destination):
    """Copie dans un fichier temporaire, puis remplace la destination."""

    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=".modele_",
        suffix=".tmp",
        delete=False
    ) as temporaire:
        chemin_temp = Path(temporaire.name)

    try:
        shutil.copy2(source, chemin_temp)
        os.replace(chemin_temp, destination)
    finally:
        chemin_temp.unlink(missing_ok=True)


def enregistrer_etat(etat):
    """Enregistre l'etat via un fichier temporaire."""

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=DOSSIER_ML,
        prefix=".etat_",
        suffix=".tmp",
        delete=False
    ) as temporaire:
        chemin_temp = Path(temporaire.name)
        json.dump(etat, temporaire, indent=2, ensure_ascii=False)

    try:
        os.replace(chemin_temp, ETAT)
    finally:
        chemin_temp.unlink(missing_ok=True)


# ============================================================
# VERIFICATION D'UNE VERSION
# ============================================================

def verifier_version(version, rapport):
    versions = rapport.get("modeles", {})

    if version not in versions:
        raise ValueError(
            f"La version {version} n'est pas presente dans resultats.json"
        )

    evaluation = versions[version]

    chemin_modele = DOSSIER_MODELES / version / "model.pkl"

    if not chemin_modele.is_file():
        raise FileNotFoundError(
            f"Modele introuvable : {chemin_modele}"
        )

    sha_reel = calculer_sha256(chemin_modele)
    sha_evalue = evaluation.get("sha256", "")

    if (
        not isinstance(sha_evalue, str)
        or len(sha_evalue) < 12
        or not sha_reel.startswith(sha_evalue)
    ):
        raise ValueError(
            f"Empreinte SHA-256 incorrecte pour {version}"
        )

    mae = float(evaluation["mae_minutes"])

    if (
        evaluation.get("statut") != "OK"
        or not (0 <= mae <= SEUIL_MAE)
    ):
        raise ValueError(
            f"Version {version} non admissible : MAE = {mae}"
        )

    return chemin_modele, sha_reel, mae


# ============================================================
# IDENTIFICATION DU MODELE ACTIF
# ============================================================

def identifier_version_active(rapport):
    if not PRODUCTION.is_file():
        if ETAT.exists():
            raise ValueError(
                "Un etat existe, mais le modele de production est absent"
            )
        return None

    sha_actif = calculer_sha256(PRODUCTION)

    if ETAT.is_file():
        etat = lire_json(ETAT)
        version = etat["version_active"]

        chemin, sha_attendu, _ = verifier_version(version, rapport)

        if sha_actif != sha_attendu:
            raise ValueError(
                "Le fichier de production ne correspond pas "
                "a la version active enregistree"
            )

        return version

    # Initialisation : reconnaitre une version deja en production.
    for version in rapport.get("modeles", {}):
        chemin, sha, _ = verifier_version(version, rapport)

        if sha == sha_actif:
            return version

    raise ValueError(
        "Le modele actuellement en production n'est pas "
        "identifie dans resultats.json. Activation refusee."
    )


# ============================================================
# ACTIVATION
# ============================================================

def activer_version(version):
    if not re.fullmatch(r"v[1-9][0-9]*", version):
        raise ValueError("Format de version invalide")

    rapport = lire_json(RESULTATS)

    chemin_modele, sha, mae = verifier_version(version, rapport)
    version_actuelle = identifier_version_active(rapport)

    if version_actuelle == version:
        print(f"La version {version} est deja active.")
        return

    nouvel_etat = {
        "version_active": version,
        "version_precedente": version_actuelle,
        "sha256_actif": sha
    }

    # Sauvegarde de secours pour restaurer les fichiers
    # si une erreur Python survient pendant l'activation.
    with tempfile.TemporaryDirectory(dir=DOSSIER_ML) as sauvegarde:
        dossier_secours = Path(sauvegarde)

        ancien_modele = dossier_secours / "production.pkl"
        ancien_etat = dossier_secours / "etat.json"

        if PRODUCTION.exists():
            shutil.copy2(PRODUCTION, ancien_modele)

        if ETAT.exists():
            shutil.copy2(ETAT, ancien_etat)

        try:
            remplacer_fichier(chemin_modele, PRODUCTION)
            enregistrer_etat(nouvel_etat)

        except Exception:
            if ancien_modele.exists():
                remplacer_fichier(ancien_modele, PRODUCTION)
            else:
                PRODUCTION.unlink(missing_ok=True)

            if ancien_etat.exists():
                remplacer_fichier(ancien_etat, ETAT)
            else:
                ETAT.unlink(missing_ok=True)

            raise

    print("=== ACTIVATION REUSSIE ===")
    print("Version active :", version)
    print("Version precedente :", version_actuelle)
    print("SHA-256 :", sha[:12])
    print("MAE :", mae, "minutes")
    print("Redemarrage du backend necessaire")


def main():
    parser = argparse.ArgumentParser(
        description="Activation d'une version du modele Frenchcab"
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
        KeyError,
        ValueError,
        OSError,
        json.JSONDecodeError
    ) as erreur:
        sys.exit(f"ECHEC : {erreur}")


if __name__ == "__main__":
    main()
