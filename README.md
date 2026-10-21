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
python -m ml.entrainement
```
Depuis la VM, dans le dossier contenant compose.yml :
```bash
docker compose exec -T -e MODELS_DIR=/ml/modeles backend python /app/ml/entrainement.py
```
Attention : deux noms de versions différents ne garantissent pas deux modèles différents si les données, paramètres et graines aléatoires sont identiques. Vérifier les empreintes SHA-256 avant la démonstration V1/V2.

Pour avoir deux versions différentes, pour le deuxième entrainement changer les données `n_estimators`, `max_depth` sur le modèle de `RadomForestRegressor`. Attention il ne fait pas changer `random_state` entre deux versions où la reproductivité ne marche plus et donc les deux modèles ne sont plus comparables. Exemple de changement pour la V2 :
```python
"Random Forest": Pipeline([
        ("prep", clone(preprocessor)),
        ("reg", RandomForestRegressor(
            n_estimators=30,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        ))
    ])
```

### Prédiction
Le module `ml/prediction.py` charge le modèle de production indiqué par **MODEL_PATH** :
- En local : ml/modele_temps_trajet.pkl par défaut.
- Sur la VM : /ml/modele_temps_trajet.pkl lorsque MODEL_PATH est configuré dans Docker.

Une fois importé, le modèle reste chargé en mémoire dans le processus Python. Après toute activation ou restauration, FastAPI doit donc être redémarré ou son processus rechargé pour utiliser effectivement la version choisie.

La route `GET /modele/version` a été ajoutée au code pour afficher la version mémorisée lors du chargement du modèle. Son fonctionnement avec les vrais modèles reste à vérifier sur la VM.

## Déploiement CI/CD et MLOPS

### Architecture CI/CD et MLOps

Le projet Frenchcab repose sur trois workflows GitHub Actions distincts :

| Élément | Responsabilité | Déclenchement |
|---|---|---|
| `ci.yml` | Tests Python, fusion vers `dev`, construction et publication Docker Hub | Automatique lors d'un push, sauf sur `main`, ou manuel |
| `cd.yml` | Déploiement du backend sur la VM et vérification HTTP | Déclenché explicitement par la CI après publication Docker |
| `mlops.yml` | Vérification, entraînement, comparaison, initialisation, activation et rollback des modèles | Manuel avec `workflow_dispatch` |
| `deploy.sh` | Récupération des images et démarrage des conteneurs Docker | Exécuté sur la VM par la CD |

La **CI/CD** gère le déploiement de l'application. Le **MLOps** gère les modèles de Machine Learning.

Ces deux processus sont séparés : un déploiement applicatif ne provoque ni nouvel entraînement ni activation automatique d'un modèle candidat.

Les workflows CD et MLOps partagent un groupe de concurrence GitHub Actions afin d'éviter deux opérations simultanées sur la VM.

---

### Fonctionnement de la CI/CD

#### 1. Déclencher la CI

La CI se déclenche automatiquement lorsqu'un commit est envoyé sur une branche autre que `main`, notamment `lola`.

Depuis le PC, dans Git Bash :

```bash
git add <fichiers_modifies>
git commit -m "description des modifications"
git push origin lola
```

Cette action déclenche le workflow `CI` sur GitHub Actions.

Le workflow réalise successivement :

1. Installation de Python 3.14 et des dépendances de `requirements-dev.txt`.
2. Exécution des tests avec `pytest -v`.
3. Si les tests réussissent sur `lola`, fusion automatique de cette branche dans `dev`.
4. Déclenchement d'une nouvelle CI sur `dev`.
5. Construction de l'image Docker du backend.
6. Publication de l'image sur Docker Hub, avec deux tags :
   - Le SHA du commit.
   - `latest`.
7. Déclenchement explicite du workflow CD avec le SHA de l'image publiée.

La publication Docker ne suffit pas à elle seule pour considérer le déploiement comme réussi : il faut également vérifier le résultat du workflow CD.

#### 2. Déclencher une CI manuellement

Il est également possible de lancer la CI depuis GitHub :

1. Ouvrir le dépôt **Frenchcab-Backend**.
2. Aller dans l'onglet **Actions**.
3. Sélectionner le workflow **CI**.
4. Cliquer sur **Run workflow**.
5. Choisir la branche `dev`.
6. Confirmer le lancement.

Une CI exécutée sur `dev` teste le code, construit l'image Docker et déclenche la CD si toutes les étapes réussissent.

#### 3. Déploiement automatique avec `cd.yml`

Après la publication sur Docker Hub, le job `build` de la CI appelle le workflow CD :

```bash
gh workflow run cd.yml \
  --repo "${{ github.repository }}" \
  --ref main \
  -f image_sha="${GITHUB_SHA}"
