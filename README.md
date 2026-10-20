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

## Machine Learning

### Objectif

Le modèle de Machine Learning de Frenchcab a pour objectif de **prédire la durée d'une course de taxi**, exprimée en minutes.

La variable cible est :

```text
trip_duration_min
```

Elle est calculée pendant le traitement des données à partir des dates de début et de fin de trajet :

```text
tpep_pickup_datetime
tpep_dropoff_datetime
```

### Chargement des données analytiques

Les données d'entraînement sont récupérées depuis la base décisionnelle SQLite :

```text
ETL/frenchcab.db
```

Sur la VM, cette base est conservée dans un volume Docker persistant et accessible au conteneur à l'emplacement `/app/ETL/frenchcab.db`.

### Variables utilisées

Parmi les principales variables utilisées pour la prédiction :

- `trip_distance`
- `heure`
- `minute`
- `mois`
- `est_weekend`
- `nom_jour`
- `id_localisation_d`
- `id_localisation_a`

### Préparation des données

La préparation est réalisée dans :

```text
ml/preparation.py
```

Ce module contient les fonctions permettant de charger et de préparer les données nécessaires à l'entraînement.

Il est utilisé par `entrainement.py`.

### Modèles testés

Deux algorithmes sont comparés pendant l'entraînement :

- `LinearRegression`
- `RandomForestRegressor`

Le modèle présentant les meilleures performances sur les données de validation est sélectionné.

Lors de notre dernier entraînement, le modèle retenu était un **RandomForestRegressor**.

### Entraînement

L'entraînement est réalisé avec :

```bash
python ml/entrainement.py
```

Il utilise les données de la base décisionnelle pour construire un nouveau modèle.

Le chemin de sauvegarde peut être configuré avec la variable d'environnement `MODEL_OUTPUT_PATH`.

Dans le cadre du MLOps de la semaine 4, l'objectif est de **conserver plusieurs versions du modèle**, par exemple :

```text
modele_v1.pkl
modele_v2.pkl
```

Chaque version doit pouvoir être évaluée et identifiée indépendamment.

L'entraînement sur la VM sera déclenché manuellement via le workflow `mlops.yml`, une fois son intégration terminée.

### Prédiction

Le module :

```text
ml/prediction.py
```

charge le modèle indiqué par la variable d'environnement `MODEL_PATH`.

Il utilise ensuite ce modèle pour calculer la durée estimée d'un trajet.

Exemple de résultat :

```text
Temps de trajet estimé : 17.75 minutes
```

Le modèle est chargé en mémoire au démarrage du processus Python. Après une activation ou une restauration, le backend doit donc être redémarré pour utiliser le modèle sélectionné.

---

## MLOps — Versionnement, comparaison et déploiement des modèles

### Objectif

Le pipeline MLOps de Frenchcab permet de gérer le cycle de vie des modèles de prédiction.

Il doit permettre de :

1. Entraîner de nouvelles versions du modèle.
2. Conserver plusieurs modèles identifiables.
3. Évaluer deux versions sur un même jeu de données.
4. Comparer leurs performances avec la MAE.
5. Vérifier le respect du seuil de qualité.
6. Activer explicitement une version admissible.
7. Restaurer la version précédente en cas de problème.
8. Vérifier que l'API utilise réellement la version sélectionnée.

L'objectif est de faire évoluer le modèle **sans dégrader le fonctionnement de l'application Frenchcab**.

### Architecture CI/CD et MLOps

Le projet utilise GitHub Actions, Docker, Docker Hub et une VM Linux.

Trois workflows sont prévus :

| Workflow | Rôle | Déclenchement |
|---|---|---|
| `ci.yml` | Tests, validation du code et construction/publication de l'image Docker | Selon les événements configurés dans la CI |
| `cd.yml` | Déploiement de l'application sur la VM | Après une CI réussie, déclenchée manuellement sur `dev` |
| `mlops.yml` | Entraînement, comparaison, activation et restauration des modèles | Manuel (`workflow_dispatch`) |

**La CD et le MLOps sont indépendants.**

Un déploiement de l'application ne déclenche plus automatiquement l'entraînement d'un modèle ni sa mise en production.

### Déploiement de l'application — `cd.yml`

Le workflow `cd.yml` :

