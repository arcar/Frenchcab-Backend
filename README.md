# Frenchcab-Backend


## Prérequis
Pour ce projet, les outils suivants doivent être installés :

* Docker Desktop
* Git
* FastAPI
* sqlite3

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
https://github.com/mmorkos-cyber/Frenchcab-Backend.git
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


## Présentation et Reste à faire

### Règles appliquées

Chaque ligne est vérifiée selon les règles suivantes. Une ligne qui en enfreint au moins une est exclue du jeu de données.

| Règle | Condition | Justification |
|---|---|---|
| `date_invalide` | Date de prise en charge ou de dépose manquante | Impossible de calculer la durée du trajet |
| `hors_periode` | Trajet en dehors de la période couverte par le fichier | Donnée incohérente avec la source |
| `duree_negative_ou_nulle` | Durée du trajet ≤ 0 minute | Erreur de saisie ou d'horodatage |
| `duree_sup_5h` | Durée du trajet > 300 minutes | Valeur aberrante pour une course en taxi |
| `distance_nulle_ou_aberrante` | Distance ≤ 0 ou > 300 miles | Course non effectuée ou erreur de compteur |
| `montant_negatif_ou_nul` | Tarif (`fare_amount`) ou montant total (`total_amount`) ≤ 0 | Remboursement, annulation ou erreur |
| `montant_aberrant` | Montant total > 1 000 $ | Valeur aberrante |

### Gestion des valeurs manquantes restantes

Après application des règles, certaines colonnes contenaient encore des valeurs manquantes (NaN) sur plusieurs colonnes à la fois. Ces valeurs ont été **remplacées par une valeur par défaut** plutôt que supprimées, pour la raison suivante :

- ces colonnes n'ont pas d'impact direct sur les prédictions ;
- en revanche, les autres colonnes de ces mêmes lignes sont, elles, nécessaires à la prédiction.

Supprimer toutes les lignes contenant un NaN aurait donc entraîné une perte importante de données utiles au modèle.