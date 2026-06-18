"""Tests de l'API Médiathèque — Exercice 2 TD2 (Étape 5)"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, salles_db, reservations_db

client = TestClient(app)
HEADERS = {"Authorization": "Bearer mon_token_secret_123"}
HEADERS_INVALIDE = {"Authorization": "Bearer mauvais_token"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_db():
    """Remet la base en mémoire dans son état initial avant chaque test."""
    salles_db.clear()
    salles_db.extend([
        {"id": 1, "nom": "Salle Voltaire", "capacite": 12, "equipement": ["vidéoprojecteur", "tableau blanc"]},
        {"id": 2, "nom": "Salle Curie",    "capacite": 6,  "equipement": ["écran TV"]},
        {"id": 3, "nom": "Salle Hugo",     "capacite": 20, "equipement": ["vidéoprojecteur", "système audio"]},
    ])
    reservations_db.clear()
    reservations_db.append(
        {"id": 1, "salle_id": 1, "usager": "M. Dupont",
         "date": "2026-06-20", "heure_debut": "14:00", "heure_fin": "15:30"}
    )
    import app as app_module
    app_module.next_reservation_id = 2
    yield


# ---------------------------------------------------------------------------
# Tests — Authentification
# ---------------------------------------------------------------------------

def test_auth_token_invalide():
    r = client.get("/salles", headers=HEADERS_INVALIDE)
    assert r.status_code == 403

def test_auth_sans_token():
    r = client.get("/salles")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Tests — GET /salles
# ---------------------------------------------------------------------------

def test_get_salles_retourne_liste():
    r = client.get("/salles", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 3

def test_get_salle_existante():
    r = client.get("/salles/1", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["nom"] == "Salle Voltaire"

def test_get_salle_inexistante():
    r = client.get("/salles/999", headers=HEADERS)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests — GET /salles/{id}/reservations
# ---------------------------------------------------------------------------

def test_get_reservations_salle_existante():
    r = client.get("/salles/1/reservations", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["usager"] == "M. Dupont"

def test_get_reservations_salle_vide():
    r = client.get("/salles/2/reservations", headers=HEADERS)
    assert r.status_code == 200
    assert r.json() == []

def test_get_reservations_salle_inexistante():
    r = client.get("/salles/999/reservations", headers=HEADERS)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tests — POST /salles/{id}/reservations
# ---------------------------------------------------------------------------

RESA_VALIDE = {
    "usager": "Mme Martin",
    "date": "2026-06-21",
    "heure_debut": "10:00",
    "heure_fin": "11:30",
}

def test_creer_reservation_valide():
    r = client.post("/salles/1/reservations", json=RESA_VALIDE, headers=HEADERS)
    assert r.status_code == 201
    data = r.json()
    assert data["usager"] == "Mme Martin"
    assert data["salle_id"] == 1

def test_creer_reservation_salle_inexistante():
    r = client.post("/salles/999/reservations", json=RESA_VALIDE, headers=HEADERS)
    assert r.status_code == 404

def test_creer_reservation_conflit_creneau():
    # Même salle, même date, créneau qui chevauche la réservation existante (14:00-15:30)
    resa_en_conflit = {
        "usager": "Mme Durand",
        "date": "2026-06-20",
        "heure_debut": "15:00",
        "heure_fin": "16:00",
    }
    r = client.post("/salles/1/reservations", json=resa_en_conflit, headers=HEADERS)
    assert r.status_code == 409

def test_creer_reservation_sans_conflit_meme_jour():
    # Même salle, même date, mais créneau qui NE chevauche PAS
    resa_ok = {
        "usager": "M. Bernard",
        "date": "2026-06-20",
        "heure_debut": "16:00",
        "heure_fin": "17:00",
    }
    r = client.post("/salles/1/reservations", json=resa_ok, headers=HEADERS)
    assert r.status_code == 201

def test_creer_reservation_date_invalide():
    resa = {**RESA_VALIDE, "date": "pas-une-date"}
    r = client.post("/salles/1/reservations", json=resa, headers=HEADERS)
    assert r.status_code == 422

def test_creer_reservation_heure_invalide():
    resa = {**RESA_VALIDE, "heure_debut": "25:00"}
    r = client.post("/salles/1/reservations", json=resa, headers=HEADERS)
    assert r.status_code == 422

def test_creer_reservation_heure_fin_avant_debut():
    resa = {**RESA_VALIDE, "heure_debut": "14:00", "heure_fin": "13:00"}
    r = client.post("/salles/1/reservations", json=resa, headers=HEADERS)
    assert r.status_code == 422

def test_creer_reservation_usager_vide():
    resa = {**RESA_VALIDE, "usager": "   "}
    r = client.post("/salles/1/reservations", json=resa, headers=HEADERS)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Tests — DELETE /reservations/{id}
# ---------------------------------------------------------------------------

def test_supprimer_reservation_existante():
    r = client.delete("/reservations/1", headers=HEADERS)
    assert r.status_code == 204

def test_supprimer_reservation_inexistante():
    r = client.delete("/reservations/999", headers=HEADERS)
    assert r.status_code == 404

def test_supprimer_puis_verifier():
    client.delete("/reservations/1", headers=HEADERS)
    r = client.get("/salles/1/reservations", headers=HEADERS)
    assert r.json() == []
