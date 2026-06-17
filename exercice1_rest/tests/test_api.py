"""
Tests unitaires et d'intégration pour l'API REST Événements
Lancement : pytest tests/ -v
"""

import pytest
import sys
import os
from dotenv import load_dotenv

# Permet d'importer app.py depuis le dossier parent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as app_module
from app import app

load_dotenv()

# Le token est lu depuis .env (API_TOKEN) pour éviter de coder un secret en dur
_bearer = os.getenv("API_TOKEN", "mon_token_secret_123")
HEADERS_OK  = {"Authorization": f"Bearer {_bearer}"}
HEADERS_BAD = {"Authorization": "Bearer mauvais_token"}

# Données initiales de référence pour la réinitialisation
INITIAL_DB = [
    {"id": 1, "nom": "Conférence Tech Paris", "lieu": "Paris",    "date": "2025-09-15", "capacite_max": 500, "organisateur": "TechFrance"},
    {"id": 2, "nom": "Hackathon IA",           "lieu": "Lyon",     "date": "2025-10-20", "capacite_max": 100, "organisateur": "DataLab"},
    {"id": 3, "nom": "Forum Data Science",     "lieu": "Bordeaux", "date": "2025-11-05", "capacite_max": 200, "organisateur": "DSBordeaux"},
]


@pytest.fixture(autouse=True)
def reset_db():
    """Réinitialise la base de données et le compteur avant chaque test."""
    app_module.evenements_db = [dict(e) for e in INITIAL_DB]
    app_module.next_id = 4
    yield


