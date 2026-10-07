# Contexte
Ce fichier vise à définir les rêgle de contribution collaboratives dans le cadre du projet "Frenchcab".


## Branches

Les branches devront suivrent cet appelation et devront tous être écris en miniscule sans ponctuation: 

```:nom:```  (example:  ```ursula```)

## 3. Stratégie de branches

| Branche | Rôle | CI/CD |
|---|---|---|
| `main` | Code prêt pour la production | Aucun pipeline, mise à jour par pull request depuis `dev` |
| `dev` | Version de développement, déployée sur la VM | Tests, puis build et push de l'image sur Docker Hub |
| `:nom:` | Branche perso de chaque membre | Tests, puis merge automatique dans `dev` si les tests passent |

Un push sur votre branche perso lance les tests. S'ils passent, la branche est mergée automatiquement dans `dev`, qui est retestée puis buildée et poussée sur Docker Hub. S'ils échouent (ou en cas de conflit avec `dev`), rien n'est mergé : corrigez puis repoussez.

## Commits
Les commits devront être précédés de ces balises et devront tous être écris en miniscule sans ponctuation :

```<feat>``` ```<fix>``` ```<docs>``` ```<chores>```

### Règles

- Ne jamais pousser directement sur `main` ou `dev`. Les modifications arrivent sur `dev` par le merge automatique de votre branche perso, et sur `main` par pull request.
- Chaque push sur votre branche distante devra être précédé d'un pull de la branche de développement principale (```dev```), pour éviter les conflits lors du merge automatique.
- L'intégrateur' est à la charge de s'assurer de la santé de la branche de développement principale (```dev```) ainsi que la branche ```main```.



## Rôles

| Personne | Rôle | Sprint(s) |
| --- | --- | --- |
| Mario | ETL, gateway |  |
| Lola | Pipeline CI/CD, Docker |  |
| Ursula | ETL | |
| Clement | Angular |  |