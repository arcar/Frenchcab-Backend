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

1. Créer un dossier `raw_data` dans `Frenchcab-Backend`, pour acceuillir le fichier parquet.
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

Ce qui va créer deux bdd :
- `frenchcab_relationnelle.db` = base de donnée relationnelle
- `frenchcab.db` = base de donnée décisionnelle

## Machine Learning

### Objectif

Le modèle de Machine Learning de Frenchcab prédit la durée d'une course de taxi en minutes. La variable cible, `trip_duration_min`, est calculée par différence entre `tpep_dropoff_datetime` et `tpep_pickup_datetime` lors de la préparation des données.

### Données et préparation
Les données d'entraînement sont chargées depuis la base décisionnelle SQLite `ETL/frenchcab.db`, accessible dans le conteneur de la VM sous `/app/ETL/frenchcab.db` grâce au montage Docker existant. Le module `ml/preparation.py` prépare les données consommées par `ml/entrainement.py`.

Dans la version d'`entrainement.py` transmise par l'équipe, les variables d'entrée sont :
- Catégorielles : nom_jour, id_localisation_d, id_localisation_a.
- Numériques : trip_distance, heure, minute, est_weekend.

*Point à vérifier avant la recette : ml/prediction.py transmet encore la variable mois, qui ne figure plus parmi les variables d'entraînement de cette version. Les variables utilisées à l'entraînement et à la prédiction doivent rester cohérentes.*


### Entraînement et versions
Le script `ml/entrainement.py` compare une **régression linéaire (LinearRegression)** et une **forêt aléatoire (RandomForestRegressor)**. Le modèle présentant la meilleure **MAE** sur le jeu de validation est réentraîné sur les ensembles d'entraînement et de validation, puis évalué sur un jeu de test interne.

L'entraînement produit une nouvelle version sans remplacer les versions précédentes :
```
ml/
├── modeles/
│   ├── v1/
│   │   ├── model.pkl
│   │   ├── metadata.json
│   │   └── evaluation_validation.csv
│   └── v2/
│       ├── model.pkl
│       ├── metadata.json
│       └── evaluation_validation.csv
└── modele_temps_trajet.pkl
```
Chaque dossier `vN` contient le **modèle entraîné**, ses **métadonnées** et les **métriques de validation** des algorithmes comparés. 

**MODELS_DIR** définit le dossier de stockage des versions : `ml/modeles/` par défaut en local et `/ml/modeles/` dans le conteneur de la VM.

Depuis la racine du backend en développement :
```bash
python ml/entrainement.py
```
Depuis la VM, dans le dossier contenant compose.yml :
```bash
docker compose exec -T -e MODELS_DIR=/ml/modeles backend python /app/ml/entrainement.py
```
Attention : deux noms de versions différents ne garantissent pas deux modèles différents si les données, paramètres et graines aléatoires sont identiques. Vérifier les empreintes SHA-256 avant la démonstration V1/V2.

### Prédiction
Le module `ml/prediction.py` charge le modèle de production indiqué par **MODEL_PATH** :
- En local : ml/modele_temps_trajet.pkl par défaut.
- Sur la VM : /ml/modele_temps_trajet.pkl lorsque MODEL_PATH est configuré dans Docker.

Une fois importé, le modèle reste chargé en mémoire dans le processus Python. Après toute activation ou restauration, FastAPI doit donc être redémarré ou son processus rechargé pour utiliser effectivement la version choisie.

La route `GET /modele/version` a été ajoutée au code pour afficher la version mémorisée lors du chargement du modèle. Son fonctionnement avec les vrais modèles reste à vérifier sur la VM.

## MLOps — Comparaison, activation et restauration des modèles

### Objectif de la semaine 4
Le système MLOps doit permettre de comparer deux versions compatibles sur les mêmes données, de contrôler leur qualité avec la MAE, de choisir explicitement une version à utiliser par Frenchcab, puis de revenir à la version précédente si nécessaire.

Il n'est pas nécessaire de réentraîner un modèle à chaque déploiement. Entraînement, évaluation, activation et retour arrière constituent des opérations distinctes.

### Architecture CI/CD et MLOps
|Élément|	Responsabilité|	Déclenchement|
|-------|-----------------|----------------|
|ci.yml|	Tests et construction/publication de l'image Docker|	Selon la configuration de la CI|
|cd.yml|	Connexion SSH à la VM, exécution de deploy.sh, vérification HTTP|	Après une CI réussie lancée manuellement sur dev, selon la condition actuelle|
|deploy.sh (sur la VM)|	Récupération et démarrage des images avec Docker Compose|	Appelé par la CD|
|mlops.yml|	Vérification, entraînement, comparaison, activation et rollback|	workflow_dispatch manuel|

La CD ne réentraîne plus automatiquement de modèle et n'active pas automatiquement de candidat. Le workflow MLOps est distinct et utilise la même VM.

### Arborescence du stockage MLOps
Les fichiers persistants de la VM se trouvent sur l'hôte dans `/home/groupe2/frenchcab/ml/`, monté dans le conteneur sous `/ml/`.

```
/ml/
├── modeles/
│   ├── v1/
│   │   ├── model.pkl
│   │   ├── metadata.json
│   │   └── evaluation_validation.csv
│   ├── v2/
│   │   ├── model.pkl
│   │   ├── metadata.json
│   │   └── evaluation_validation.csv
│   ├── resultats_comparaison.json
│   └── version_active.json
└── modele_temps_trajet.pkl
```
Les dossiers v1, v2, etc. contiennent les versions conservées. `modele_temps_trajet.pkl` est le fichier effectivement utilisé par FastAPI. `version_active.json` conserve les identifiants de la version active et de la précédente. Le rapport `resultats_comparaison.json` contient les métriques d'évaluation calculées par `MLO.py`.


