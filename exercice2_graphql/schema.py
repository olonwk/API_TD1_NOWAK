"""
Schéma GraphQL - Gestion d'événements
Module ECHE834 - Exercice 2B
Réimplémentation du domaine REST en GraphQL avec Strawberry
"""

import re
import strawberry
from typing import Optional, List


# ---------------------------------------------------------------------------
# TYPES GraphQL
# Les types définissent la structure des données exposées par l'API.
# Strawberry convertit automatiquement snake_case → camelCase dans le schéma.
# Exemple : capacite_max (Python) → capaciteMax (GraphQL)
# ---------------------------------------------------------------------------

@strawberry.type
class Evenement:
    """Représente un événement dans notre système."""
    id: int
    nom: str
    lieu: str
    date: str
    capacite_max: int
    organisateur: str


@strawberry.input
class EvenementInput:
    """Données d'entrée pour créer ou modifier un événement."""
    nom: str
    lieu: str
    date: str
    capacite_max: int
    organisateur: str


@strawberry.type
class DeleteResult:
    """Résultat d'une opération de suppression."""
    success: bool
    message: str


# ---------------------------------------------------------------------------
# BASE DE DONNÉES EN MÉMOIRE
# ---------------------------------------------------------------------------

evenements_db: List[dict] = [
    {"id": 1, "nom": "Conférence Tech Paris", "lieu": "Paris",    "date": "2025-09-15", "capacite_max": 500, "organisateur": "TechFrance"},
    {"id": 2, "nom": "Hackathon IA",           "lieu": "Lyon",     "date": "2025-10-20", "capacite_max": 100, "organisateur": "DataLab"},
    {"id": 3, "nom": "Forum Data Science",     "lieu": "Bordeaux", "date": "2025-11-05", "capacite_max": 200, "organisateur": "DSBordeaux"},
]
_next_id = 4


def _dict_to_evenement(d: dict) -> Evenement:
    """Convertit un dictionnaire de la DB en objet Evenement Strawberry."""
    return Evenement(
        id=d["id"],
        nom=d["nom"],
        lieu=d["lieu"],
        date=d["date"],
        capacite_max=d["capacite_max"],
        organisateur=d["organisateur"],
    )


# ---------------------------------------------------------------------------
# QUERIES — Lecture de données (équivalent GET en REST)
# ---------------------------------------------------------------------------

@strawberry.type
class Query:

    @strawberry.field(description="Retourne tous les événements. Filtre optionnel par lieu.")
    def evenements(self, lieu: Optional[str] = None) -> List[Evenement]:
        if lieu:
            return [_dict_to_evenement(e) for e in evenements_db
                    if lieu.lower() in e["lieu"].lower()]
        return [_dict_to_evenement(e) for e in evenements_db]

    @strawberry.field(description="Retourne un événement par son identifiant, ou null s'il est introuvable.")
    def evenement(self, id: int) -> Optional[Evenement]:
        e = next((e for e in evenements_db if e["id"] == id), None)
        return _dict_to_evenement(e) if e else None


# ---------------------------------------------------------------------------
# MUTATIONS — Modification de données (équivalent POST/PUT/DELETE en REST)
# ---------------------------------------------------------------------------

@strawberry.type
class Mutation:

    @strawberry.mutation(description="Crée un nouvel événement. Lève une ValueError si les données sont invalides.")
    def creer_evenement(self, evenement_input: EvenementInput) -> Evenement:
        global _next_id

        # Validation des données d'entrée
        if evenement_input.capacite_max <= 0:
            raise ValueError("La capacité maximale doit être un entier strictement positif")
        if not evenement_input.nom.strip():
            raise ValueError("Le nom de l'événement ne peut pas être vide")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", evenement_input.date):
            raise ValueError("La date doit être au format YYYY-MM-DD")

        nouveau = {
            "id": _next_id,
            "nom": evenement_input.nom.strip(),
            "lieu": evenement_input.lieu.strip(),
            "date": evenement_input.date,
            "capacite_max": evenement_input.capacite_max,
            "organisateur": evenement_input.organisateur.strip(),
        }
        evenements_db.append(nouveau)
        _next_id += 1
        return _dict_to_evenement(nouveau)

    @strawberry.mutation(description="Modifie un événement existant. Retourne null si l'ID est introuvable.")
    def modifier_evenement(self, id: int, evenement_input: EvenementInput) -> Optional[Evenement]:
        e = next((e for e in evenements_db if e["id"] == id), None)
        if e is None:
            return None
        e["nom"] = evenement_input.nom.strip()
        e["lieu"] = evenement_input.lieu.strip()
        e["date"] = evenement_input.date
        e["capacite_max"] = evenement_input.capacite_max
        e["organisateur"] = evenement_input.organisateur.strip()
        return _dict_to_evenement(e)

    @strawberry.mutation(description="Supprime un événement. Retourne success=True si supprimé, False sinon.")
    def supprimer_evenement(self, id: int) -> DeleteResult:
        global evenements_db
        avant = len(evenements_db)
        evenements_db = [e for e in evenements_db if e["id"] != id]
        if len(evenements_db) < avant:
            return DeleteResult(success=True, message=f"Événement {id} supprimé avec succès")
        return DeleteResult(success=False, message=f"Événement {id} introuvable")


# ---------------------------------------------------------------------------
# SCHÉMA final — combine Query et Mutation
# ---------------------------------------------------------------------------

schema = strawberry.Schema(query=Query, mutation=Mutation)
