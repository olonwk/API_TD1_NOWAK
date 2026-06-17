"""
Tests pour l'API GraphQL Événements avec pytest + FastAPI TestClient
Lancement : pytest tests/ -v

Notes GraphQL :
- Strawberry convertit snake_case → camelCase dans le schéma GraphQL
  Exemple : capacite_max → capaciteMax, creer_evenement → creerEvenement
- Les erreurs de validation retournent HTTP 200 avec un champ "errors" dans la réponse
- Un objet introuvable retourne HTTP 200 avec data.evenement = null
"""

import pytest
import sys
import os

# Permet d'importer app.py et schema.py depuis le dossier parent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import schema as schema_module
from app import app

from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv()

# Le token est lu depuis .env (API_TOKEN) pour éviter de coder un secret en dur
_bearer = os.getenv("API_TOKEN", "mon_token_secret_123")
HEADERS = {"Authorization": f"Bearer {_bearer}"}
URL = "/graphql"

# Données initiales de référence pour la réinitialisation
INITIAL_DB = [
    {"id": 1, "nom": "Conférence Tech Paris", "lieu": "Paris",    "date": "2025-09-15", "capacite_max": 500, "organisateur": "TechFrance"},
    {"id": 2, "nom": "Hackathon IA",           "lieu": "Lyon",     "date": "2025-10-20", "capacite_max": 100, "organisateur": "DataLab"},
    {"id": 3, "nom": "Forum Data Science",     "lieu": "Bordeaux", "date": "2025-11-05", "capacite_max": 200, "organisateur": "DSBordeaux"},
]


@pytest.fixture(autouse=True)
def reset_db():
    """Réinitialise la base de données et le compteur avant chaque test."""
    schema_module.evenements_db = [dict(e) for e in INITIAL_DB]
    schema_module._next_id = 4
    yield


@pytest.fixture
def client():
    """Fixture : crée un TestClient FastAPI."""
    return TestClient(app)


def gql(client, query: str, headers=None):
    """Helper : envoie une requête GraphQL et retourne la Response."""
    return client.post(URL, json={"query": query}, headers=headers or HEADERS)


# ---------------------------------------------------------------------------
# Tests QUERIES
# ---------------------------------------------------------------------------
class TestQueries:
    def test_lister_evenements(self, client):
        """Query { evenements } → liste des 3 événements initiaux."""
        q = "{ evenements { id nom lieu } }"
        r = gql(client, q)
        assert r.status_code == 200
        data = r.json()["data"]
        assert len(data["evenements"]) == 3

    def test_evenement_par_id(self, client):
        """Query { evenement(id: 1) } → nom correct."""
        q = "{ evenement(id: 1) { nom lieu } }"
        r = gql(client, q)
        assert r.status_code == 200
        assert r.json()["data"]["evenement"]["nom"] == "Conférence Tech Paris"

    def test_evenement_inexistant_retourne_null(self, client):
        """Query { evenement(id: 999) } → null (GraphQL retourne 200 + null)."""
        q = "{ evenement(id: 999) { nom } }"
        r = gql(client, q)
        assert r.status_code == 200
        assert r.json()["data"]["evenement"] is None

    def test_filtre_par_lieu(self, client):
        """Query { evenements(lieu: "Paris") } → uniquement Paris."""
        q = '{ evenements(lieu: "Paris") { nom lieu } }'
        r = gql(client, q)
        assert r.status_code == 200
        resultats = r.json()["data"]["evenements"]
        assert len(resultats) == 1
        assert resultats[0]["lieu"] == "Paris"

    def test_filtre_lieu_aucun_resultat(self, client):
        """Query { evenements(lieu: "Marseille") } → liste vide."""
        q = '{ evenements(lieu: "Marseille") { nom } }'
        r = gql(client, q)
        assert r.status_code == 200
        assert r.json()["data"]["evenements"] == []

    def test_champs_selectionnes(self, client):
        """GraphQL permet de ne demander que certains champs (avantage vs REST)."""
        q = "{ evenements { nom organisateur } }"
        r = gql(client, q)
        assert r.status_code == 200
        e = r.json()["data"]["evenements"][0]
        # Seuls nom et organisateur sont présents
        assert "nom" in e
        assert "organisateur" in e
        assert "lieu" not in e