```

Le workflow CD utilise `workflow_dispatch` et reçoit le SHA de l'image à déployer.

Il établit une connexion SSH vers la VM, puis exécute :

```bash
cd /home/groupe2/frenchcab
bash ./deploy.sh
```

Le script `deploy.sh` effectue notamment :

```bash
docker compose pull
docker compose up -d --remove-orphans
docker compose ps backend
```

La CD vérifie ensuite les routes HTTP :

```text
GET /test
GET /modele/version
```

La première confirme que le backend répond. La seconde permet de vérifier que l'API du modèle est accessible.

Si une vérification échoue, le workflow CD est signalé en échec.

Le déploiement conserve les fichiers MLOps persistants grâce au volume Docker `/ml`.

#### 4. Suivre une exécution CI/CD

Depuis GitHub, ouvrir :

`Frenchcab-Backend → Actions`

Vérifier les exécutions :

| Workflow | Résultat attendu |
|---|---|
| CI sur `lola` | Tests réussis et fusion vers `dev` |
| CI sur `dev` | Tests, build Docker et publication réussis |
| Continuous Deployment - Backend | Déploiement sur la VM réussi |

En cas d'erreur, consulter les logs du job concerné.

Le workflow CD peut également être lancé manuellement depuis GitHub Actions, à condition de fournir le SHA d'une image Docker déjà publiée.

---

### Fonctionnement du MLOps

Le workflow `mlops.yml` est indépendant de la CI/CD.

Il permet de gérer plusieurs versions du modèle de prédiction de durée des trajets, sans modifier le code applicatif.

#### Lancer le MLOps depuis GitHub Actions

1. Ouvrir **Frenchcab-Backend** sur GitHub.
2. Aller dans **Actions**.
3. Sélectionner **MLOps - Frenchcab**.
4. Cliquer sur **Run workflow**.
5. Sélectionner la branche `main`.
6. Choisir l'opération souhaitée.
7. Renseigner les versions de référence et candidate.
8. Confirmer le lancement.

Les paramètres disponibles sont :

| Paramètre | Description | Exemple |
|---|---|---|
| `operation` | Opération MLOps à exécuter | `pipeline` |
| `version` | Version candidate | `v2` |
| `version_actuelle` | Version de référence | `v1` |

#### Opérations disponibles

| Opération | Fonction |
|---|---|
| `pipeline` | Vérifie les fichiers, compare les modèles, applique les critères de qualité et initialise ou active une version si les conditions sont réunies |
| `verifier` | Liste les versions disponibles et affiche la version active |
| `entrainer` | Exécute le script d'entraînement sans activation automatique |
| `comparer` | Compare les performances de deux versions |
| `initialiser` | Initialise V1 lors de la première mise en service |
| `activer` | Active explicitement une version après vérification des critères |
| `rollback` | Restaure la version précédente |

L'opération recommandée pour exécuter la chaîne de validation est `pipeline`.

Le rollback reste une opération distincte, déclenchée manuellement en cas de besoin.

#### Déroulement du pipeline MLOps

Lorsqu'on sélectionne `pipeline`, GitHub Actions exécute automatiquement les étapes suivantes sur la VM :

1. Vérification de la présence des modèles et du fichier d'évaluation.
2. Évaluation des versions sur le même jeu de données.
3. Calcul des MAE et génération du rapport.
4. Vérification du seuil de qualité : **MAE ≤ 6 minutes**.
5. Comparaison de la MAE du candidat avec celle du modèle de référence.
6. Initialisation de V1 si aucune version n'est active, ou promotion du candidat si les critères sont satisfaits.
7. Redémarrage du backend lorsqu'une version est activée.
8. Vérification de la version chargée par l'API.

La candidate n'est promue automatiquement que si elle est conforme et si sa MAE est inférieure ou égale à celle du modèle de référence.

Lors de la toute première exécution, le pipeline initialise uniquement V1, sans activer immédiatement la candidate.

**Le pipeline est automatisé dans son exécution, mais son déclenchement reste manuel avec `Run workflow`.**

---

### Arborescence du stockage MLOps

Les fichiers persistants sont stockés sur la VM :

```text
/home/groupe2/frenchcab/ml/
```

Ils sont accessibles depuis le conteneur Docker sous :

```text
/ml/
```

Arborescence :

```text
/ml/
└── modeles/
    ├── v1/
    │   ├── model.pkl
    │   ├── metadata.json
    │   └── evaluation_validation.csv
    ├── v2/
    │   ├── model.pkl
    │   ├── metadata.json
    │   └── evaluation_validation.csv
    ├── historique_rapports/
    │   └── ...
    ├── resultats_comparaison.json
    └── version_active.json