1. Vérifie la réussite de la CI.
2. Se connecte à la VM par SSH.
3. Transmet la référence de l'image Docker validée.
4. Exécute le script `deploy.sh` déjà présent sur la VM.
5. Vérifie que l'API FastAPI répond correctement.

Le script `deploy.sh` assure notamment la récupération et le démarrage des images avec Docker Compose.

Les modèles sont conservés dans un volume persistant afin de ne pas être perdus lors des redéploiements.

### Gestion des modèles — `mlops.yml`

Un second workflow GitHub Actions est prévu pour les opérations MLOps.

Il propose cinq actions :

| Action | Fonction |
|---|---|
| `verifier` | Consulter les modèles présents sur la VM et identifier le fichier actif |
| `entrainer` | Entraîner et sauvegarder une nouvelle version |
| `comparer` | Évaluer deux versions sur les mêmes données |
| `activer` | Sélectionner explicitement une version admissible |
| `rollback` | Restaurer la version précédente |

L'action `verifier` est prévue pour être non destructive.

Les autres actions sont en cours d'intégration avec les scripts Python du projet.

### Entraînement et versionnement

Le script `ml/entrainement.py` entraîne les algorithmes et sélectionne le modèle retenu.

Les versions doivent être conservées sous des noms distincts afin d'éviter d'écraser les modèles précédents.

Exemple d'organisation prévue :

```text
ml/
├── modele_v1.pkl
├── modele_v2.pkl
├── modele_temps_trajet.pkl
└── version_active.json
```

- `modele_v1.pkl` : première version conservée.
- `modele_v2.pkl` : deuxième version à comparer.
- `modele_temps_trajet.pkl` : modèle utilisé par l'application.
- `version_active.json` : fichier d'état envisagé pour identifier la version active et la version précédente.

Le format définitif des fichiers de versionnement sera confirmé après intégration des modifications d'entraînement.

### Évaluation des modèles — `MLO.py`

Le script :

```text
ml/MLO.py
```

permet d'évaluer un modèle sur un jeu de données indépendant de l'entraînement.

Le jeu d'évaluation utilisé est celui des taxis de New York d'avril 2026 :

[ Télécharger yellow_tripdata_2026-04.parquet ](https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2026-04.parquet)

Exemple d'exécution locale, avec les chemins de données et de modèle configurés :

```bash
python ml/MLO.py --seuil 6
```

Le script calcule notamment :

- Le nombre de trajets évalués.
- La durée moyenne réelle.
- La durée moyenne prédite.
- La MAE exprimée en minutes.
- Le statut de conformité au seuil.
- L'empreinte identifiant le modèle évalué.

**Le seuil de qualité est fixé à une MAE inférieure ou égale à 6 minutes.**

Une version dépassant ce seuil ne doit pas pouvoir être activée par la procédure normale.

### Comparaison de deux versions

La semaine 4 introduit la comparaison de deux modèles existants.

Les deux versions doivent être évaluées :

- Sur exactement le même jeu de données.
- Avec la même méthode de calcul de la MAE.
- Avec le même seuil de qualité.

Un rapport doit permettre de consulter leurs métriques, d'identifier les versions admissibles et de comparer leurs performances.

Le format définitif du rapport de comparaison est en cours de développement.

**Le modèle présentant la meilleure MAE n'est pas automatiquement activé.** L'activation reste une opération explicite.

### Résultats de la dernière évaluation

Lors du pipeline MLOps du 20 octobre 2026, un modèle Random Forest a été entraîné et évalué.

| Indicateur | Résultat |
|---|---|
| Algorithme | `RandomForestRegressor` |
| MAE sur le jeu de test interne | 3,78 minutes |
| MAE sur les données d'avril 2026 | 4,63 minutes |
| Seuil de qualité | 6 minutes |
| Statut | Conforme |
| Identifiant SHA-256 (12 caractères) | `886e25d2f40c` |

Ces résultats concernent la version évaluée à cette date et ne constituent pas encore une comparaison entre V1 et V2.

### Activation explicite d'une version

Le script :

```text
ml/publier_modele.py
```

est adapté pour pouvoir sélectionner explicitement une version.

Exemple de commande prévue :

```bash
python ml/publier_modele.py --version v2
```

Avant activation, le mécanisme vérifie :