# ---------------------------------------------------------------------------
# Tests MUTATIONS
# ---------------------------------------------------------------------------
class TestMutations:
    def test_creer_evenement(self, client):
        """Mutation creerEvenement → nouvel événement avec ID assigné."""
        mutation = """
        mutation {
            creerEvenement(evenementInput: {
                nom: "Summit DevOps"
                lieu: "Nantes"
                date: "2025-12-01"
                capaciteMax: 300
                organisateur: "DevOpsNantes"
            }) {
                id
                nom
                capaciteMax
            }
        }
        """
        r = gql(client, mutation)
        assert r.status_code == 200
        e = r.json()["data"]["creerEvenement"]
        assert e["nom"] == "Summit DevOps"
        assert e["capaciteMax"] == 300
        assert e["id"] == 4  # Prochain ID attendu

    def test_creer_evenement_capacite_invalide(self, client):
        """Mutation creerEvenement avec capacité ≤ 0 → champ errors."""
        mutation = """
        mutation {
            creerEvenement(evenementInput: {
                nom: "Test"
                lieu: "Paris"
                date: "2025-12-01"
                capaciteMax: -5
                organisateur: "Org"
            }) { id }
        }
        """
        r = gql(client, mutation)
        assert r.status_code == 200
        assert "errors" in r.json()

    def test_modifier_evenement(self, client):
        """Mutation modifierEvenement → données mises à jour."""
        mutation = """
        mutation {
            modifierEvenement(id: 1, evenementInput: {
                nom: "Conférence Tech Paris 2025"
                lieu: "Paris"
                date: "2025-09-20"
                capaciteMax: 750
                organisateur: "TechFrance"
            }) {
                nom
                capaciteMax
                date
            }
        }
        """
        r = gql(client, mutation)
        assert r.status_code == 200
        e = r.json()["data"]["modifierEvenement"]
        assert e["capaciteMax"] == 750
        assert e["date"] == "2025-09-20"

    def test_modifier_evenement_inexistant(self, client):
        """Mutation modifierEvenement(id: 999) → null."""
        mutation = """
        mutation {
            modifierEvenement(id: 999, evenementInput: {
                nom: "X" lieu: "X" date: "2025-01-01" capaciteMax: 1 organisateur: "X"
            }) { nom }
        }
        """
        r = gql(client, mutation)
        assert r.status_code == 200
        assert r.json()["data"]["modifierEvenement"] is None

    def test_supprimer_evenement(self, client):
        """Mutation supprimerEvenement(id: 1) → success True."""
        mutation = "mutation { supprimerEvenement(id: 1) { success message } }"
        r = gql(client, mutation)
        assert r.status_code == 200
        result = r.json()["data"]["supprimerEvenement"]
        assert result["success"] is True

    def test_supprimer_evenement_inexistant(self, client):
        """Mutation supprimerEvenement(id: 999) → success False."""
        mutation = "mutation { supprimerEvenement(id: 999) { success message } }"
        r = gql(client, mutation)
        assert r.status_code == 200
        result = r.json()["data"]["supprimerEvenement"]
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Tests AUTHENTIFICATION
# ---------------------------------------------------------------------------
class TestAuthentification:
    def test_sans_token(self, client):
        """Requête sans header Authorization → 422 (header manquant)."""
        r = client.post(URL, json={"query": "{ evenements { nom } }"})
        assert r.status_code in [401, 403, 422]

    def test_token_invalide(self, client):
        """Requête avec mauvais token → 403."""
        headers = {"Authorization": "Bearer mauvais_token"}
        r = gql(client, "{ evenements { nom } }", headers=headers)
        assert r.status_code == 403
