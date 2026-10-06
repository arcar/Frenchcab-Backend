import sqlite3

import pandas as pd
import pytest

from ML import preparation


COLONNES_ML = [
    "id_temps",
    "heure",
    "minute",
    "nom_jour",
    "est_weekend",
    "id_localisation_d",
    "id_localisation_a",
    "trip_duration_min",
    "trip_distance",
]


def faux_dataframe():
    return pd.DataFrame({
        "trip_duration_min": [12.5, 30.0, None],
        "trip_distance": [2.1, 8.4, 1.0],
        "id_temps": [1, 2, 3],
        "heure": [8, 17, 23],
        "minute": [15, 30, 45],
        "nom_jour": ["Lundi", "Samedi", "Mardi"],
        "est_weekend": [0, 1, 0],
        "mois": [1, 1, 1],
        "id_localisation_d": [100, 132, 50],
        "id_localisation_a": [200, 161, 60],
    })


def test_preparer_dataframe_ml_garde_les_bonnes_colonnes():
    df_ml = preparation.preparer_dataframe_ml(faux_dataframe())

    assert list(df_ml.columns) == COLONNES_ML
    assert "mois" not in df_ml.columns


def test_preparer_dataframe_ml_supprime_les_lignes_incompletes():
    df_ml = preparation.preparer_dataframe_ml(faux_dataframe())

    assert len(df_ml) == 2
    assert not df_ml.isna().any().any()


def test_preparer_dataframe_ml_ne_modifie_pas_l_original():
    df = faux_dataframe()

    preparation.preparer_dataframe_ml(df)

    assert len(df) == 3
    assert "mois" in df.columns


@pytest.fixture
def fausse_bdd(tmp_path, monkeypatch):
    """Crée une petite base SQLite temporaire avec les tables utilisées."""
    db_path = tmp_path / "test.db"
    connexion = sqlite3.connect(db_path)
    connexion.executescript("""
        CREATE TABLE Dim_Temps (
            id_temps INTEGER PRIMARY KEY,
            heure INTEGER, minute INTEGER, nom_jour TEXT,
            est_weekend INTEGER, mois INTEGER
        );
        CREATE TABLE Faits_Prediction (
            trip_duration_min REAL, trip_distance REAL,
            id_temps_d INTEGER, id_localisation_d INTEGER, id_localisation_a INTEGER
        );
        INSERT INTO Dim_Temps VALUES (1, 8, 15, 'Lundi', 0, 1), (2, 17, 30, 'Samedi', 1, 1);
        INSERT INTO Faits_Prediction VALUES
            (12.5, 2.1, 1, 100, 200),
            (30.0, 8.4, 2, 132, 161),
            (20.0, 5.0, 1, 50, 60);
    """)
    connexion.close()

    monkeypatch.setattr(preparation, "DB_PATH", db_path)
    return db_path


def test_charger_donnees_analytiques_joint_les_tables(fausse_bdd):
    df = preparation.charger_donnees_analytiques()

    assert len(df) == 3
    assert {"trip_duration_min", "heure", "nom_jour"}.issubset(df.columns)
    assert df.loc[1, "nom_jour"] == "Samedi"


def test_charger_donnees_analytiques_respecte_la_limite(fausse_bdd):
    df = preparation.charger_donnees_analytiques(limit=2)

    assert len(df) == 2
