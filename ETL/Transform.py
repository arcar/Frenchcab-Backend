from Extract import parquet_df, pd, year, month

colonnes_date = ["tpep_pickup_datetime", "tpep_dropoff_datetime"]
colonnes_int = ["VendorID", "passenger_count", "RatecodeID", "PULocationID", "DOLocationID", "payment_type"]
colonnes_float = ["fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount", "improvement_surcharge", "total_amount", "congestion_surcharge", "airport_fee", "cbd_congestion_fee"]
na_cols = ["passenger_count", "RatecodeID", "store_and_fwd_flag", "congestion_surcharge", "Airport_fee"]
fill_values = {"passenger_count": 0, "RatecodeID": 99, "store_and_fwd_flag": "N", "congestion_surcharge": 0.0, "Airport_fee": 0.0}

try:
    def convert_types(df):
        df = df.copy()
        df = df.rename(columns={"airport_fee": "Airport_fee"})
        if "cbd_congestion_fee" not in df.columns:
            df["cbd_congestion_fee"] = 0.0

        for c in colonnes_date:
            df[c] = pd.to_datetime(df[c], errors="coerce")

        for c in colonnes_int:
            df[c] = pd.to_numeric(df[c], errors="coerce").round().astype("Int64")

        for c in ["trip_distance"] + [m for m in colonnes_float if m in df.columns]:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")

        df["store_and_fwd_flag"] = df["store_and_fwd_flag"].astype("string")

        return df.drop_duplicates()

    def valeur_defaut_fill_nan(df):
        mask = df[na_cols].isna().sum(axis=1) >= 2
        df.loc[mask, na_cols] = df.loc[mask, na_cols].fillna(value=fill_values)

        return df

    def colonnes_calcules(df):
        df["trip_duration_min"] = (df["tpep_dropoff_datetime"] - df["tpep_pickup_datetime"]).dt.total_seconds() / 60
        df["pickup_hour"] = df["tpep_pickup_datetime"].dt.hour.astype("Int64")
        df["pickup_weekday"] = df["tpep_pickup_datetime"].dt.dayofweek.astype("Int64")

        return df
    

    def filter(df,  year=None, month=None):
        pickup = df["tpep_pickup_datetime"]

        if year and month:
            hors_periode = (pickup.dt.year != year) | (pickup.dt.month != month)
        else:
            hors_periode = pd.Series(False, index=df.index)
        

        rules = {
            "date_invalide": df["tpep_pickup_datetime"].isna() | df["tpep_dropoff_datetime"].isna(),
            "hors_periode": hors_periode,
            "duree_negative_ou_nulle": df["trip_duration_min"] <= 0,
            "duree_sup_5h": df["trip_duration_min"] > 300,
            "distance_nulle_ou_aberrante": (df["trip_distance"] <= 0) | (df["trip_distance"] > 300),
            "montant_negatif_ou_nul": (df["fare_amount"] <= 0) | (df["total_amount"] <= 0),
            "montant_aberrant": df["total_amount"] > 1000,
        }
        rejected = pd.Series(False, index=df.index)
        for mask in rules.values():
            rejected |= mask.fillna(True)

        return df[~rejected].copy()

    def transform(df, year=None, month=None):
        df = convert_types(df)
        df = valeur_defaut_fill_nan(df)
        df = colonnes_calcules(df)
        df = filter(df, year, month)

        return df.reset_index(drop=True)

    df = transform(parquet_df, year, month)
except FileNotFoundError:
    print("File not found:", parquet_df)
except Exception as e:
    print("Error while reading the file:", e)