```

Chaque dossier `vN` conserve un modèle et ses métadonnées.

Le fichier `version_active.json` indique la version active, la version précédente, ainsi que l'empreinte SHA-256 du modèle actif.

Les scripts d'activation et de rollback mettent à jour cet état sans recopier les fichiers `model.pkl`.

L'API sélectionne le modèle à partir de cet état et vérifie son empreinte lors du chargement.

---

### Évaluation et comparaison — `ml/MLO.py`

Les modèles sont évalués à partir du jeu indépendant d'avril 2026 :

```text
/raw_data/yellow_tripdata_2026-04.parquet
```

La comparaison utilise un échantillon reproductible de 100 000 trajets et calcule la MAE en minutes.

Le seuil de qualité est fixé à **6 minutes**.

La comparaison est normalement exécutée via l'opération `pipeline` ou `comparer` du workflow GitHub Actions.

Pour une exécution directe sur la VM :

```bash
cd /home/groupe2/frenchcab

docker compose exec -T backend python -m ml.MLO \
  --actuelle v1 \
  --candidate v2 \
  --seuil 6 \
  --donnees /raw_data/yellow_tripdata_2026-04.parquet
```

Le rapport principal est enregistré dans :

```text
/ml/modeles/resultats_comparaison.json
```

Il contient les versions évaluées, leurs empreintes SHA-256 abrégées, leurs MAE, le nom du jeu de données, le nombre de trajets et le seuil retenu.

Une copie horodatée est également conservée dans `historique_rapports/`.

#### Résultats de référence

Lors de la validation du 21 octobre 2026 :

| Modèle | Algorithme | MAE | Conformité |
|---|---|---|---|
| V1 | Random Forest | 4,63 min | Conforme |
| V2 | Random Forest | 4,78 min | Conforme |

Les deux modèles respectent le seuil de qualité, mais V1 présente une MAE légèrement inférieure.

Le pipeline refuse donc la promotion automatique de V2 selon la règle de performance retenue.

---

### Activation d'un modèle — `ml/publier_modele.py`

L'activation est gérée par le workflow MLOps.

Le script vérifie notamment :

1. L'existence du modèle à activer.
2. Sa présence dans le rapport de comparaison.
3. La correspondance de l'empreinte SHA-256.
4. Le respect du seuil MAE.
5. La cohérence de la version active enregistrée.

Initialisation de V1 dans le conteneur :

```bash
docker compose exec -T backend \
  python -m ml.publier_modele \
  --version v1 \
  --initialiser
```

Activation ultérieure de V2 :

```bash
docker compose exec -T backend \
  python -m ml.publier_modele \
  --version v2
