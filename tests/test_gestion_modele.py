
import hashlib
import json
from pathlib import Path

import pytest

from ml import publier_modele
from ml import rollback_modele


# ============================================================
# 1. ENVIRONNEMENT DE TEST
# ============================================================

@pytest.fixture
def environnement_modeles(tmp_path, monkeypatch):
    """
    Crée deux faux modèles et un rapport de comparaison.

    Tous les fichiers sont créés dans tmp_path.
    Les vrais modèles Frenchcab ne sont jamais modifiés.
    """

    dossier_ml = tmp_path / "ml"
    dossier_modeles = dossier_ml / "modeles"

    dossier_modeles.mkdir(parents=True)

    modeles = {
        "v1": b"modele fictif version 1",
        "v2": b"modele fictif version 2",
    }

    evaluations = {}

    for version, contenu in modeles.items():
        dossier_version = dossier_modeles / version
        dossier_version.mkdir()

        fichier_modele = dossier_version / "model.pkl"
        fichier_modele.write_bytes(contenu)

        evaluations[version] = {
            "version": version,
            "algorithme": "Random Forest",
            "date_entrainement": "2026-10-20T10:00:00",
            "sha256": hashlib.sha256(contenu).hexdigest()[:12],
            "mae_minutes": 4.5 if version == "v1" else 5.0,
            "conforme": True,
        }

    rapport = {
        "date_evaluation": "2026-10-20T12:00:00",
        "donnees_test": "yellow_tripdata_2026-04.parquet",
        "nb_trajets": 100000,
        "seuil_mae_minutes": 6.0,
        "actuelle": evaluations["v1"],
        "candidate": evaluations["v2"],
    }

    fichier_rapport = dossier_modeles / "resultats_comparaison.json"
    fichier_rapport.write_text(
        json.dumps(rapport, indent=2),
        encoding="utf-8"
    )

    fichier_etat = dossier_modeles / "version_active.json"

    # Les chemins du module sont redirigés vers les fichiers fictifs.
    monkeypatch.setattr(
        publier_modele, "DOSSIER_ML", dossier_ml
    )
    monkeypatch.setattr(
        publier_modele, "MODELS_DIR", dossier_modeles
    )
    monkeypatch.setattr(
        publier_modele, "RESULTATS", fichier_rapport
    )
    monkeypatch.setattr(
        publier_modele, "ETAT", fichier_etat
    )

    # rollback_modele utilise directement publier_modele,
    # donc il récupère automatiquement ces mêmes chemins.

    return {
        "ml": dossier_ml,
        "modeles": dossier_modeles,
        "rapport": fichier_rapport,
        "etat": fichier_etat,
    }


# ============================================================
# 2. FONCTIONS UTILITAIRES
# ============================================================

def lire_json(chemin):
    return json.loads(chemin.read_text(encoding="utf-8"))


def fichier_modele(env, version):
    return env["modeles"] / version / "model.pkl"


# ============================================================
# 3. INITIALISATION DE V1
# ============================================================

def test_initialisation_v1(environnement_modeles):
    env = environnement_modeles

    publier_modele.activer_version(
        "v1",
        initialiser=True
    )

    etat = lire_json(env["etat"])

    assert etat["version"] == "v1"
    assert etat["precedente"] is None
    assert etat["sha256_actif"] == (
        publier_modele.calculer_sha256(
            fichier_modele(env, "v1")
        )
    )


def test_initialisation_sans_copie_modele(environnement_modeles):
    env = environnement_modeles

    publier_modele.activer_version(
        "v1",
        initialiser=True
    )

    # Les deux modèles versionnés existent toujours.
    assert fichier_modele(env, "v1").is_file()
    assert fichier_modele(env, "v2").is_file()

    # Aucun troisième modèle n'a été créé.
    assert not (
        env["ml"] / "modele_temps_trajet.pkl"
    ).exists()

    # Les deux versions restent distinctes.
    assert (
        fichier_modele(env, "v1").read_bytes()
        != fichier_modele(env, "v2").read_bytes()
    )


