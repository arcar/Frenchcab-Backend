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

Le modèle de Machine Learning de Frenchcab prédit la durée d'une course de taxi en minutes.

La variable cible `trip_duration_min` est calculée à partir de la différence entre `tpep_dropoff_datetime` et `tpep_pickup_datetime` lors de la préparation des données.

### Prérequis

Pour utiliser le Machine Learning, il faut disposer :

- De Python et des dépendances du projet.
- De la base de données décisionnelle `ETL/frenchcab.db`.
- Des données nécessaires à l'entraînement.
- Du fichier Parquet d'évaluation `yellow_tripdata_2026-04.parquet`.
- D'au moins une version de modèle entraînée.

Les modèles et les données volumineuses peuvent ne pas être inclus dans le dépôt Git. Leur présence doit donc être vérifiée avant l'exécution des scripts.

### Installation des dépendances en local

Depuis la racine de `Frenchcab-Backend`, créer un environnement virtuel :

```powershell
python -m venv .venv
```

Activer l'environnement sous Windows PowerShell :

```powershell
.\.venv\Scripts\Activate.ps1
```

Installer les dépendances :

```powershell
python -m pip install -r requirements.txt
```

Pour installer également les dépendances utilisées dans les tests et le développement :

```powershell
python -m pip install -r requirements-dev.txt
```

### Données et préparation

Les données d'entraînement sont chargées depuis la base décisionnelle SQLite :

```text
ETL/frenchcab.db
```

Dans le conteneur de la VM, cette base est accessible sous :

```text
/app/ETL/frenchcab.db
```

Le module `ml/preparation.py` prépare les données nécessaires à `ml/entrainement.py`.

Les variables utilisées par le modèle sont :

| Type | Variables |
|---|---|
| Catégorielles | `nom_jour`, `id_localisation_d`, `id_localisation_a` |
| Numériques | `trip_distance`, `heure`, `minute`, `est_weekend` |

La fonction de prédiction accepte également un paramètre `mois` pour conserver la compatibilité de l'API, mais ce paramètre ne figure pas parmi les variables d'entraînement de cette version.

### Entraînement et création des versions

Le script `ml/entrainement.py` compare une régression linéaire (`LinearRegression`) et une forêt aléatoire (`RandomForestRegressor`).

Le modèle sélectionné est enregistré dans un dossier de version.

Exemple d'arborescence :

```text
ml/
└── modeles/
    ├── v1/
    │   ├── model.pkl
    │   ├── metadata.json
    │   └── evaluation_validation.csv
    └── v2/
        ├── model.pkl
        ├── metadata.json
        └── evaluation_validation.csv
```

Chaque version conserve son modèle, ses métadonnées et ses métriques d'évaluation.

**En local**, depuis la racine de `Frenchcab-Backend` :

```powershell
python -m ml.entrainement
```

**Sur la VM**, depuis `/home/groupe2/frenchcab` :

```bash
docker compose exec -T \
  -w /app \
  -e MODELS_DIR=/ml/modeles \
  backend python -m ml.entrainement
```

Il est important d'utiliser `python -m ml.entrainement` plutôt que `python /app/ml/entrainement.py`, afin que Python reconnaisse correctement le package `ml`.

Pour produire deux modèles différents tout en conservant une comparaison reproductible, les hyperparamètres peuvent être modifiés, notamment `n_estimators` et `max_depth`. Il est recommandé de conserver un `random_state` fixe.

### Comparaison des modèles

L'entraînement ne suffit pas à rendre un modèle actif.

Avant toute initialisation ou activation, il faut générer un rapport de comparaison avec `ml/MLO.py`.

Le script évalue les versions sur le jeu indépendant d'avril 2026 et calcule leurs MAE.

**En local**, depuis la racine du backend, avec le fichier Parquet placé dans `raw_data/` :

```powershell
python -m ml.MLO --actuelle v1 --candidate v2 --seuil 6 --donnees raw_data/yellow_tripdata_2026-04.parquet
```

**Sur la VM** :

