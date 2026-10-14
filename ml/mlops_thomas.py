# Script de management de modèles prédictifs pour le projet Frenchcab
# Importation des modules
import os
from ETL.Extract import parquet_df, pd, year, month

# Définition des chemins de fichiers et variables globales


# Récupération des données dans le dossier raw_data
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Nettoyage des données
#
# 1. Chargement des données dans un dataframe Pandas et
# conversion des types de données

# 2. Nettoyage des données : identifier et compter les erreurs et
# incohérences, les valeurs manquantes et les doublons

# 3. Filtrage des données : on ne garde que les données pertinentes 
# pour l'analyse et la modélisation

# 4. Transformation des données : modification des formats au besoin,
# création de nouvelles variables, etc.

# 5. Echantillonnage des données : on peut créer un échantillon de données pour
# tester les modèles prédictifs avant de les appliquer à l'ensemble des données

