import os
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import duckdb
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel

app = FastAPI()
router = APIRouter()

# Base relationnelle créée par ETL/Load.py (fonction creer_db_relationnelle)
# DB_RELATIONNELLE permet de la placer ailleurs (ex : volume Docker sur la VM)
DB_RELATIONNELLE = Path(os.getenv(
    "DB_RELATIONNELLE",
    Path(__file__).resolve().parent / "ETL" / "frenchcab_relationnelle.db",
))

# DuckDB n'accepte pas deux connexions de configurations differentes
# (lecture seule / ecriture) en meme temps dans un processus : on serialise.
VERROU_DB = threading.Lock()


@contextmanager
def ouvrir_db_relationnelle(ecriture=False):
    """Ouvre la base (une connexion par requete) et la ferme a la fin."""
    if not DB_RELATIONNELLE.exists():
        raise HTTPException(
            status_code=503,
            detail="Base relationnelle absente : lancez l'ETL (ETL/Load.py).",
        )
    with VERROU_DB:
        con = duckdb.connect(str(DB_RELATIONNELLE), read_only=not ecriture)
        try:
            yield con
        finally:
            con.close()


@app.get("/test")
def get_test():

    return {
        "test": "la route fonctionne"
    }


@app.get("/zones")
def get_zones():
    """Liste des zones de taxi (pour les listes déroulantes du front)."""
    with ouvrir_db_relationnelle() as con:
        lignes = con.execute("""
            SELECT LocationID, Borough, Zone, service_zone
            FROM taxi_zones
            WHERE LocationID NOT IN (264, 265)   -- zones 'Unknown' / hors NYC
            ORDER BY Borough, Zone
        """).fetchall()

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


def calculer_duree(demande):
    """Calcule (duree_minutes, distance, moment) pour une demande."""
    try:
        moment = datetime.strptime(f"{demande.date} {demande.heure}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=422, detail="Date ou heure invalide.")

    with ouvrir_db_relationnelle() as con:
        distance = estimer_distance(con, demande.zone_depart, demande.zone_arrivee)

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
    return round(duree, 1), round(distance, 2), moment


@app.post("/predictions/duree")
def predire_duree(demande: DemandeDuree):
    """Estime la duree (minutes) d'une course a partir des zones, de la date et de l'heure."""
    duree, distance, _ = calculer_duree(demande)
    return {"duree_minutes": duree, "distance_estimee": distance}


# ------------------------------------------------------------
# Courses planifiees (table reservation)
# ------------------------------------------------------------
class DemandeCourse(DemandeDuree):
    passagers: Optional[int] = 1


def preparer_table_reservation(con):
    """Ajoute les colonnes utiles a la planification si elles manquent."""
    con.execute("ALTER TABLE reservation ADD COLUMN IF NOT EXISTS duree_estimee DOUBLE")
    con.execute("ALTER TABLE reservation ADD COLUMN IF NOT EXISTS statut VARCHAR DEFAULT 'planifiee'")


def zone_existe(con, zone_id):
    return con.execute(
        "SELECT 1 FROM taxi_zones WHERE LocationID = ?", [zone_id]
    ).fetchone() is not None


@app.post("/courses", status_code=201)
def creer_course(demande: DemandeCourse):
    """Enregistre une course planifiee. La duree est recalculee cote serveur."""
    if demande.zone_depart == demande.zone_arrivee:
        raise HTTPException(status_code=422, detail="Départ et arrivée identiques.")
    if demande.passagers is None or demande.passagers < 1:
        raise HTTPException(status_code=422, detail="Nombre de passagers invalide.")

    duree, _, moment = calculer_duree(demande)

    with ouvrir_db_relationnelle(ecriture=True) as con:
        for zone in (demande.zone_depart, demande.zone_arrivee):
            if not zone_existe(con, zone):
                raise HTTPException(status_code=422, detail=f"Zone inconnue : {zone}")

        preparer_table_reservation(con)
        nouvel_id = con.execute(
            "SELECT COALESCE(MAX(ReservationID), 0) + 1 FROM reservation"
        ).fetchone()[0]
        con.execute(
            """
            INSERT INTO reservation
                (ReservationID, reservation_datetime, PULocationID, DOLocationID,
                 passenger_count, duree_estimee, statut)
            VALUES (?, ?, ?, ?, ?, ?, 'planifiee')
            """,
            [nouvel_id, moment, demande.zone_depart, demande.zone_arrivee,
             float(demande.passagers), duree],
        )

    return {
        "id": nouvel_id,
        "date": demande.date,
        "heure": demande.heure,
        "zone_depart": demande.zone_depart,
        "zone_arrivee": demande.zone_arrivee,
        "passagers": demande.passagers,
        "duree_minutes": duree,
        "statut": "planifiee",
    }


@app.get("/courses")
def lister_courses():
    """Liste des courses planifiees, avec le nom des zones."""
    with ouvrir_db_relationnelle(ecriture=True) as con:
        preparer_table_reservation(con)
        lignes = con.execute("""
            SELECT r.ReservationID, r.reservation_datetime,
                   r.PULocationID, zd.Zone, r.DOLocationID, za.Zone,
                   r.passenger_count, r.duree_estimee, r.statut
            FROM reservation r
            LEFT JOIN taxi_zones zd ON zd.LocationID = r.PULocationID
            LEFT JOIN taxi_zones za ON za.LocationID = r.DOLocationID
            ORDER BY r.reservation_datetime DESC, r.ReservationID DESC
        """).fetchall()

    return [
        {
            "id": l[0],
            "date_heure": l[1].strftime("%Y-%m-%d %H:%M"),
            "zone_depart": l[2],
            "nom_depart": l[3],
            "zone_arrivee": l[4],
            "nom_arrivee": l[5],
            "passagers": int(l[6]) if l[6] is not None else None,
            "duree_minutes": l[7],
            "statut": l[8],
        }
        for l in lignes
    ]