```bash
docker compose exec -T \
  -w /app \
  -e MODELS_DIR=/ml/modeles \
  backend python -m ml.MLO \
  --actuelle v1 \
  --candidate v2 \
  --seuil 6 \
  --donnees /raw_data/yellow_tripdata_2026-04.parquet
```

Le script génère :

```text
ml/modeles/resultats_comparaison.json
```

Ce rapport contient les résultats d'évaluation des versions, leurs MAE et leurs empreintes SHA-256.

Le seuil de qualité est fixé à **6 minutes de MAE**.

### Initialisation du modèle actif — Première installation

Après l'entraînement de V1 et V2, il est nécessaire de comparer les modèles avec `MLO.py` afin de générer `resultats_comparaison.json`.

Une fois le rapport généré, **V1 doit être initialisée pour pouvoir effectuer des prédictions**.

**En local**, depuis la racine de `Frenchcab-Backend` :

```bash
python -m ml.publier_modele --version v1 --initialiser
```

**Sur la VM**, depuis `/home/groupe2/frenchcab` :

```bash
docker compose exec -T \
  -w /app \
  -e ML_DIR=/ml \
  -e MODELS_DIR=/ml/modeles \
  backend python -m ml.publier_modele \
  --version v1 \
  --initialiser
```

Cette commande vérifie le rapport de comparaison, la qualité du modèle et son empreinte SHA-256, puis crée :

```text
ml/modeles/version_active.json
```

Le fichier contient la version active et la référence à la version précédente.

**Cette initialisation ne doit être effectuée qu'une seule fois par environnement.** Pour les activations suivantes, utiliser l'opération `pipeline` ou `activer` du MLOps.

Après initialisation, redémarrer FastAPI pour charger V1, puis vérifier :

```text
GET /modele/version
```

Sur la VM, l'opération `pipeline` de GitHub Actions peut effectuer cette initialisation automatiquement si aucune version n'est encore active.

### Initialisation du premier modèle actif

**Cette étape est obligatoire lors d'une première installation.**

L'entraînement et la comparaison produisent des modèles et des rapports, mais ne définissent pas automatiquement le modèle actif.

Le script `ml/publier_modele.py` permet d'initialiser V1 et de créer le fichier :

```text
ml/modeles/version_active.json
```

Ce fichier indique notamment la version active et son empreinte SHA-256.

**En local**, depuis la racine du backend :

```powershell
python -m ml.publier_modele --version v1 --initialiser
```

**Sur la VM** :

```bash
docker compose exec -T \
  -w /app \
  -e ML_DIR=/ml \
  -e MODELS_DIR=/ml/modeles \
  backend python -m ml.publier_modele \
  --version v1 \
  --initialiser
```

Le script vérifie la présence du modèle, sa correspondance avec le rapport de comparaison et le respect du seuil de qualité.

Après initialisation, l'arborescence contient :

```text
ml/
└── modeles/
    ├── v1/
    │   └── model.pkl
    ├── v2/
    │   └── model.pkl
    ├── resultats_comparaison.json
    └── version_active.json
```

Le fichier `version_active.json` ne doit pas être créé manuellement : le script d'initialisation assure les vérifications nécessaires.

### Prédiction et version active

Le module `ml/prediction.py` lit `version_active.json` afin de déterminer le modèle à utiliser.

Il charge ensuite le fichier :

```text
ml/modeles/vN/model.pkl
```

où `vN` correspond à la version active.

Les emplacements sont configurables avec les variables d'environnement :

| Environnement | `ML_DIR` | `MODELS_DIR` |
|---|---|---|
| Local | `ml/` | `ml/modeles/` |
| VM Docker | `/ml` | `/ml/modeles` |

Sur le PC, les chemins sont déterminés automatiquement à partir du dossier contenant `prediction.py`, sauf si des variables d'environnement les remplacent.

Sur la VM, Docker Compose fournit les chemins des volumes montés.

### Démarrage et vérification de FastAPI en local

Depuis la racine de `Frenchcab-Backend` :

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Documentation interactive :

