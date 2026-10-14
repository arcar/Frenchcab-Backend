import argparse
import json
import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error


# ============================================================
# CONFIGURATION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent

MODEL_PATH_1 = Path(
    os.getenv(
        "MODEL_PATH_1",
        str(DOSSIER_SCRIPT / "modele_temps_trajet.pkl")
    )
)

MODEL_PATH_2 = Path(
    os.getenv(
        "MODEL_PATH_2",
        str(DOSSIER_SCRIPT / "modele_temps_trajet_lin_model.pkl")
    )
)

COLONNE_DEPART = "tpep_pickup_datetime"
COLONNE_ARRIVEE = "tpep_dropoff_datetime"
COLONNE_DISTANCE = "trip_distance"
COLONNE_LOCALISATION_D = "PULocationID"
COLONNE_LOCALISATION_A = "DOLocationID"


# ============================================================
# PRÉPARATION DES DONNÉES
# ============================================================

def preparer_donnees(fichier_csv):
    df = pd.read_csv(fichier_csv, low_memory=False)

    colonnes_requises = [
        COLONNE_DEPART,
        COLONNE_ARRIVEE,
        COLONNE_DISTANCE,
        COLONNE_LOCALISATION_D,
        COLONNE_LOCALISATION_A,
    ]

    colonnes_manquantes = [
        col for col in colonnes_requises
        if col not in df.columns
    ]

    if colonnes_manquantes:
        raise ValueError(
            f"Colonnes manquantes dans le CSV : {colonnes_manquantes}"
        )

    # Conversion des types
    df[COLONNE_DEPART] = pd.to_datetime(
        df[COLONNE_DEPART], errors="coerce"
    )
    df[COLONNE_ARRIVEE] = pd.to_datetime(
        df[COLONNE_ARRIVEE], errors="coerce"
    )

    df[COLONNE_DISTANCE] = pd.to_numeric(
        df[COLONNE_DISTANCE], errors="coerce"
    )

    df[COLONNE_LOCALISATION_D] = pd.to_numeric(
        df[COLONNE_LOCALISATION_D], errors="coerce"
    )
    df[COLONNE_LOCALISATION_A] = pd.to_numeric(
        df[COLONNE_LOCALISATION_A], errors="coerce"
    )

    # Durée réelle en minutes
    df["duree_reelle_minutes"] = (
        df[COLONNE_ARRIVEE] - df[COLONNE_DEPART]
    ).dt.total_seconds() / 60

    # Suppression des données invalides
    df = df.dropna(
        subset=[
            COLONNE_DEPART,
            COLONNE_ARRIVEE,
            COLONNE_DISTANCE,
            COLONNE_LOCALISATION_D,
            COLONNE_LOCALISATION_A,
            "duree_reelle_minutes",
        ]
    ).copy()

    df = df[
        (df["duree_reelle_minutes"] > 0)
        & (df["duree_reelle_minutes"] <= 300)
        & (df[COLONNE_DISTANCE] > 0)
        & (df[COLONNE_DISTANCE] <= 300)
    ].copy()

    if df.empty:
        raise ValueError("Aucune course valide dans le jeu de test.")

    date_depart = df[COLONNE_DEPART]

   
    X_test = pd.DataFrame({
        "nom_jour": date_depart.dt.day_name(),
        "id_localisation_d": df[COLONNE_LOCALISATION_D],
        "id_localisation_a": df[COLONNE_LOCALISATION_A],
        "trip_distance": df[COLONNE_DISTANCE],
        "heure": date_depart.dt.hour,
        "minute": date_depart.dt.minute,
        "est_weekend": (
            date_depart.dt.dayofweek >= 5
        ).astype(int),
    }, index=df.index)

    y_reel = df["duree_reelle_minutes"]

    return df, X_test, y_reel


# ============================================================
# ÉVALUATION D'UN MODÈLE
# ============================================================

