# Palier 3 — OAuth2 : Pourquoi deux tokens ?

## Problème à résoudre

Un seul JWT longue durée pose deux problèmes antagonistes :
- **Trop court** → l'utilisateur doit se ré-authentifier souvent → mauvaise UX.
- **Trop long** → si le token est volé, l'attaquant a un accès durable.

## Solution : la paire access + refresh

| Propriété | Access Token | Refresh Token |
|---|---|---|
| **Format** | JWT signé (HS256) | Opaque (token aléatoire) |
| **Durée de vie** | 15 minutes | 7 jours |
| **Stockage** | Aucun côté serveur | Dict en mémoire (DB en prod) |
| **Envoyé à chaque requête** | Oui (Bearer header) | Non (uniquement sur `/oauth/refresh`) |
| **Révocable immédiatement** | Non (jusqu'à expiration) | Oui (suppression du dict) |

## Flux complet

```
Utilisateur            Serveur OAuth2          Application cliente
     |                       |                          |
     |--- identifiants ----→ |                          |
     |                       |--- code (5 min) -------→ |
     |                       |                          |
     |                       |←-- {code, client_id} ---|
     |                       |--- access + refresh ---→ |
     |                       |                          |
     |                       |←-- Bearer access_token --| (chaque appel API)
     |                       |--- données protégées --→ |
     |                       |                          |
     |                       |  (15 min plus tard)      |
     |                       |←-- refresh_token --------|
     |                       |--- nouvel access_token → |
```

## Pourquoi le code d'autorisation ?

Le code est à **usage unique et très court** (5 min). Il permet de ne pas exposer
les tokens dans l'URL (logs serveur, historique navigateur). L'application cliente
échange le code via un appel serveur-à-serveur, pas via le navigateur.

## Limites de cette implémentation simplifiée

- Les tokens sont stockés **en mémoire** : ils disparaissent au redémarrage.
- En production : utiliser Redis (TTL automatique) ou une table SQL pour les refresh tokens.
- Le formulaire d'autorisation est simulé en JSON : en vrai, c'est une page HTML rendue par le serveur OAuth2.
- PKCE (Proof Key for Code Exchange) n'est pas implémenté — requis pour les clients publics (SPA, mobile).
