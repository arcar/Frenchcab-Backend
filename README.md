# Frenchcab-Backend


# Prérequis
Pour ce projet, les outils suivants doivent être installés :

* Docker Desktop
* Git
* FastAPI
* sqlite3

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