@pytest.fixture
def client():
    """Fixture : crée un client de test Flask."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# Tests GET
# ---------------------------------------------------------------------------
class TestGetEvenements:
    def test_get_tous_les_evenements(self, client):
        """GET /evenements → 200 + liste non vide."""
        r = client.get("/evenements", headers=HEADERS_OK)
        assert r.status_code == 200
        data = r.get_json()
        assert "evenements" in data
        assert data["total"] == 3

    def test_get_evenement_par_id(self, client):
        """GET /evenements/1 → 200 + nom correct."""
        r = client.get("/evenements/1", headers=HEADERS_OK)
        assert r.status_code == 200
        assert r.get_json()["nom"] == "Conférence Tech Paris"

    def test_get_evenement_inexistant(self, client):
        """GET /evenements/999 → 404."""
        r = client.get("/evenements/999", headers=HEADERS_OK)
        assert r.status_code == 404

    def test_get_sans_token(self, client):
        """GET /evenements sans header Authorization → 401."""
        r = client.get("/evenements")
        assert r.status_code == 401

    def test_get_mauvais_token(self, client):
        """GET /evenements avec token incorrect → 403."""
        r = client.get("/evenements", headers=HEADERS_BAD)
        assert r.status_code == 403

    def test_filtre_par_lieu(self, client):
        """GET /evenements?lieu=Paris → résultats filtrés."""
        r = client.get("/evenements?lieu=Paris", headers=HEADERS_OK)
        assert r.status_code == 200
        data = r.get_json()
        assert data["total"] == 1
        assert all("Paris" in e["lieu"] for e in data["evenements"])

    def test_filtre_par_lieu_insensible_casse(self, client):
        """GET /evenements?lieu=paris → filtre insensible à la casse."""
        r = client.get("/evenements?lieu=paris", headers=HEADERS_OK)
        assert r.status_code == 200
        assert r.get_json()["total"] == 1

    def test_filtre_aucun_resultat(self, client):
        """GET /evenements?lieu=Marseille → liste vide."""
        r = client.get("/evenements?lieu=Marseille", headers=HEADERS_OK)
        assert r.status_code == 200
        assert r.get_json()["total"] == 0


# ---------------------------------------------------------------------------
# Tests POST
# ---------------------------------------------------------------------------
class TestCreateEvenement:
    def test_creer_evenement_valide(self, client):
        """POST /evenements avec données valides → 201 + objet créé."""
        payload = {
            "nom": "Summit DevOps",
            "lieu": "Nantes",
            "date": "2025-12-01",
            "capacite_max": 300,
            "organisateur": "DevOpsNantes",
        }
        r = client.post("/evenements", json=payload, headers=HEADERS_OK)
        assert r.status_code == 201
        e = r.get_json()
        assert e["nom"] == "Summit DevOps"
        assert e["lieu"] == "Nantes"
        assert "id" in e

    def test_creer_evenement_champ_manquant(self, client):
        """POST /evenements sans 'lieu' → 400."""
        payload = {"nom": "Test", "date": "2025-12-01", "capacite_max": 50, "organisateur": "Org"}
        r = client.post("/evenements", json=payload, headers=HEADERS_OK)
        assert r.status_code == 400

    def test_creer_evenement_capacite_invalide(self, client):
        """POST /evenements avec capacité négative → 400."""
        payload = {"nom": "Test", "lieu": "Paris", "date": "2025-12-01", "capacite_max": -10, "organisateur": "Org"}
        r = client.post("/evenements", json=payload, headers=HEADERS_OK)
        assert r.status_code == 400

    def test_creer_evenement_capacite_zero(self, client):
        """POST /evenements avec capacité = 0 → 400."""
        payload = {"nom": "Test", "lieu": "Paris", "date": "2025-12-01", "capacite_max": 0, "organisateur": "Org"}
        r = client.post("/evenements", json=payload, headers=HEADERS_OK)
        assert r.status_code == 400

    def test_creer_evenement_date_invalide(self, client):
        """POST /evenements avec date mal formatée → 400."""
        payload = {"nom": "Test", "lieu": "Paris", "date": "01/12/2025", "capacite_max": 100, "organisateur": "Org"}
        r = client.post("/evenements", json=payload, headers=HEADERS_OK)
        assert r.status_code == 400

    def test_creer_evenement_sans_json(self, client):
        """POST /evenements sans Content-Type JSON → 400."""
        r = client.post("/evenements", data="pas du json", headers=HEADERS_OK)
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Tests PUT
# ---------------------------------------------------------------------------
class TestUpdateEvenement:
    def test_modifier_evenement(self, client):
        """PUT /evenements/1 → 200 + données mises à jour."""
        payload = {
            "nom": "Conférence Tech Paris 2025",
            "lieu": "Paris",
            "date": "2025-09-20",
            "capacite_max": 600,
            "organisateur": "TechFrance",
        }
        r = client.put("/evenements/1", json=payload, headers=HEADERS_OK)
        assert r.status_code == 200
        e = r.get_json()
        assert e["capacite_max"] == 600
        assert e["date"] == "2025-09-20"

    def test_modifier_evenement_inexistant(self, client):
        """PUT /evenements/999 → 404."""
        payload = {"nom": "X", "lieu": "Paris", "date": "2025-01-01", "capacite_max": 10, "organisateur": "X"}
        r = client.put("/evenements/999", json=payload, headers=HEADERS_OK)
        assert r.status_code == 404

    def test_modifier_sans_token(self, client):
        """PUT /evenements/1 sans token → 401."""
        payload = {"nom": "X", "lieu": "Paris", "date": "2025-01-01", "capacite_max": 10, "organisateur": "X"}
        r = client.put("/evenements/1", json=payload)
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Tests DELETE
# ---------------------------------------------------------------------------
class TestDeleteEvenement:
    def test_supprimer_evenement(self, client):
        """DELETE /evenements/1 → 204 + événement absent ensuite."""
        r = client.delete("/evenements/1", headers=HEADERS_OK)
        assert r.status_code == 204
        # Vérification : l'événement n'existe plus
        r2 = client.get("/evenements/1", headers=HEADERS_OK)
        assert r2.status_code == 404

    def test_supprimer_evenement_inexistant(self, client):
        """DELETE /evenements/999 → 404."""
        r = client.delete("/evenements/999", headers=HEADERS_OK)
        assert r.status_code == 404

    def test_supprimer_sans_token(self, client):
        """DELETE /evenements/1 sans token → 401."""
        r = client.delete("/evenements/1")
        assert r.status_code == 401
