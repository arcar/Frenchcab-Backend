# Contexte
Ce fichier vise à définir les rêgle de contribution collaboratives dans le cadre du projet "Frenchcab".


## Branches

Les branches devront suivrent cet appelation et devront tous être écris en miniscule sans ponctuation: 

```:nom:```  (example:  ```ursula```)

## 3. Stratégie de branches

| Branche | Rôle | CI/CD |
|---|---|---|
| `main` | Code prêt pour la production | Déclenche le pipeline |
| `dev` | Version de développement, déployée pour les tests | Déclenche le pipeline |
| `staging` | Branche d'intégration : on regroupe et on teste les fonctionnalités ensemble avant de les envoyer sur `dev` | Pas de pipeline |

## Commits
Les commits devront être précédés de ces balises et devront tous être écris en miniscule sans ponctuation :

```<feat>``` ```<fix>``` ```<docs>``` ```<chores>```

### Règles

- Ne jamais pousser directement sur `main` ou `dev`. Les modifications arrivent uniquement par des pull requests.
- Chaque push sur votre branche distante devra être précédé d'un pull de la branche de développement principale (```staging```).
- L'intégrateur' est à la charge de s'assurer de la santé de la branche de développement principale (```dev```) ainsi que la branche ```main```.



## Rôles

| Personne | Rôle | Sprint(s) |
| --- | --- | --- |
| Mario | ETL, gateway |  |
| Lola | Pipeline CI/CD, Docker |  |
| Ursula | ETL | |
| Clement | Angular |  |