```text
http://127.0.0.1:8000/docs
```

Vérification du modèle actif :

```text
http://127.0.0.1:8000/modele/version
```

Si V1 est correctement initialisée :

```json
{
  "version": "v1"
}
```

Si aucun modèle n'est initialisé, la route renvoie une erreur HTTP 503 avec un message expliquant l'absence de version active.

### Vérification sur la VM

Depuis `/home/groupe2/frenchcab` :

```bash
curl http://127.0.0.1:3001/modele/version
```

Le résultat doit indiquer la version active.

Après toute activation ou restauration, le conteneur doit être redémarré pour que FastAPI charge effectivement le modèle sélectionné :

```bash
docker compose restart backend
```

### Automatisation avec GitHub Actions

En production, ces opérations peuvent être réalisées directement depuis le workflow **MLOps - Frenchcab**.

Depuis GitHub :

1. Aller dans `Actions`.
2. Sélectionner `MLOps - Frenchcab`.
3. Cliquer sur `Run workflow`.
4. Sélectionner la branche `main`.
5. Choisir l'opération `pipeline`.
6. Renseigner la version actuelle et la version candidate.
7. Lancer le workflow.

Le pipeline vérifie les fichiers, effectue la comparaison et initialise V1 si aucune version n'est active. Lors des exécutions suivantes, il peut promouvoir une candidate conforme et au moins aussi performante que la version de référence.

Les opérations `entrainer`, `comparer`, `initialiser`, `activer` et `rollback` restent également accessibles séparément.

Le workflow MLOps est indépendant de la CI/CD : un déploiement applicatif ne déclenche pas automatiquement un nouvel entraînement.

### Création d'une nouvelle version de modèle (V3, V4...)

Le script `ml/entrainement.py` possède un système de versionnement automatique grâce à la fonction `prochaine_version()`.

À chaque entraînement, il recherche les versions existantes dans `MODELS_DIR` et crée un nouveau dossier avec le numéro suivant.

Par exemple, si `v1` et `v2` existent déjà, le prochain entraînement produira automatiquement `v3`.

#### 1. Modifier les paramètres du modèle (facultatif)

Avant un nouvel entraînement, il est possible de modifier les hyperparamètres du `RandomForestRegressor` dans `ml/entrainement.py` :

```python
"Random Forest": Pipeline([
    ("prep", clone(preprocessor)),
    ("reg", RandomForestRegressor(
        n_estimators=40,
        max_depth=12,
        random_state=42,
        n_jobs=-1
    ))
])
```

Cet exemple utilise 40 arbres et une profondeur maximale de 12, contre 30 arbres et une profondeur maximale de 10 pour V2.

Conserver un `random_state` fixe permet de reproduire les expérimentations dans un environnement identique.

**Attention :** changer les paramètres n'assure pas une amélioration des performances. La nouvelle version devra être évaluée.

#### 2. Lancer un nouvel entraînement

**Depuis GitHub Actions (méthode recommandée sur la VM)**

1. Ouvrir le dépôt GitHub `Frenchcab-Backend`.
2. Aller dans **Actions → MLOps - Frenchcab**.
3. Cliquer sur **Run workflow**.
4. Sélectionner la branche `main`.
5. Choisir l'opération `entrainer`.
6. Lancer le workflow.

Le script crée automatiquement la prochaine version disponible sur la VM, sans activer le modèle.

Si V1 et V2 sont déjà présents, le dossier suivant est créé :

```text
/ml/modeles/v3/
├── model.pkl
├── metadata.json
└── evaluation_validation.csv
```

**En local**, depuis la racine du backend :

```powershell
python -m ml.entrainement
```

**Directement sur la VM**, depuis `/home/groupe2/frenchcab` :

```bash
docker compose exec -T \
  -w /app \
  -e MODELS_DIR=/ml/modeles \
  backend python -m ml.entrainement
```

La version réellement créée est indiquée dans les logs de fin d'entraînement.

#### 3. Comparer V3 à la version active V1

