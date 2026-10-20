
import hashlib
import json
import os
from io import BytesIO
from pathlib import Path

import joblib
import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent

DOSSIER_ML = Path(
    os.getenv("ML_DIR", str(DOSSIER_SCRIPT))
)

MODELS_DIR = Path(
    os.getenv("MODELS_DIR", str(DOSSIER_ML / "modeles"))
)

VERSION_ACTIVE_PATH = MODELS_DIR / "version_active.json"


# ============================================================
# 2. IDENTIFICATION DE LA VERSION ACTIVE
# ============================================================

if not VERSION_ACTIVE_PATH.is_file():
    raise FileNotFoundError(
        "Aucune version active : initialiser V1 avant "
        "d'effectuer des predictions."
    )

with open(VERSION_ACTIVE_PATH, "r", encoding="utf-8") as fichier:
    etat = json.load(fichier)

VERSION_MODELE_CHARGE = etat["version"]

# La version doit correspondre à un dossier v1, v2...
import re

if not re.fullmatch(r"v[1-9][0-9]*", VERSION_MODELE_CHARGE):
    raise ValueError("Version du modele invalide")

MODEL_PATH = MODELS_DIR / VERSION_MODELE_CHARGE / "model.pkl"

if not MODEL_PATH.is_file():
    raise FileNotFoundError(
        f"Modele actif introuvable : {MODEL_PATH}"
    )


# ============================================================
# 3. CONTROLE DU SHA-256
# ============================================================

donnees_modele = MODEL_PATH.read_bytes()

SHA_MODELE_CHARGE = hashlib.sha256(
    donnees_modele
).hexdigest()

if SHA_MODELE_CHARGE != etat.get("sha256_actif"):
    raise ValueError(
        "Le modele charge ne correspond pas "
        "au SHA-256 de version_active.json"
    )


# ============================================================
# 4. CHARGEMENT DU MODELE
# ============================================================

modele = joblib.load(BytesIO(donnees_modele))


def obtenir_version_modele():
    return VERSION_MODELE_CHARGE
