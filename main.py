from datetime import datetime
from pathlib import Path

import duckdb
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel

app = FastAPI()
router = APIRouter()

# Base relationnelle créée par ETL/Load.py (fonction creer_db_relationnelle)
DB_RELATIONNELLE = Path(__file__).resolve().parent / "ETL" / "frenchcab_relationnelle.db"


def ouvrir_db_relationnelle():
    """Ouvre la base en lecture seule (une connexion par requête)."""
    if not DB_RELATIONNELLE.exists():
        raise HTTPException(
            status_code=503,
            detail="Base relationnelle absente : lancez l'ETL (ETL/Load.py).",
        )
    return duckdb.connect(str(DB_RELATIONNELLE), read_only=True)


@app.get("/test")
def get_test():

    return {
        "test": "la route fonctionne"
    }


@app.get("/zones")
def get_zones():
    """Liste des zones de taxi (pour les listes déroulantes du front)."""
    con = ouvrir_db_relationnelle()
    try:
        lignes = con.execute("""
            SELECT LocationID, Borough, Zone, service_zone
            FROM taxi_zones
            WHERE LocationID NOT IN (264, 265)   -- zones 'Unknown' / hors NYC
            ORDER BY Borough, Zone
        """).fetchall()
    finally:
        con.close()

    return [
        {
            "LocationID": ligne[0],
            "Borough": ligne[1],
            "Zone": ligne[2],
            "service_zone": ligne[3],
        }
        for ligne in lignes
    ]


# ------------------------------------------------------------
# POST /predictions/duree
# ------------------------------------------------------------
class DemandeDuree(BaseModel):
    zone_depart: int
    zone_arrivee: int
    date: str    # "YYYY-MM-DD"
    heure: str   # "HH:MM"


def estimer_distance(con, zone_depart, zone_arrivee):
    """Le client ne connait pas la distance : on prend la moyenne historique
    du couple de zones, sinon celle des trajets partant de la zone de depart,
    sinon la moyenne generale."""
    requetes = [
        ("WHERE PULocationID = ? AND DOLocationID = ?", [zone_depart, zone_arrivee]),
        ("WHERE PULocationID = ?", [zone_depart]),
        ("", []),
    ]
    for filtre, params in requetes:
        filtre_distance = "trip_distance > 0 AND trip_distance < 100"
        clause = f"{filtre} AND {filtre_distance}" if filtre else f"WHERE {filtre_distance}"
        resultat = con.execute(
            f"SELECT AVG(trip_distance) FROM yellowtripdata {clause}", params
        ).fetchone()[0]
        if resultat is not None:
            return float(resultat)
    raise HTTPException(status_code=404, detail="Aucune distance estimable.")


@app.post("/predictions/duree")
def predire_duree(demande: DemandeDuree):
    """Estime la duree (minutes) d'une course a partir des zones, de la date et de l'heure."""
    try:
        moment = datetime.strptime(f"{demande.date} {demande.heure}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=422, detail="Date ou heure invalide.")

    con = ouvrir_db_relationnelle()
    try:
        distance = estimer_distance(con, demande.zone_depart, demande.zone_arrivee)
    finally:
        con.close()

    # Import ici : le modele (.pkl) n'est charge qu'a la premiere prediction
    from ML.prediction import predire_temps_trajet

    try:
        duree = predire_temps_trajet(
            trip_distance=distance,
            heure=moment.hour,
            minute=moment.minute,
            mois=moment.month,
            est_weekend=moment.weekday() >= 5,
            nom_jour=moment.strftime("%A"),
            id_localisation_d=demande.zone_depart,
            id_localisation_a=demande.zone_arrivee,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Modele absent : lancez ML/entrainement.py.",
        )

    return {
        "duree_minutes": round(duree, 1),
        "distance_estimee": round(distance, 2),
    }