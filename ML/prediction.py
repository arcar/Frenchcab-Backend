from pathlib import Path

import joblib
import pandas as pd

# ---------------------------------
# CONNEXION BASE ANALYTIQUEs
# ---------------------------------
DOSSIER_SCRIPT = Path(__file__).resolve().parent

DB_PATH = (DOSSIER_SCRIPT.parent/ "ETL"/ "frenchcab.db")

print("Base SQLite :", DB_PATH)

modele = joblib.load("modele_temps_trajet.pkl")
prediction = modele.predict(nouvelles_donnees)