Une fois V3 créée, retourner dans **Actions → MLOps - Frenchcab → Run workflow**.

Renseigner :

| Paramètre | Valeur |
|---|---|
| Branch | `main` |
| `operation` | `pipeline` |
| `version` | `v3` |
| `version_actuelle` | `v1` |

Le pipeline vérifie la présence des fichiers, évalue V1 et V3 sur le jeu indépendant d'avril 2026, calcule leurs MAE et applique les critères de promotion.

La candidate doit respecter le seuil de **6 minutes de MAE** et obtenir une MAE inférieure ou égale à celle de V1 pour être promue automatiquement.

- Si V3 respecte les critères, elle est activée, le backend redémarre et l'API vérifie la version chargée.
- Si V3 ne respecte pas les critères, V1 reste active.

**Il faut obligatoirement créer V3 avant de demander sa comparaison.** L'opération `pipeline` ne lance pas d'entraînement.

#### 4. Vérifier la version active

Sur la VM :

```bash
curl http://127.0.0.1:3001/modele/version
```

L'API renvoie la version réellement chargée, par exemple :

```json
{
  "version": "v3"
}
```

Ce résultat n'est attendu que si V3 a été activée avec succès.

#### 5. Revenir à la version précédente

En cas de problème après activation, ouvrir **Actions → MLOps - Frenchcab → Run workflow**, puis sélectionner `rollback`.

Cette opération restaure la version précédente enregistrée dans `version_active.json`, redémarre le backend et vérifie la version exposée par l'API.

Aucun réentraînement n'est nécessaire.

**Important :** le versionnement est propre à chaque environnement. Une V3 entraînée localement n'apparaît pas automatiquement sur la VM, et inversement. Les fichiers de modèles ne sont pas synchronisés par GitHub Actions.

Déploiement CI/CD et MLOPS
Architecture CI/CD et MLOps
Le projet Frenchcab repose sur trois workflows GitHub Actions distincts :
Élément	Responsabilité	Déclenchement
ci.yml	Tests Python, fusion vers dev, construction et publication Docker Hub	Automatique lors d'un push, sauf sur main, ou manuel
cd.yml	Déploiement du backend sur la VM et vérification HTTP	Déclenché explicitement par la CI après publication Docker
mlops.yml	Vérification, entraînement, comparaison, initialisation, activation et rollback des modèles	Manuel avec workflow_dispatch
deploy.sh	Récupération des images et démarrage des conteneurs Docker	Exécuté sur la VM par la CD


La CI/CD gère le déploiement de l'application. Le MLOps gère les modèles de Machine Learning.

Ces deux processus sont séparés : un déploiement applicatif ne provoque ni nouvel entraînement ni activation automatique d'un modèle candidat.

Les workflows CD et MLOps partagent un groupe de concurrence GitHub Actions afin d'éviter deux opérations simultanées sur la VM.

---
Fonctionnement de la CI/CD
1. Déclencher la CI
La CI se déclenche automatiquement lorsqu'un commit est envoyé sur une branche autre que main, notamment lola.

Depuis le PC, dans Git Bash :

git add \<fichiers_modifies>

git commit -m "description des modifications"

git push origin lola

Cette action déclenche le workflow CI sur GitHub Actions.

Le workflow réalise successivement :
1. Installation de Python 3.14 et des dépendances de requirements-dev.txt.
2. Exécution des tests avec pytest -v.
3. Si les tests réussissent sur lola, fusion automatique de cette branche dans dev.
4. Déclenchement d'une nouvelle CI sur dev.
5. Construction de l'image Docker du backend.
6. Publication de l'image sur Docker Hub, avec deux tags :
   - Le SHA du commit.

   - latest.
