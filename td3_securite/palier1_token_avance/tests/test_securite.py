"""Tests TD3 — Palier 1 : Token opaque avec expiration et révocation"""

import sys
import os
sys.modules.pop("app", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timedelta
from app import app, generer_token, tokens_actifs


@pytest.fixture(autouse=True)
def reset_tokens():
    tokens_actifs.clear()
    yield
    tokens_actifs.clear()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Tests unitaires — logique de génération de token
# ---------------------------------------------------------------------------

def test_generer_token_cree_entree_dans_dict():
    token = generer_token("alice")
    assert token in tokens_actifs


def test_token_associe_au_bon_utilisateur():
    token = generer_token("alice")
    assert tokens_actifs[token]["user"] == "alice"


def test_token_a_expiration_future():
    token = generer_token("alice")
    assert tokens_actifs[token]["expire_le"] > datetime.utcnow()


def test_deux_tokens_successifs_sont_differents():
    t1 = generer_token("alice")
    t2 = generer_token("alice")
    assert t1 != t2


def test_token_fait_64_caracteres():
    token = generer_token("alice")
    assert len(token) == 64


# ---------------------------------------------------------------------------
# Tests d'intégration — routes HTTP
# ---------------------------------------------------------------------------

def test_login_retourne_token_et_duree(client):
    r = client.post("/auth/login", json={"username": "alice", "password": "motdepasse123"})
    assert r.status_code == 200
    data = r.get_json()
    assert "token" in data
    assert data["expire_dans_minutes"] == 30


def test_login_mauvais_mot_de_passe(client):
    r = client.post("/auth/login", json={"username": "alice", "password": "mauvais"})
    assert r.status_code == 401


def test_login_utilisateur_inconnu(client):
    r = client.post("/auth/login", json={"username": "inconnu", "password": "x"})
    assert r.status_code == 401


def test_profil_sans_token_renvoie_401(client):
    r = client.get("/profil")
    assert r.status_code == 401


def test_profil_avec_token_valide(client):
    login = client.post("/auth/login", json={"username": "alice", "password": "motdepasse123"})
    token = login.get_json()["token"]
    r = client.get("/profil", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()["utilisateur"] == "alice"


def test_profil_token_bidon_renvoie_403(client):
    r = client.get("/profil", headers={"Authorization": "Bearer token_qui_nexiste_pas"})
    assert r.status_code == 403


def test_logout_revoque_le_token(client):
    login = client.post("/auth/login", json={"username": "alice", "password": "motdepasse123"})
    token = login.get_json()["token"]
    client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    r = client.get("/profil", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_token_expire_renvoie_401_et_est_supprime(client):
    token = generer_token("alice")
    tokens_actifs[token]["expire_le"] = datetime.utcnow() - timedelta(minutes=1)
    r = client.get("/profil", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert token not in tokens_actifs
