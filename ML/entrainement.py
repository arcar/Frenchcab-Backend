from pathlib import Path

import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (mean_absolute_error, mean_absolute_percentage_error)
from sklearn.base import clone

from preparation import (preparer_dataframe_ml, charger_donnees_analytiques)

# ============================================================
# CONFIGURATION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent
MODEL_PATH = DOSSIER_SCRIPT / "modele_temps_trajet.pkl"

LIMIT_DATA = 1000_000


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
# RÉGRESSION LINÉAIRE
# ============================================================

lin_model = Pipeline([
    ("prep", preprocessor),
    ("reg", LinearRegression())
])

# ============================================================
# RANDOM FOREST
# ============================================================

rf_model = Pipeline([
    ("prep", preprocessor),
    ("reg",
        RandomForestRegressor(
            n_estimators=50,
            max_depth=15,
            random_state=42,
            n_jobs=-1
        )
    )
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
            n_estimators=50,
            max_depth=15,
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
# ENTRAÎNEMENT FINAL SUR TRAIN + VALIDATION
# ============================================================

print("\nEntraînement du modèle final...")

X_train_val = pd.concat([X_train, X_val])
y_train_val = pd.concat([y_train, y_val])

modele_final = clone(models[meilleur_nom])
modele_final.fit(X_train_val, y_train_val)


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


# SAUVEGARDE
joblib.dump(modele_final, MODEL_PATH)

print(f"\nModèle sauvegardé dans : {MODEL_PATH}")