def test_refus_deuxieme_initialisation(environnement_modeles):
    env = environnement_modeles

    publier_modele.activer_version(
        "v1",
        initialiser=True
    )

    with pytest.raises(
        ValueError,
        match="Initialisation refusee"
    ):
        publier_modele.activer_version(
            "v1",
            initialiser=True
        )

    assert lire_json(env["etat"])["version"] == "v1"


# ============================================================
# 4. ACTIVATION DE V2
# ============================================================

def test_activation_v2(environnement_modeles):
    env = environnement_modeles

    publier_modele.activer_version(
        "v1",
        initialiser=True
    )

    publier_modele.activer_version("v2")

    etat = lire_json(env["etat"])

    assert etat["version"] == "v2"
    assert etat["precedente"] == "v1"

    sha_v2 = publier_modele.calculer_sha256(
        fichier_modele(env, "v2")
    )

    assert etat["sha256_actif"] == sha_v2

    # Aucune version n'a été supprimée.
    assert fichier_modele(env, "v1").is_file()
    assert fichier_modele(env, "v2").is_file()


# ============================================================
# 5. REFUS D'ACTIVATION
# ============================================================

def test_refus_modele_non_conforme(environnement_modeles):
    env = environnement_modeles

    publier_modele.activer_version(
        "v1",
        initialiser=True
    )

    rapport = lire_json(env["rapport"])

    rapport["candidate"]["mae_minutes"] = 7.5
    rapport["candidate"]["conforme"] = False

    env["rapport"].write_text(
        json.dumps(rapport),
        encoding="utf-8"
    )

    with pytest.raises(ValueError, match="refuse"):
        publier_modele.activer_version("v2")

    # V1 doit rester active.
    assert lire_json(env["etat"])["version"] == "v1"


def test_refus_sha256_incorrect(environnement_modeles):
    env = environnement_modeles

    publier_modele.activer_version(
        "v1",
        initialiser=True
    )

    rapport = lire_json(env["rapport"])
    rapport["candidate"]["sha256"] = "000000000000"

    env["rapport"].write_text(
        json.dumps(rapport),
        encoding="utf-8"
    )

    with pytest.raises(
        ValueError,
        match="ne correspond pas"
    ):
        publier_modele.activer_version("v2")

    # V1 doit rester active.
    assert lire_json(env["etat"])["version"] == "v1"


# ============================================================
# 6. ROLLBACK
# ============================================================

def test_rollback_v2_vers_v1(environnement_modeles):
    env = environnement_modeles

    publier_modele.activer_version(
        "v1",
        initialiser=True
    )

    publier_modele.activer_version("v2")

    version_restauree = rollback_modele.rollback()

    etat = lire_json(env["etat"])

    assert version_restauree == "v1"
    assert etat["version"] == "v1"
    assert etat["precedente"] == "v2"

    sha_v1 = publier_modele.calculer_sha256(
        fichier_modele(env, "v1")
    )

    assert etat["sha256_actif"] == sha_v1

    # V2 reste disponible après le rollback.
    assert fichier_modele(env, "v2").is_file()


def test_rollback_sans_version_precedente(environnement_modeles):
    env = environnement_modeles

    publier_modele.activer_version(
        "v1",
        initialiser=True
    )

    with pytest.raises(
        ValueError,
        match="aucune version precedente"
    ):
        rollback_modele.rollback()

    assert lire_json(env["etat"])["version"] == "v1"


def test_rollback_modele_non_conforme(environnement_modeles):
    env = environnement_modeles

    publier_modele.activer_version(
        "v1",
        initialiser=True
    )

    publier_modele.activer_version("v2")

    # On rend V1 non conforme dans le rapport.
    rapport = lire_json(env["rapport"])

    rapport["actuelle"]["mae_minutes"] = 8.0
    rapport["actuelle"]["conforme"] = False

    env["rapport"].write_text(
        json.dumps(rapport),
        encoding="utf-8"
    )

    with pytest.raises(ValueError):
        rollback_modele.rollback()

    # V2 doit rester active.
    assert lire_json(env["etat"])["version"] == "v2"
