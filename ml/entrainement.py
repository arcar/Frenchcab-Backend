from pathlib import Path
import json
from datetime import datetime
import joblib
import pandas as pd
import os

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (mean_absolute_error, mean_absolute_percentage_error)
from sklearn.base import clone

from ml.preparation import preparer_dataframe_ml, charger_donnees_analytiques

# ============================================================
# CONFIGURATION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent
DOSSIER_MODELES = Path(os.getenv("MODELS_DIR", str(DOSSIER_SCRIPT / "modeles")))

LIMIT_DATA = 1000_000

def prochaine_version(dossier):
    dossier.mkdir(parents=True, exist_ok=True)
    numeros = [
        int(d.name[1:])
        for d in dossier.iterdir()
        if d.is_dir() and d.name.startswith("v") and d.name[1:].isdigit()
    ]
    return f"v{max(numeros, default=0) + 1}"

# ============================================================
# CHARGEMENT DES DONNÉES
# ============================================================

print(f"Chargement de {LIMIT_DATA} lignes...")

df = charger_donnees_analytiques(LIMIT_DATA)

df_ml = preparer_dataframe_ml(df)


# ============================================================
# FEATURES
# ============================================================

cat_cols = [
    "nom_jour",
    "id_localisation_d",
    "id_localisation_a"
]

num_cols = [
    "trip_distance",
    "heure",
    "minute",
    "est_weekend"
]

features = cat_cols + num_cols


# ============================================================
# X / y
# ============================================================

X = df_ml[features].copy()

y = df_ml["trip_duration_min"]

X["est_weekend"] = (X["est_weekend"].astype(int))


# ============================================================
# TRAIN / TEST
# ============================================================
# 80
X_train, X_teste, y_train, y_teste = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)

X_val, X_test, y_val, y_test = train_test_split(
    X_teste,
    y_teste,
    test_size=0.50,
    random_state=42
)

print(f"Train : {len(X_train)} lignes")
print(f"Validation : {len(X_val)} lignes")
print(f"Test : {len(X_test)} lignes")


# ============================================================
# PRÉPROCESSEUR
# ============================================================

preprocessor = ColumnTransformer([
    ("cat",OneHotEncoder(handle_unknown="ignore"),cat_cols),
    ("num", "passthrough", num_cols)
])



# ============================================================
# ÉVALUATION
# ============================================================

models = {
    "Linear Regression": Pipeline([
        ("prep", clone(preprocessor)),
        ("reg", LinearRegression())
    ]),

    "Random Forest": Pipeline([
        ("prep", clone(preprocessor)),
        ("reg", RandomForestRegressor(
            n_estimators=30,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        ))
    ])
}


# ============================================================
# CALCUL DES ERREURS
# ============================================================

def calculer_metriques(y_true, y_pred):
    erreurs = abs(y_true.to_numpy() - y_pred)

    return {
        "MAE (minutes)": mean_absolute_error(y_true, y_pred),
        "Erreur min (minutes)": erreurs.min(),
        "Erreur max (minutes)": erreurs.max()
    }



results = {}

for name, model in models.items():
    print(f"\nEntraînement de {name}...")

    model.fit(X_train, y_train)

    train_pred = model.predict(X_train)
    val_pred = model.predict(X_val)

    results[name] = {
        "MAE train (minutes)": mean_absolute_error(
            y_train, train_pred
        ),
        **calculer_metriques(y_val, val_pred)
    }


# ============================================================
# RÉSULTATS DE VALIDATION — EN DEHORS DE LA BOUCLE
# ============================================================

resultats_df = pd.DataFrame(results).T

print("\nRésultats sur la validation :")
print(resultats_df.round(2))


# ============================================================
# CHOIX DU MODÈLE
# ============================================================

meilleur_nom = resultats_df["MAE (minutes)"].idxmin()

print(f"\nModèle choisi : {meilleur_nom}")



# ============================================================
# RECUPERATION DU MEILLEUR MODELE DEJA ENTRAINE
# ============================================================

print("\nRécupération du meilleur modèle...")

modele_final = models[meilleur_nom]

# ============================================================
# ÉVALUATION FINALE SUR LE TEST
# ============================================================

y_pred = modele_final.predict(X_test)

resultats_test = {
    **calculer_metriques(y_test, y_pred),
    "MAPE (%)": mean_absolute_percentage_error(
        y_test, y_pred
    ) * 100
}

print("\nRésultats sur le test :")
print(pd.Series(resultats_test).round(2))


# ============================================================
# SAUVEGARDE DE LA VERSION
# ============================================================

version = prochaine_version(DOSSIER_MODELES)
dossier_version = DOSSIER_MODELES / version
dossier_version.mkdir()

# 1. Le modèle
joblib.dump(modele_final, dossier_version / "model.pkl")

# 2. Les résultats de validation des deux modèles comparés
resultats_df.round(4).to_csv(dossier_version / "evaluation_validation.csv")


# 3. Les métadonnées + résultats sur le test
metadata = {
    "version": version,
    "date_entrainement": datetime.now().isoformat(timespec="seconds"),
    "algorithme": meilleur_nom,
    "hyperparametres": modele_final.named_steps["reg"].get_params(),
    "features": features,
    "nb_lignes": {
    "train": len(X_train),
    "validation": len(X_val),
    "test": len(X_test),
    },
    "metriques_test": {k: round(float(v), 4) for k, v in resultats_test.items()},
}

with open(dossier_version / "metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

print(f"\nVersion {version} sauvegardée dans : {dossier_version}")