import os
import re 
import pandas as pd

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dossier_data = os.path.join(root, "raw_data")

fichier_data_parquet = os.path.join(dossier_data, "yellow_tripdata_2026-01.parquet")
nom = os.path.splitext(os.path.basename(fichier_data_parquet))[0]
match = re.search(r"(\d{4})-(\d{2})", nom)
date_suffix = match.group(0)
year, month = int(match.group(1)), int(match.group(2))

try:
    parquet_df = pd.read_parquet(fichier_data_parquet)
    print("File loaded:", parquet_df.shape)
except FileNotFoundError:
    print("File not found:", fichier_data_parquet)
except Exception as e:
    print("Error while reading the file:", e)