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

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)


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
    "Linear Regression": lin_model,
    "Random Forest": rf_model
}

results = {}


for name, model in models.items():

    print(f"\nEntraînement de {name}...")

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    results[name] = {
        "MAE (min)": mean_absolute_error(y_test, y_pred),

        "MAPE (%)": mean_absolute_percentage_error(y_test, y_pred) * 100
    }


# ============================================================
# RÉSULTATS
# ============================================================

resultats_df = pd.DataFrame(results).T

print("\nRésultats :")
print(resultats_df.round(2))


# ============================================================
# MODÈLE FINAL
# ============================================================

print("\nEntraînement du modèle final...")

modele_final = rf_model

modele_final.fit(X,y)

# ============================================================
# SAUVEGARDE
# ============================================================

joblib.dump(modele_final, MODEL_PATH)

print(f"\nModèle sauvegardé dans : {MODEL_PATH}")