1. L'existence du fichier modèle.
2. L'existence de son rapport d'évaluation.
3. La correspondance entre le fichier et l'empreinte SHA-256 enregistrée.
4. Le statut de validation.
5. Le respect du seuil MAE ≤ 6 minutes.

Une version non conforme doit être refusée.

Après une activation réussie, le backend doit être rechargé pour utiliser le modèle sélectionné.

Cette fonctionnalité est en cours de sécurisation et de test.

### Retour arrière — Rollback

Le script :

```text
ml/rollback_modele.py
```

est prévu pour restaurer le modèle précédemment utilisé.

Le mécanisme doit :

1. Identifier la version précédente.
2. Vérifier la cohérence de son modèle et de ses métadonnées.
3. Restaurer cette version.
4. Redémarrer le backend.
5. Vérifier que les prédictions et les informations exposées correspondent à la version restaurée.

Le rollback doit fonctionner sans nouvel entraînement et sans modification manuelle du code source.

Cette fonctionnalité est en cours de développement.

### Stockage des modèles sur la VM

Les fichiers ML sont conservés dans :

```text
/home/groupe2/frenchcab/ml/
```

Ce dossier est monté dans le conteneur Docker sous :

```text
/ml/
```

Les modèles et leurs rapports sont ainsi persistants entre deux redéploiements.

Les fichiers historiques de la semaine 3 sont :

| Fichier | Rôle |
|---|---|
| `modele_candidat.pkl` | Modèle candidat de l'ancien pipeline |
| `resultats_candidat.json` | Rapport du candidat |
| `modele_temps_trajet.pkl` | Modèle actif |
| `resultats.json` | Rapport du modèle publié |

Les fichiers de versionnement V1/V2 seront ajoutés dans le cadre de la semaine 4.

### Compatibilité développement et production

Les scripts Python doivent pouvoir être exécutés :

- En développement local, sur le PC des développeurs.
- Dans le conteneur Docker de la VM.

Pour cela, les chemins sont configurables par variables d'environnement, avec des valeurs par défaut adaptées au développement local.

Principales variables :

| Variable | Utilisation |
|---|---|
| `ML_DIR` | Dossier de stockage des modèles |
| `MODEL_PATH` | Modèle chargé pour les prédictions |
| `MODEL_OUTPUT_PATH` | Destination d'un nouveau modèle entraîné |
| `MODEL_EVALUATION_PATH` | Modèle à évaluer |
| `EVALUATION_DATA_PATH` | Jeu de données d'évaluation |
| `RESULTATS_PATH` | Destination du rapport d'évaluation |

Le même code Python doit pouvoir être utilisé en local et en production, sans modifier manuellement les chemins dans les scripts.

### Tests et contrôle qualité

Les tests automatisés doivent vérifier :

- Le respect du seuil de qualité.
- Le refus d'activation d'un modèle non admissible.
- La correspondance entre le modèle et son rapport.
- L'activation de la version demandée.
- La restauration de la version précédente.
- La cohérence des informations de version.
- L'absence de régression sur les fonctionnalités existantes.

Les tests seront intégrés à la CI avec les contrôles déjà présents.

### État d'avancement

**Déjà opérationnel :**
- Entraînement et sélection d'un Random Forest.
- Évaluation avec calcul de la MAE.
- Vérification du seuil de qualité.
- Identification d'un modèle par SHA-256.
- Stockage persistant sur la VM.
- Déploiement Docker via CI/CD.
- API FastAPI accessible après déploiement.

**En cours de développement pour la semaine 4 :**
- Sauvegarde de plusieurs versions distinctes.
- Comparaison V1/V2.
- Déclenchement manuel des opérations MLOps.
- Activation explicite d'une version.
- Rollback sécurisé.
- Synchronisation des métadonnées avec le modèle réellement chargé.
- Tests automatisés des nouveaux mécanismes.

Cette évolution permet de **séparer l'entraînement, l'évaluation et la mise en production**, afin de maîtriser les changements de modèle et de garantir la continuité de fonctionnement de Frenchcab.

## Etat d'avancement S3
Le modèle est sur la VM ainsi que les données et bases
dans le dossier frenchcab :

* db/
* ml/
* raw_data

TOUTEFOIS un problème de persistance des volumes ne permet pas encore d'enregistrer le modèle depuis l'application en production.