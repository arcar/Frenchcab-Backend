import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

from preparation import preparer_dataframe_ml, charger_donnees_analytiques

#data
df_ml = preparer_dataframe_ml(charger_donnees_analytiques())

cat_cols = ["est_weekend", "nom_jour" ]
num_cols = ["trip_distance","id_localisation_d", "id_localisation_a", "id_temps", "heure", "minute"]
features = cat_cols + num_cols


X = df_ml[features].copy()
y = df_ml["trip_duration_min"]

X["est_weekend"] = X["est_weekend"].astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)


# ------------------------------------------------
# Préprocesseur commun
# ------------------------------------------------

preprocessor = ColumnTransformer([
    ("cat",
        OneHotEncoder(handle_unknown="ignore"),
        cat_cols
    ),
    ("num", "passthrough", num_cols)
])

# ------------------------------------------------
# Pipeline Régression Linéaire
# ------------------------------------------------

# Linear Regression
lin_model = Pipeline([
    ("prep", preprocessor),
    ("reg", LinearRegression()),
])

# ------------------------------------------------
# Pipeline Random Forest
# ------------------------------------------------

rf_model = Pipeline([
    ("prep",preprocessor),
    ( "reg",
        RandomForestRegressor(
            n_estimators=100,
            random_state=42,
            n_jobs=-1
        )
    )
])


#entrainement et predictions 
results = {}
models = [("Linear Regression", lin_model), ("Random Forest", rf_model) ]
for name, model in models:
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    results[name] = {
        "MAE (min)": mean_absolute_error(y_test, y_pred),
        "MAEP (%)": mean_absolute_percentage_error(y_test, y_pred) * 100,
    }

print(pd.DataFrame(results).T.round(2))