### Évaluation et comparaison — ml/MLO.py
Les versions sont évaluées à partir du jeu indépendant d'avril 2026 :
```
yellow_tripdata_2026-04.parquet
```
Le script de comparaison utilise un échantillon reproductible (graine aléatoire fixe) et calcule la MAE en minutes, avec un seuil de qualité fixé à 6 minutes.

Exemple sur la VM, avec la version v2 comme candidate :
```bash
docker compose exec -T \
  -e MODELS_DIR=/ml/modeles \
  -e EVALUATION_DATA_PATH=/raw_data/yellow_tripdata_2026-04.parquet \
  backend python /app/ml/MLO.py --candidate v2 --seuil 6
```
Le rapport est enregistré par défaut dans `/ml/modeles/resultats_comparaison.json`. Dans le format transmis, il contient notamment actuelle, candidate, leurs identifiants de version, leurs empreintes SHA-256 abrégées et leurs MAE, ainsi que le jeu évalué et le seuil.

### Activation explicite — ml/publier_modele.py
Après comparaison, l'activation d'une version est une décision distincte. Le script reçoit explicitement --version et vérifie :
1. L'existence du fichier `modeles/vN/model.pkl`.
2. La présence de cette version dans resultats_comparaison.json.
3. La correspondance de l'empreinte SHA-256 avec le modèle évalué.
4. Le respect du seuil MAE ≤ 6 minutes.
5. La cohérence du modèle actuellement en production avec l'état enregistré.

Commande prévue en local, depuis la racine du backend :
```bash
python -m ml.publier_modele --version v2
```
Commande prévue dans le conteneur sur la VM :
```bash
docker compose exec -T \
  -e ML_DIR=/ml \
  -e MODELS_DIR=/ml/modeles \
  backend python -m ml.publier_modele --version v2
```
Le script remplace le fichier actif et enregistre le couple version / precedente dans `modeles/version_active.json`. Un redémarrage du backend est ensuite nécessaire pour que les prédictions utilisent le nouveau modèle.

### Retour arrière — ml/rollback_modele.py
Le rollback lit `modeles/version_active.json`, vérifie la version précédente et restaure son model.pkl en production. Il met ensuite à jour les identifiants actif/précédent. Il ne nécessite pas de nouvel entraînement.

Commande prévue en local :
```bash
python -m ml.rollback_modele
```
Commande prévue sur la VM :
```bash
docker compose exec -T \
  -e ML_DIR=/ml \
  -e MODELS_DIR=/ml/modeles \
  backend python -m ml.rollback_modele
```
Après un rollback, le workflow MLOps doit redémarrer le backend et vérifier la version exposée par `GET /modele/version`.

### Vérification du modèle chargé par l'API
La route ajoutée dans main.py est :
```
GET /modele/version
```
Elle renvoie la version mémorisée lors du chargement du modèle par `ml/prediction.py`. La correspondance avec le fichier actif est contrôlée à l'aide de son empreinte SHA-256 lorsque le fichier d'état est présent.

La validation complète reste à réaliser sur la VM : activation de V2, redémarrage, vérification de l'API et d'une prédiction, puis rollback vers V1 et nouvelle vérification.

### Compatibilité développement / production
Variable	Utilisation	Exemple sur la VM :

- **ML_DIR**	Racine du stockage ML `/ml`
- **MODELS_DIR**	Dossiers de versions et fichiers de suivi	`/ml/modeles`
- **MODEL_PATH**	Modèle utilisé par FastAPI	`/ml/modele_temps_trajet.pkl`
- **EVALUATION_DATA_PATH**	Données indépendantes d'évaluation	`/raw_data/yellow_tripdata_2026-04.parquet`
- Les scripts de gestion des modèles utilisent des chemins fondés sur __file__ par défaut en local et des variables d'environnement dans Docker.

Aucun fichier .env Python supplémentaire n'est obligatoire ; os.getenv() ne lit pas automatiquement un fichier .env.

### Tests automatisés
Les tests dédiés à la gestion des modèles se trouvent dans `tests/test_gestion_modele.py`. Ils ont été exécutés avec des fichiers fictifs isolés par **pytest** et **tmp_path**, sans vrai entraînement :
|Test|	Résultat obtenu|
|----|------------------|
|Activation de V2 et conservation de V1|	Réussi|
|Refus d'une MAE supérieure à 6 minutes|	Réussi|
|Refus d'une empreinte SHA-256 incorrecte|	Réussi|
|Rollback de V2 vers V1|	Réussi|
|Refus d'un rollback sans version précédente|	Réussi|
|Refus du rollback vers un modèle non conforme|	Réussi|

Exécution depuis la racine du backend :
```bash
python -m pytest tests/test_gestion_modele.py -v
```
**Bilan** : 6 tests réussis lors de l'exécution locale communiquée. Les tests valident la logique de fichiers et les refus attendus ; ils ne remplacent pas les tests d'intégration avec de vrais modèles, le redémarrage Docker ou le contrôle de la prédiction FastAPI.

### État d'avancement
Développé et testé localement : scripts d'activation et de rollback, tests unitaires de gestion des versions, correction des imports du package ml.

Préparé ou en cours d'intégration : workflow manuel mlops.yml, identification de la version par FastAPI, format final du rapport de comparaison et comparaison explicite V1/V2.

À valider avant la recette croisée : présence de deux modèles réellement distincts sur la VM, comparaison avec le rapport définitif, protection contre les opérations simultanées et interruptions brutales, activation V1 → V2 → V1 avec redémarrage et vérification des prédictions, puis vérification globale de CI/CD et HTTPS.