7. Déclenchement explicite du workflow CD avec le SHA de l'image publiée.
La publication Docker ne suffit pas à elle seule pour considérer le déploiement comme réussi : il faut également vérifier le résultat du workflow CD.
2. Déclencher une CI manuellement
Il est également possible de lancer la CI depuis GitHub :
1. Ouvrir le dépôt Frenchcab-Backend.
2. Aller dans l'onglet Actions.
3. Sélectionner le workflow CI.
4. Cliquer sur Run workflow.
5. Choisir la branche dev.
6. Confirmer le lancement.
Une CI exécutée sur dev teste le code, construit l'image Docker et déclenche la CD si toutes les étapes réussissent.
3. Déploiement automatique avec cd.yml
Après la publication sur Docker Hub, le job build de la CI appelle le workflow CD :

gh workflow run cd.yml \\

  --repo "${{ github.repository }}" \\

  --ref main \\

  -f image_sha="${GITHUB_SHA}"

Le workflow CD utilise workflow_dispatch et reçoit le SHA de l'image à déployer.

Il établit une connexion SSH vers la VM, puis exécute :

cd /home/groupe2/frenchcab

bash ./deploy.sh

Le script deploy.sh effectue notamment :

docker compose pull

docker compose up -d --remove-orphans

docker compose ps backend

La CD vérifie ensuite les routes HTTP :

GET /test

GET /modele/version

La première confirme que le backend répond. La seconde permet de vérifier que l'API du modèle est accessible.

Si une vérification échoue, le workflow CD est signalé en échec.

Le déploiement conserve les fichiers MLOps persistants grâce au volume Docker /ml.
4. Suivre une exécution CI/CD
Depuis GitHub, ouvrir :

Frenchcab-Backend → Actions

Vérifier les exécutions :
Workflow	Résultat attendu
CI sur lola	Tests réussis et fusion vers dev
CI sur dev	Tests, build Docker et publication réussis
Continuous Deployment - Backend	Déploiement sur la VM réussi


En cas d'erreur, consulter les logs du job concerné.

Le workflow CD peut également être lancé manuellement depuis GitHub Actions, à condition de fournir le SHA d'une image Docker déjà publiée.

---
Fonctionnement du MLOps
Le workflow mlops.yml est indépendant de la CI/CD.

Il permet de gérer plusieurs versions du modèle de prédiction de durée des trajets, sans modifier le code applicatif.
Avant le lancement : vérifier la version active sur la VM
Avant de lancer une opération pipeline, vérifier la version actuellement enregistrée sur la VM. La dernière version entraînée n'est pas nécessairement la version active.

Depuis le terminal de la VM :
cd /home/groupe2/frenchcab
docker compose exec -T backend cat /ml/modeles/version_active.json
Exemple :
{
  "version": "v3",
  "precedente": "v2",
  "sha256_actif": "661152b56bbb913d0de75e67b4a4e3e83bd777616b603d959ee8c97c51019cc5",
  "date_activation": "2026-10-26T09:44:48"
}
Le champ version donne la référence à renseigner dans version_actuelle pour une exécution de pipeline. Pour confirmer que l'API utilise effectivement cette version :
curl -i http://127.0.0.1:3001/modele/version
La réponse doit être HTTP/1.1 200 OK et contenir la même version, par exemple {"version":"v3"}. En cas de divergence, ne pas lancer le pipeline avant d'avoir vérifié le backend.

Exemple : si V3 est active et que V5 a déjà été entraînée, utiliser version_actuelle = v3 et version = v5. L'opération comparer permet d'évaluer ces versions sans activation ; l'opération pipeline peut activer V5 si les critères sont remplis.

Première mise en service : si version_active.json n'existe pas encore, suivre la procédure d'initialisation de V1 décrite dans « Activation d'un modèle », plutôt que de chercher une version active.

Attention : lorsque la version de référence indiquée ne correspond pas à la version active, le pipeline s'arrête avec ERREUR : version active différente de la référence. Ne pas modifier manuellement version_active.json pour contourner cette protection.
Lancer le MLOps depuis GitHub Actions
1. Ouvrir Frenchcab-Backend sur GitHub.
2. Aller dans Actions.
3. Sélectionner MLOps - Frenchcab.
4. Cliquer sur Run workflow.
5. Sélectionner la branche main.
6. Choisir l'opération souhaitée.
7. Renseigner la version de référence vérifiée sur la VM et la version candidate déjà créée.
8. Confirmer le lancement.
Les paramètres disponibles sont :
Paramètre	Description	Exemple
operation	Opération MLOps à exécuter	pipeline
version	Version candidate déjà entraînée	v5
version_actuelle	Version active constatée sur la VM (sauf première initialisation)	v3