```

Ces commandes sont exécutées automatiquement par les opérations correspondantes du workflow MLOps.

Après une activation, le workflow redémarre le backend :

```bash
docker compose restart backend
```

Puis il contrôle la version exposée par l'API.

---

### Retour arrière — `ml/rollback_modele.py`

Le rollback permet de restaurer la version précédemment active sans réentraîner le modèle.

Il lit `version_active.json`, vérifie la version précédente et met à jour l'état d'activation.

L'opération est accessible depuis GitHub Actions :

`Actions → MLOps - Frenchcab → Run workflow → rollback`

La commande équivalente sur la VM est :

```bash
docker compose exec -T backend \
  python -m ml.rollback_modele
```

Le workflow redémarre ensuite le conteneur et vérifie que l'API utilise la version restaurée.

Le rollback ne peut pas être exécuté si aucune version précédente n'est enregistrée.

---

### Vérification de la version active par l'API

Une route spécifique est disponible :

```http
GET /modele/version
```

Elle permet de consulter la version du modèle chargée par FastAPI.

Après l'activation ou le rollback, le workflow MLOps interroge cette route et vérifie que la version renvoyée correspond à celle attendue.

Le chargement du modèle s'appuie également sur une vérification SHA-256 afin de détecter une différence entre le fichier `model.pkl` et la version enregistrée.

---

### Compatibilité développement / production

| Variable ou chemin | Utilisation | Valeur sur la VM |
|---|---|---|
| `ML_DIR` | Racine du stockage ML | `/ml` |
| `MODELS_DIR` | Répertoire des versions | `/ml/modeles` |
| `EVALUATION_DATA_PATH` | Fichier Parquet d'évaluation, si utilisé par le script | `/raw_data/yellow_tripdata_2026-04.parquet` |
| `version_active.json` | Référence du modèle actif | `/ml/modeles/version_active.json` |

Les modèles sont stockés indépendamment des images Docker, ce qui permet de mettre à jour le backend sans écraser les fichiers ML.

Les modèles V1 et V2 ont été entraînés avec **scikit-learn 1.9.0**.

La version de scikit-learn installée dans l'image Docker a été fixée à :

```text
scikit-learn==1.9.0
```

Les dépendances de développement sont définies dans `requirements-dev.txt`, qui réutilise celles de production grâce à :

```text
-r requirements.txt
```

---

### Tests automatisés

Les tests de gestion des modèles se trouvent dans :

```text
tests/test_gestion_modele.py
```

Ils utilisent notamment `pytest` et `tmp_path` pour vérifier la logique de gestion des versions avec des fichiers temporaires, sans entraîner de vrais modèles.

Les scénarios comprennent :

- Activation d'une nouvelle version.
- Refus d'un modèle dépassant le seuil MAE.
- Refus d'une empreinte SHA-256 incorrecte.
- Retour arrière vers la version précédente.
- Refus d'un rollback sans version précédente.
- Refus d'un rollback vers un modèle non conforme.

Exécution locale :

```bash
python -m pytest tests/test_gestion_modele.py -v
```

Ces tests sont également exécutés dans le cadre de la CI grâce à la commande :

```bash
pytest -v
```

Ils vérifient la logique des scripts, mais ne remplacent pas les contrôles d'intégration effectués sur la VM.

---

### État d'avancement

**CI/CD : opérationnelle.**

La chaîne automatique depuis `lola` vers `dev`, Docker Hub et la VM a été validée. Le déclenchement explicite de la CD utilise le SHA de l'image Docker publiée.

**MLOps : pipeline opérationnel.**

Le pipeline MLOps a été exécuté avec succès depuis GitHub Actions : détection des modèles, comparaison sur 100 000 trajets, décision de qualité, initialisation de V1, redémarrage Docker et vérification HTTP.

**Version active : V1.**

Le modèle V1 a été initialisé et reconnu par l'API. V2 reste disponible comme candidate, mais n'a pas été promue automatiquement car sa MAE est légèrement supérieure.

**Reste à valider :** 
Le MLOps reste déclenché manuellement depuis GitHub Actions ; aucun entraînement périodique ni détection automatique d'un nouveau modèle n'est actuellement configuré.