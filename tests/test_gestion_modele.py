
import hashlib
import json
import sys
from pathlib import Path

import pytest


# Permet d'importer le module ml/publier_modele.py
DOSSIER_ML = Path(__file__).resolve().parents[1] / "ml"
sys.path.insert(0, str(DOSSIER_ML))

import publier_modele


def test_activation_v2(tmp_path, monkeypatch):

    # 1. Créer des dossiers temporaires
    dossier_ml = tmp_path / "ml"
    dossier_modeles = dossier_ml / "modeles"

    v1 = dossier_modeles / "v1"
    v2 = dossier_modeles / "v2"

    v1.mkdir(parents=True)
    v2.mkdir(parents=True)

    # 2. Créer deux faux modèles distincts
    (v1 / "model.pkl").write_bytes(b"modele-v1")
    (v2 / "model.pkl").write_bytes(b"modele-v2")

    # 3. Calculer leurs empreintes
    sha_v1 = hashlib.sha256(b"modele-v1").hexdigest()
    sha_v2 = hashlib.sha256(b"modele-v2").hexdigest()

    # 4. Simuler V1 actuellement en production
    production = dossier_ml / "modele_temps_trajet.pkl"
    production.write_bytes(b"modele-v1")

    # 5. Créer le rapport d'évaluation
    rapport = {
        "donnees_test": "yellow_tripdata_2026-04.parquet",
        "seuil_mae_minutes": 6.0,
        "actuelle": {
            "version": "v1",
            "sha256": sha_v1[:12],
            "mae_minutes": 4.5
        },
        "candidate": {
            "version": "v2",
            "sha256": sha_v2[:12],
            "mae_minutes": 5.2
        }
    }

    resultat = dossier_modeles / "resultats_comparaison.json"
    resultat.write_text(
        json.dumps(rapport),
        encoding="utf-8"
    )

    # 6. Rediriger les chemins du script vers tmp_path
    monkeypatch.setattr(publier_modele, "DOSSIER_ML", dossier_ml)
    monkeypatch.setattr(publier_modele, "MODELS_DIR", dossier_modeles)
    monkeypatch.setattr(publier_modele, "PRODUCTION", production)
    monkeypatch.setattr(publier_modele, "RESULTATS", resultat)
    monkeypatch.setattr(
        publier_modele,
        "ETAT",
        dossier_modeles / "version_active.json"
    )

    # 7. Activer V2
    publier_modele.activer_version("v2")

    # 8. Vérifier que V2 est désormais en production
    assert production.read_bytes() == b"modele-v2"

    # 9. Vérifier le fichier d'état
    etat = json.loads(
        (dossier_modeles / "version_active.json").read_text(
            encoding="utf-8"
        )
    )

    assert etat["version"] == "v2"
    assert etat["precedente"] == "v1"
    assert etat["sha256_actif"] == sha_v2

    # 10. Vérifier que V1 est toujours conservée
    assert (v1 / "model.pkl").read_bytes() == b"modele-v1"


def test_refus_modele_non_conforme(tmp_path, monkeypatch):

    # Créer les dossiers de test
    dossier_ml = tmp_path / "ml"
    dossier_modeles = dossier_ml / "modeles"

    v1 = dossier_modeles / "v1"
    v2 = dossier_modeles / "v2"

    v1.mkdir(parents=True)
    v2.mkdir(parents=True)

    # Créer deux faux modèles
    (v1 / "model.pkl").write_bytes(b"modele-v1")
    (v2 / "model.pkl").write_bytes(b"modele-v2")

    # V1 est actuellement en production
    production = dossier_ml / "modele_temps_trajet.pkl"
    production.write_bytes(b"modele-v1")

    # Empreintes des deux modèles
    sha_v1 = hashlib.sha256(b"modele-v1").hexdigest()
    sha_v2 = hashlib.sha256(b"modele-v2").hexdigest()

    # V2 dépasse le seuil autorisé
    rapport = {
        "donnees_test": "yellow_tripdata_2026-04.parquet",
        "seuil_mae_minutes": 6.0,
        "actuelle": {
            "version": "v1",
            "sha256": sha_v1[:12],
            "mae_minutes": 4.5
        },
        "candidate": {
            "version": "v2",
            "sha256": sha_v2[:12],
            "mae_minutes": 7.5
        }
    }

    resultat = dossier_modeles / "resultats_comparaison.json"
    resultat.write_text(
        json.dumps(rapport),
        encoding="utf-8"
    )

    # Rediriger les chemins vers les fichiers temporaires
    monkeypatch.setattr(publier_modele, "DOSSIER_ML", dossier_ml)
    monkeypatch.setattr(publier_modele, "MODELS_DIR", dossier_modeles)
    monkeypatch.setattr(publier_modele, "PRODUCTION", production)
    monkeypatch.setattr(publier_modele, "RESULTATS", resultat)
    monkeypatch.setattr(
        publier_modele,
        "ETAT",
        dossier_modeles / "version_active.json"
    )

    # Vérifier que l'activation est refusée
    with pytest.raises(ValueError, match="MAE"):
        publier_modele.activer_version("v2")

    # Vérifier que V1 reste en production
    assert production.read_bytes() == b"modele-v1"

    # Aucun changement de version enregistré
    assert not (dossier_modeles / "version_active.json").exists()