Opérations disponibles
Opération	Fonction
pipeline	Vérifie les fichiers, compare les modèles, applique les critères de qualité et initialise ou active une version si les conditions sont réunies
verifier	Liste les versions disponibles et affiche la version active
entrainer	Exécute le script d'entraînement sans activation automatique
comparer	Compare les performances de deux versions
initialiser	Initialise V1 lors de la première mise en service
activer	Active explicitement une version après vérification des critères
rollback	Restaure la version précédente


L'opération recommandée pour exécuter la chaîne de validation est pipeline.

Le rollback reste une opération distincte, déclenchée manuellement en cas de besoin.
Déroulement du pipeline MLOps
Lorsqu'on sélectionne pipeline, GitHub Actions exécute automatiquement les étapes suivantes sur la VM :
1. Vérification de la présence des modèles et du fichier d'évaluation.
2. Évaluation des versions sur le même jeu de données.
3. Calcul des MAE et génération du rapport.
4. Vérification du seuil de qualité : MAE ≤ 6 minutes.
5. Comparaison de la MAE du candidat avec celle du modèle de référence.
6. Initialisation de V1 si aucune version n'est active, ou promotion du candidat si les critères sont satisfaits.
7. Redémarrage du backend lorsqu'une version est activée.
8. Vérification de la version chargée par l'API.
La candidate n'est promue automatiquement que si elle est conforme et si sa MAE est inférieure ou égale à celle du modèle de référence.

Lors de la toute première exécution, le pipeline initialise uniquement V1, sans activer immédiatement la candidate.

Le pipeline est automatisé dans son exécution, mais son déclenchement reste manuel avec Run workflow.

---
Arborescence du stockage MLOps
Les fichiers persistants sont stockés sur la VM :

/home/groupe2/frenchcab/ml/

Ils sont accessibles depuis le conteneur Docker sous :

/ml/

Arborescence :

/ml/

└── modeles/

    ├── v1/

    │   ├── model.pkl

    │   ├── metadata.json

    │   └── evaluation_validation.csv

    ├── v2/

    │   ├── model.pkl

    │   ├── metadata.json

    │   └── evaluation_validation.csv

    ├── historique_rapports/

    │   └── ...

    ├── resultats_comparaison.json

    └── version_active.json

Chaque dossier vN conserve un modèle et ses métadonnées.

Le fichier version_active.json indique la version active, la version précédente, ainsi que l'empreinte SHA-256 du modèle actif.

Les scripts d'activation et de rollback mettent à jour cet état sans recopier les fichiers model.pkl.

L'API sélectionne le modèle à partir de cet état et vérifie son empreinte lors du chargement.

---
Évaluation et comparaison — ml/MLO.py
Les modèles sont évalués à partir du jeu indépendant d'avril 2026 :

/raw_data/yellow_tripdata_2026-04.parquet

La comparaison utilise un échantillon reproductible de 100 000 trajets et calcule la MAE en minutes.

Le seuil de qualité est fixé à 6 minutes.

La comparaison est normalement exécutée via l'opération pipeline ou comparer du workflow GitHub Actions.

Pour une exécution directe sur la VM :

cd /home/groupe2/frenchcab

docker compose exec -T backend python -m ml.MLO \\

  --actuelle v1 \\

  --candidate v2 \\

  --seuil 6 \\

  --donnees /raw_data/yellow_tripdata_2026-04.parquet

Le rapport principal est enregistré dans :

/ml/modeles/resultats_comparaison.json

Il contient les versions évaluées, leurs empreintes SHA-256 abrégées, leurs MAE, le nom du jeu de données, le nombre de trajets et le seuil retenu.

