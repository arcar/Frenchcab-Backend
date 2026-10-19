# Frenchcab-Backend

## Prérequis
Pour ce projet, les outils suivants doivent être installés :

* Docker Desktop
* Git
* FastAPI
* sqlite3

## Données sources

Le jeu de données n'est pas versionné dans le dépôt : il doit être téléchargé manuellement.

1. À la racine du backend, créer un dossier `raw_data` :


2. Télécharger un fichier **Yellow Taxi Trip Records** au format Parquet depuis le site de la TLC :
   [https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)

3. Placer le fichier téléchargé dans `raw_data/`.

Arborescence attendue :

```
Frenchcab-Backend/
├── raw_data/
│   └── yellow_tripdata_2026-01.parquet
├── ...
```

## Contexte 
Vous intégrez une équipe chargée de développer, sur cinq semaines, une application exploitant les données réelles des taxis de New York publiées par la NYC Taxi & Limousine Commission (TLC).

## Structuration du projet
Projet avec **4 repos** `Github`

```
Frenchcab-compose
-> Frenchcab-Backend + Frenchcab-Frontend + Frenchcab-Gateway
```
Le dossier `Frenchcab-compose` contient les autres dossiers du projet (`Frenchcab-Backend`, `Frenchcab-Frontend`, `Frenchcab-Gateway`) il est là pour orchetrer tous le projet.

## Installation 

### 1. Github

1. Cloner les autres repos dans le dossier `Frenchcab-compose` :
- `Frenchcab-Frontend` :
```powershell
https://github.com/arcar/Frenchcab-Backend.gitgit add 
```
Demander l'accès en tant que membre à `mmorkos-cyber`, puis lire le `contributing`.

2. Secrets **Github**
Dans ce repo ont été ajouté des secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`), afin de pouvoir lancer le `workflows`.

3. `.github`
Dans `Frenchcab-Frontend` a été créer un dossier `github` qui contient le `workflows` avec un fichier `ci.yml`.
Actuellement le fichier `ci.yml`, sert uniquement à lancer `docker build` et `docker push`, le Frontend n'ayant à ce stade pas de test.

### 2. VM

1. Pour accéder à la VM :
```bash
ssh -i ~/Downloads/myKey.pem groupe2@{numéro api dans VM-linux.txt}
```
Il existe 4 utilisateurs crées (`utilisateur1`, `utilisateur2`, `utilisateur3`, `utilisateur4`). Chacun a un mot de passe qui se trouve dans le fichier text `VM-linux.txt`.

2. `deploy.sh`
Dans la VM a été crée un fichier `deploy.sh` qui avec `cron` se déclenche à intervalle de ....... pour faire un `docker pull` et un `docker up`.

### 3. Docker

Le Frontend a été dockerisé.

Les images docker sont sur **Dockerhub**, et s'active via le fichier `ci.yml` dans ce repo, il suffit donc de faire actuellement un `push` sur la branche `staging`. A terme il semble plus judicieux de modifier `ci.yml` pour qu'il s'active sur un `push` sur la branche `dev`.

## Traitement des données

### Gestion des valeurs manquantes restantes

Après application des règles de nettoyage, certaines colonnes contenaient encore
des valeurs manquantes (`NaN`).

Pour certaines colonnes, ces valeurs ont été remplacées par des valeurs par défaut
plutôt que de supprimer entièrement les lignes concernées.

Ce choix permet de conserver les informations utiles présentes sur ces lignes,
notamment celles pouvant servir à l'analyse ou à la prédiction.

---

### Pipeline ETL

Le traitement des données est organisé en trois étapes :

1. Créer un fichier `raw_data` dans `Frenchcab-Backend`, pour acceuillir le fichier parquet.
Télécharger le dossier parquet ici : https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2026-01.parquet

2. `Extract.py`
   - charge les fichier `taxi_zone_lookup.csv` dans le `dossier raw_data` ;

2. `Transform.py`
   - convertit les types ;
   - traite certaines valeurs manquantes ;
   - supprime les doublons ;
   - calcule notamment la durée de trajet ;
   - filtre les valeurs aberrantes ;

3. `Load.py`
   - initialise la base SQLite ;
   - crée les tables analytiques ;
   - insère les données transformées.

Pour exécuter tout l'**ETL** (extract, transform, load), lancer :

```bash
python ETL/Load.py
```

<<<<<<< HEAD
=======
Ce qui va créer deux bdd :
- `frenchcab_relationnelle.db` = base de donnée relationnelle
- `frenchcab.db` = base de donnée décisionnelle

>>>>>>> lola
## Machine Learning

### Objectif

Le modèle de Machine Learning a pour objectif de **prédire la durée d'une course de taxi**.

La variable cible utilisée est :

```text
trip_duration_min
```
Cette durée est calculée en amont dans le traitement des données à partir de :
```
tpep_pickup_datetime
tpep_dropoff_datetime
```
### Chargement des données analytiques
Les données utilisées pour l'entraînement sont chargées depuis la base SQLite :
```
ETL/frenchcab.db
```
### Les principales variables utilisées sont :
```
trip_distance
heure
minute
mois
est_weekend
nom_jour
id_localisation_d
id_localisation_a
```
### Préparation des données
Les données sont préparées dans le fichier, lancer le fichier :
```
ml/preparation.py
```
### Modèles testés
Deux modèles sont comparés :
```
LinearRegression
RandomForestRegressor
```

## Entrainement ml

Lancer le fichier `entrainement.py` pour créer le modèle du ml `modele_temps_trajet.pkl"`, qui sera dans le dossier `ml`.

## Prédiction

Lancer le fichier `prediction.py` pour avoir une prédiction, vous devez obtenir dans le log une prédiction : *Temps de trajet estimé : 17.75 minutes*



## MLOPS
Commencer par télécharger le nouveaux parquet qui correspond à la pèriode d'Avril 2026 : https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2026-04.parquet

Puis lancer le fichier MLO.py :
```bash
python ml/MLO.py
```
Le fichier MLO va :
- charger les données des taxis du mois d'avril 2026
- evaluation du modèle
  - retester le modèle **MAE** 
  - définir un seuil de qualité en audessus duquel le ML est considéré comme non efficace
  - crée un rapport `resultats.json`

## Etat d'avancement
Le modèle est sur la VM ainsi que les données et bases
dans le dossier frenchcab :

* db/
* ml/
* raw_data

TOUTEFOIS un problème de persistance des volumes ne permet pas encore d'enregistrer le modèle depuis l'application en production.