def test_refus_sha256_incorrect(tmp_path, monkeypatch):

    # 1. Préparer les deux versions
    dossier_ml = tmp_path / "ml"
    dossier_modeles = dossier_ml / "modeles"

    v1 = dossier_modeles / "v1"
    v2 = dossier_modeles / "v2"

    v1.mkdir(parents=True)
    v2.mkdir(parents=True)

    (v1 / "model.pkl").write_bytes(b"modele-v1")
    (v2 / "model.pkl").write_bytes(b"modele-v2-modifie")

    # 2. V1 est actuellement en production
    production = dossier_ml / "modele_temps_trajet.pkl"
    production.write_bytes(b"modele-v1")

    sha_v1 = hashlib.sha256(b"modele-v1").hexdigest()

    # Empreinte correspondant à l'ancienne V2,
    # et non au fichier modifié.
    sha_v2_original = hashlib.sha256(b"modele-v2").hexdigest()

    # 3. Rapport de comparaison
    rapport = {
        "donnees_test": "yellow_tripdata_2026-04.parquet",
        "seuil_mae_minutes": 6.0,
        "actuelle": {
            "version": "v1",
            "sha256": sha_v1[:12],
            "mae_minutes": 4.5
        },
        "candidate": {
            "version": "v2",
            "sha256": sha_v2_original[:12],
            "mae_minutes": 5.2
        }
    }

    resultat = dossier_modeles / "resultats_comparaison.json"
    resultat.write_text(
        json.dumps(rapport),
        encoding="utf-8"
    )

    # 4. Utiliser uniquement les fichiers temporaires
    monkeypatch.setattr(publier_modele, "DOSSIER_ML", dossier_ml)
    monkeypatch.setattr(publier_modele, "MODELS_DIR", dossier_modeles)
    monkeypatch.setattr(publier_modele, "PRODUCTION", production)
    monkeypatch.setattr(publier_modele, "RESULTATS", resultat)
    monkeypatch.setattr(
        publier_modele,
        "ETAT",
        dossier_modeles / "version_active.json"
    )

    # 5. L'activation doit être refusée
    with pytest.raises(ValueError, match="correspond pas"):
        publier_modele.activer_version("v2")

    # 6. Le modèle de production reste inchangé
    assert production.read_bytes() == b"modele-v1"

    # Aucun état d'activation créé
    assert not (dossier_modeles / "version_active.json").exists()


def test_rollback_v2_vers_v1(tmp_path, monkeypatch):

    import rollback_modele

    # 1. Créer deux versions fictives
    dossier_ml = tmp_path / "ml"
    dossier_modeles = dossier_ml / "modeles"

    v1 = dossier_modeles / "v1"
    v2 = dossier_modeles / "v2"

    v1.mkdir(parents=True)
    v2.mkdir(parents=True)

    (v1 / "model.pkl").write_bytes(b"modele-v1")
    (v2 / "model.pkl").write_bytes(b"modele-v2")

    sha_v1 = hashlib.sha256(b"modele-v1").hexdigest()
    sha_v2 = hashlib.sha256(b"modele-v2").hexdigest()

    # 2. Simuler V2 actuellement en production
    production = dossier_ml / "modele_temps_trajet.pkl"
    production.write_bytes(b"modele-v2")

    # 3. Enregistrer V2 comme active et V1 comme précédente
    etat_path = dossier_modeles / "version_active.json"

    etat_path.write_text(
        json.dumps({
            "version": "v2",
            "precedente": "v1",
            "sha256_actif": sha_v2
        }),
        encoding="utf-8"
    )

    # 4. Créer un rapport avec les deux évaluations
    rapport_path = dossier_modeles / "resultats_comparaison.json"

    rapport_path.write_text(
        json.dumps({
            "donnees_test": "yellow_tripdata_2026-04.parquet",
            "seuil_mae_minutes": 6.0,
            "actuelle": {
                "version": "v1",
                "sha256": sha_v1[:12],
                "mae_minutes": 4.5
            },
            "candidate": {
                "version": "v2",
                "sha256": sha_v2[:12],
                "mae_minutes": 5.2
            }
        }),
        encoding="utf-8"
    )

    # 5. Rediriger les chemins de publier_modele.py
    monkeypatch.setattr(publier_modele, "DOSSIER_ML", dossier_ml)
    monkeypatch.setattr(publier_modele, "MODELS_DIR", dossier_modeles)
    monkeypatch.setattr(publier_modele, "PRODUCTION", production)
    monkeypatch.setattr(publier_modele, "RESULTATS", rapport_path)
    monkeypatch.setattr(publier_modele, "ETAT", etat_path)

    # Rediriger aussi les chemins de rollback_modele.py
    monkeypatch.setattr(rollback_modele, "DOSSIER_ML", dossier_ml)
    monkeypatch.setattr(rollback_modele, "PRODUCTION", production)
    monkeypatch.setattr(rollback_modele, "RESULTATS", rapport_path)
    monkeypatch.setattr(rollback_modele, "ETAT", etat_path)

    # 6. Exécuter le rollback
    rollback_modele.rollback()

    # 7. Vérifier que V1 est restaurée
    assert production.read_bytes() == b"modele-v1"

    nouvel_etat = json.loads(
        etat_path.read_text(encoding="utf-8")
    )

    assert nouvel_etat["version"] == "v1"
    assert nouvel_etat["precedente"] == "v2"
    assert nouvel_etat["sha256_actif"] == sha_v1

    # 8. Vérifier que V2 est toujours disponible
    assert (v2 / "model.pkl").read_bytes() == b"modele-v2"


