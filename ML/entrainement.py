import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

from .preparation import preparer_dataframe_ml, charger_donnees_analytiques

#data
df_ml = preparer_dataframe_ml(charger_donnees_analytiques())

cat_cols = ["ID_location_pickup", "ID_location_dropoff", "heure_pickup"]
num_cols = ["trip_distance", "store_and_fwd_flag", "est_weekend_pickup"]
features = cat_cols + num_cols

X = df_ml[features].copy()
y = df_ml["trip_duration_min"]

X["store_and_fwd_flag"] = X["store_and_fwd_flag"].map({"N": 0, "Y": 1})
X["est_weekend_pickup"] = X["est_weekend_pickup"].astype(int)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

#Random Forest
rf_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)

#Linear Regression
lin_model = Pipeline([
    ("prep", ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
        ("num", "passthrough", num_cols),
    ])),
    ("reg", LinearRegression()),
])

#entrainement et predictions 
results = {}
for name, model in [("Linear Regression", lin_model), ("Random Forest", rf_model)]:
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    results[name] = {
        "MAE (min)": mean_absolute_error(y_test, y_pred),
        "MAPE (%)": mean_absolute_percentage_error(y_test, y_pred) * 100,
    }

print(pd.DataFrame(results).T.round(2))