def evaluer_un_modele(nom_modele, chemin_modele, X_test, y_reel):

    if not chemin_modele.exists():
        raise FileNotFoundError(
            f"Modèle introuvable : {chemin_modele}"
        )

    # Charger le modèle existant
    modele = joblib.load(chemin_modele)

    print(f"\n===== {nom_modele} =====")
    print(f"Fichier : {chemin_modele}")
    print(f"Nombre de courses : {len(X_test)}")

    # Vérification du pipeline et du préprocesseur
    if not hasattr(modele, "named_steps"):
        raise TypeError(
            f"{nom_modele} n'est pas un pipeline scikit-learn attendu."
        )

    if "prep" not in modele.named_steps or "reg" not in modele.named_steps:
        raise ValueError(
            f"{nom_modele} doit contenir les étapes 'prep' et 'reg'."
        )

    prep = modele.named_steps["prep"]
    reg = modele.named_steps["reg"]

    # Vérifier les colonnes attendues par le préprocesseur
    colonnes_attendues = list(prep.feature_names_in_)
    colonnes_manquantes = [
        col for col in colonnes_attendues
        if col not in X_test.columns
    ]

    if colonnes_manquantes:
        raise ValueError(
            f"{nom_modele} attend des colonnes absentes : "
            f"{colonnes_manquantes}"
        )

    # Transmettre au préprocesseur uniquement ses colonnes attendues,
    # dans le même ordre que pendant l'entraînement.
    X_entree = X_test[colonnes_attendues].copy()

    # Transformation des variables
    X_transforme = prep.transform(X_entree)

    nombre_variables_produites = X_transforme.shape[1]
    nombre_variables_attendues = reg.n_features_in_

    print("Colonnes d'entrée :", colonnes_attendues)
    print("Variables après prétraitement :", nombre_variables_produites)
    print("Variables attendues par la régression :", nombre_variables_attendues)

    # Ne pas masquer une incompatibilité du modèle sauvegardé
    if nombre_variables_produites != nombre_variables_attendues:
        raise ValueError(
            f"Incompatibilité dans {nom_modele} : le préprocesseur produit "
            f"{nombre_variables_produites} variables, mais la régression "
            f"en attend {nombre_variables_attendues}. "
            "Le modèle sauvegardé est incohérent : "
            "et sa sauvegarde."
        )

    # Prédictions avec le modèle déjà entraîné
    predictions = reg.predict(X_transforme)

    # Erreurs absolues en minutes
    erreurs_absolues = abs(
        y_reel.to_numpy() - predictions
    )

    mae = mean_absolute_error(y_reel, predictions)

    resultat = {
        "nom_modele": nom_modele,
        "fichier_modele": chemin_modele.name,
        "mae_minutes": round(float(mae), 3),
        "nombre_courses_evaluees": int(len(y_reel)),
        "predictions": [
            {
                "duree_reelle_minutes": round(float(reel), 2),
                "duree_predite_minutes": round(float(predite), 2),
                "erreur_absolue_minutes": round(float(erreur), 2),
            }
            for reel, predite, erreur in zip(
                y_reel.to_numpy(),
                predictions,
                erreurs_absolues,
            )
        ],
    }

    print(f"MAE : {mae:.3f} minutes")

    return resultat


# ============================================================
# ÉVALUATION DES DEUX MODÈLES
# ============================================================

def evaluer_modeles(fichier_csv, fichier_json):

    df, X_test, y_reel = preparer_donnees(fichier_csv)

    resultats = []

    modeles = [
        ("Modèle 1 - Random Forest", MODEL_PATH_1),
        ("Modèle 2 - Régression linéaire", MODEL_PATH_2),
    ]

    # On tente les deux évaluations même si l'un des modèles échoue.
    erreurs_modeles = []

    for nom_modele, chemin_modele in modeles:
        try:
            resultat = evaluer_un_modele(
                nom_modele,
                chemin_modele,
                X_test,
                y_reel,
            )
            resultats.append(resultat)

        except Exception as erreur:
            print(f"\nERREUR pour {nom_modele} : {erreur}")
            erreurs_modeles.append({
                "nom_modele": nom_modele,
                "erreur": str(erreur),
            })

    if not resultats:
        raise RuntimeError(
            "Aucun modèle n'a pu être évalué. "
            "Consulte les messages d'erreur ci-dessus."
        )

    # Classement par MAE croissante
    resultats_tries = sorted(
        resultats,
        key=lambda resultat: resultat["mae_minutes"]
    )

    meilleur_modele = resultats_tries[0]

    rapport = {
        "jeu_de_test": str(fichier_csv),
        "nombre_courses_evaluees": int(len(df)),
        "metrique": "MAE",
        "unite": "minutes",
        "comparaison": [
            {
                "nom_modele": resultat["nom_modele"],
                "fichier_modele": resultat["fichier_modele"],
                "mae_minutes": resultat["mae_minutes"],
                "nombre_courses_evaluees": (
                    resultat["nombre_courses_evaluees"]
                ),
            }
            for resultat in resultats_tries
        ],
        "meilleur_modele": meilleur_modele["nom_modele"],
        "resultats_detaillees": resultats,
        "erreurs_modeles": erreurs_modeles,
    }

    # Export JSON
    fichier_json = Path(fichier_json)
    fichier_json.parent.mkdir(parents=True, exist_ok=True)

    with open(fichier_json, "w", encoding="utf-8") as fichier:
        json.dump(
            rapport,
            fichier,
            indent=4,
            ensure_ascii=False,
        )

    print("\n===== COMPARAISON DES MODÈLES =====")

    for resultat in resultats_tries:
        print(
            f"{resultat['nom_modele']} : "
            f"MAE = {resultat['mae_minutes']:.3f} minutes"
        )

    print(f"\nMeilleur modèle évalué : {meilleur_modele['nom_modele']}")
    print(f"Rapport JSON : {fichier_json.resolve()}")

    if erreurs_modeles:
        print(
            "\nAttention : certains modèles n'ont pas pu être évalués. "
            "Consulte le JSON et les messages d'erreur."
        )


# ============================================================
# EXÉCUTION
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Comparer deux modèles de durée de trajet TLC"
    )

    parser.add_argument(
        "--data",
        required=True,
        help="Chemin du CSV TLC de test",
    )

    parser.add_argument(
        "--output",
        default="resultats_evaluation.json",
        help="Chemin du rapport JSON",
    )

    args = parser.parse_args()

    evaluer_modeles(
        fichier_csv=args.data,
        fichier_json=args.output,
    )