def test_rollback_sans_version_precedente(tmp_path, monkeypatch):

    import rollback_modele

    # 1. Préparer les dossiers temporaires
    dossier_ml = tmp_path / "ml"
    dossier_modeles = dossier_ml / "modeles"
    dossier_modeles.mkdir(parents=True)

    # 2. Simuler V2 en production
    production = dossier_ml / "modele_temps_trajet.pkl"
    production.write_bytes(b"modele-v2")

    sha_v2 = hashlib.sha256(b"modele-v2").hexdigest()

    # 3. Enregistrer un état sans version précédente
    etat_path = dossier_modeles / "version_active.json"

    etat_path.write_text(
        json.dumps({
            "version": "v2",
            "precedente": None,
            "sha256_actif": sha_v2
        }),
        encoding="utf-8"
    )

    # 4. Rediriger les chemins du rollback
    monkeypatch.setattr(rollback_modele, "ETAT", etat_path)
    monkeypatch.setattr(rollback_modele, "PRODUCTION", production)

    # 5. Vérifier que le rollback est refusé
    with pytest.raises(ValueError, match="Aucune version precedente"):
        rollback_modele.rollback()

    # 6. Vérifier que V2 reste en production
    assert production.read_bytes() == b"modele-v2"


def test_rollback_modele_non_conforme(tmp_path, monkeypatch):

    import rollback_modele

    # 1. Créer les deux modèles fictifs
    dossier_ml = tmp_path / "ml"
    dossier_modeles = dossier_ml / "modeles"

    v1 = dossier_modeles / "v1"
    v2 = dossier_modeles / "v2"

    v1.mkdir(parents=True)
    v2.mkdir(parents=True)

    (v1 / "model.pkl").write_bytes(b"modele-v1")
    (v2 / "model.pkl").write_bytes(b"modele-v2")

    sha_v1 = hashlib.sha256(b"modele-v1").hexdigest()
    sha_v2 = hashlib.sha256(b"modele-v2").hexdigest()

    # 2. V2 est actuellement en production
    production = dossier_ml / "modele_temps_trajet.pkl"
    production.write_bytes(b"modele-v2")

    etat_path = dossier_modeles / "version_active.json"

    etat_initial = {
        "version": "v2",
        "precedente": "v1",
        "sha256_actif": sha_v2
    }

    etat_path.write_text(
        json.dumps(etat_initial),
        encoding="utf-8"
    )

    # 3. V1 ne respecte pas le seuil de qualité
    rapport_path = dossier_modeles / "resultats_comparaison.json"

    rapport_path.write_text(
        json.dumps({
            "donnees_test": "yellow_tripdata_2026-04.parquet",
            "seuil_mae_minutes": 6.0,
            "actuelle": {
                "version": "v1",
                "sha256": sha_v1[:12],
                "mae_minutes": 8.0
            },
            "candidate": {
                "version": "v2",
                "sha256": sha_v2[:12],
                "mae_minutes": 5.2
            }
        }),
        encoding="utf-8"
    )

    # 4. Rediriger les chemins des deux modules
    for module in (publier_modele, rollback_modele):
        monkeypatch.setattr(module, "DOSSIER_ML", dossier_ml)
        monkeypatch.setattr(module, "PRODUCTION", production)
        monkeypatch.setattr(module, "RESULTATS", rapport_path)
        monkeypatch.setattr(module, "ETAT", etat_path)

    monkeypatch.setattr(
        publier_modele, "MODELS_DIR", dossier_modeles
    )

    # 5. Le rollback doit être refusé
    with pytest.raises(ValueError, match="MAE"):
        rollback_modele.rollback()

    # 6. V2 reste active
    assert production.read_bytes() == b"modele-v2"

    etat_final = json.loads(
        etat_path.read_text(encoding="utf-8")
    )

    assert etat_final == etat_initial