Une copie horodatée est également conservée dans historique_rapports/.
Résultats de référence
Lors de la validation du 21 octobre 2026 :
Modèle	Algorithme	MAE	Conformité
V1	Random Forest	4,63 min	Conforme
V2	Random Forest	4,78 min	Conforme


Les deux modèles respectent le seuil de qualité, mais V1 présente une MAE légèrement inférieure.

Le pipeline refuse donc la promotion automatique de V2 selon la règle de performance retenue.

---
Activation d'un modèle — ml/publier_modele.py
L'activation est gérée par le workflow MLOps.

Le script vérifie notamment :
1. L'existence du modèle à activer.
2. Sa présence dans le rapport de comparaison.
3. La correspondance de l'empreinte SHA-256.
4. Le respect du seuil MAE.
5. La cohérence de la version active enregistrée.
Initialisation de V1 dans le conteneur :

docker compose exec -T backend \\

  python -m ml.publier_modele \\

  --version v1 \\

  --initialiser

Activation ultérieure de V2 :

docker compose exec -T backend \\

  python -m ml.publier_modele \\

  --version v2

Ces commandes sont exécutées automatiquement par les opérations correspondantes du workflow MLOps.

Après une activation, le workflow redémarre le backend :

docker compose restart backend

Puis il contrôle la version exposée par l'API.

---
Retour arrière — ml/rollback_modele.py
Le rollback permet de restaurer la version précédemment active sans réentraîner le modèle.

Il lit version_active.json, vérifie la version précédente et met à jour l'état d'activation.

L'opération est accessible depuis GitHub Actions :

Actions → MLOps - Frenchcab → Run workflow → rollback

La commande équivalente sur la VM est :

docker compose exec -T backend \\

  python -m ml.rollback_modele

Le workflow redémarre ensuite le conteneur et vérifie que l'API utilise la version restaurée.

Le rollback ne peut pas être exécuté si aucune version précédente n'est enregistrée.

---
Vérification après activation ou rollback
Après une activation ou un rollback, le workflow contrôle automatiquement GET /modele/version pour s'assurer que FastAPI a bien chargé la version attendue. La même commande curl que dans la vérification préalable permet de refaire ce contrôle manuellement sur la VM. Le chargement du modèle vérifie également la cohérence de son empreinte SHA-256.

---**
Compatibilité développement / production
Variable ou chemin	Utilisation	Valeur sur la VM
ML_DIR	Racine du stockage ML	/ml
MODELS_DIR	Répertoire des versions	/ml/modeles
EVALUATION_DATA_PATH	Fichier Parquet d'évaluation, si utilisé par le script	/raw_data/yellow_tripdata_2026-04.parquet
version_active.json	Référence du modèle actif	/ml/modeles/version_active.json


Les modèles sont stockés indépendamment des images Docker, ce qui permet de mettre à jour le backend sans écraser les fichiers ML.

Les modèles V1 et V2 ont été entraînés avec scikit-learn 1.9.0.

La version de scikit-learn installée dans l'image Docker a été fixée à :

scikit-learn==1.9.0

Les dépendances de développement sont définies dans requirements-dev.txt, qui réutilise celles de production grâce à :

-r requirements.txt

---
Tests automatisés
Les tests de gestion des modèles se trouvent dans :

tests/test_gestion_modele.py

Ils utilisent notamment pytest et tmp_path pour vérifier la logique de gestion des versions avec des fichiers temporaires, sans entraîner de vrais modèles.

Les scénarios comprennent :

- Activation d'une nouvelle version.

- Refus d'un modèle dépassant le seuil MAE.

- Refus d'une empreinte SHA-256 incorrecte.

- Retour arrière vers la version précédente.

- Refus d'un rollback sans version précédente.

- Refus d'un rollback vers un modèle non conforme.

Exécution locale :

python -m pytest tests/test_gestion_modele.py -v

Ces tests sont également exécutés dans le cadre de la CI grâce à la commande :

pytest -v

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