# Exercice 2 — Conception de l'API RESTful
## Contexte

API de réservation de salles pour une médiathèque municipale.  
Les usagers peuvent consulter les salles disponibles et réserver des créneaux horaires.

---

## Étape 1 — Modélisation des ressources

### Ressources identifiées

| Ressource | Description |
|---|---|
| `/salles` | Les salles de la médiathèque (nom, capacité, équipement) |
| `/reservations` | Les créneaux réservés (date, heures, usager, salle liée) |

### Relation entre les ressources

Une réservation est une **sous-ressource** d'une salle pour la création :
- Elle ne peut pas exister sans salle parente
- Pour éviter une imbrication trop profonde, on adresse la suppression directement via `/reservations/{id}`

### URLs retenues

| Action | Méthode HTTP | URL |
|---|---|---|
| Lister toutes les salles | `GET` | `/salles` |
| Détail d'une salle | `GET` | `/salles/{salle_id}` |
| Réservations d'une salle | `GET` | `/salles/{salle_id}/reservations` |
| Créer une réservation | `POST` | `/salles/{salle_id}/reservations` |
| Annuler une réservation | `DELETE` | `/reservations/{reservation_id}` |

### Codes HTTP utilisés

| Situation | Code |
|---|---|
| Succès lecture | `200 OK` |
| Création réussie | `201 Created` |
| Annulation réussie | `204 No Content` |
| Ressource introuvable | `404 Not Found` |
| Conflit de créneau | `409 Conflict` |
| Token invalide | `403 Forbidden` |
