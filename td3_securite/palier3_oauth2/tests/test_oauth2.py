"""Tests TD3 — Palier 3 : Flux OAuth2 Authorization Code

Teste chaque étape du flux isolément, puis le flux complet bout-en-bout.
"""

import sys
import os
sys.modules.pop("app", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timedelta
from jose import jwt as jose_jwt
from app import (
    app, creer_access_token,
    codes_autorisation, refresh_tokens_db,
    SECRET_KEY, ALGORITHM,
)

BASE_ARGS = "?client_id=client_app_1&redirect_uri=http://localhost:8080/callback&state=test"


@pytest.fixture(autouse=True)
def reset_state():
    codes_autorisation.clear()
    refresh_tokens_db.clear()
    yield
    codes_autorisation.clear()
    refresh_tokens_db.clear()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def obtenir_code(client, username="alice", password="motdepasse123"):
    r = client.post(
        f"/oauth/authorize{BASE_ARGS}",
        json={"username": username, "password": password},
    )
    assert r.status_code == 200
    return r.get_json()["code"]


def obtenir_tokens(client, code):
    r = client.post("/oauth/token", json={"code": code, "client_id": "client_app_1"})
    assert r.status_code == 200
    return r.get_json()


# ---------------------------------------------------------------------------
# Tests — Étape 1 & 2 : /oauth/authorize
# ---------------------------------------------------------------------------

def test_authorize_get_retourne_invite_login(client):
    r = client.get(f"/oauth/authorize{BASE_ARGS}")
    assert r.status_code == 200
    assert "message" in r.get_json()


def test_authorize_post_retourne_code_usage_unique(client):
    r = client.post(
        f"/oauth/authorize{BASE_ARGS}",
        json={"username": "alice", "password": "motdepasse123"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "code" in data
    assert data["code"] in codes_autorisation


def test_authorize_code_stocke_bon_utilisateur(client):
    code = obtenir_code(client)
    assert codes_autorisation[code]["user"] == "alice"


def test_authorize_code_expire_dans_5_minutes(client):
    code = obtenir_code(client)
    expire = codes_autorisation[code]["expire_le"]
    assert expire > datetime.utcnow()
    assert expire < datetime.utcnow() + timedelta(minutes=6)


def test_authorize_mauvais_identifiants(client):
    r = client.post(
        f"/oauth/authorize{BASE_ARGS}",
        json={"username": "alice", "password": "faux"},
    )
    assert r.status_code == 401


def test_authorize_client_inconnu(client):
    r = client.post(
        "/oauth/authorize?client_id=inconnu&redirect_uri=http://localhost:8080/callback",
        json={"username": "alice", "password": "motdepasse123"},
    )
    assert r.status_code == 400


def test_authorize_redirect_uri_non_autorise(client):
    r = client.post(
        "/oauth/authorize?client_id=client_app_1&redirect_uri=http://evil.com",
        json={"username": "alice", "password": "motdepasse123"},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Tests — Étape 3 : /oauth/token
# ---------------------------------------------------------------------------

def test_token_retourne_access_et_refresh(client):
    tokens = obtenir_tokens(client, obtenir_code(client))
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 15 * 60


def test_access_token_est_un_jwt_valide(client):
    tokens = obtenir_tokens(client, obtenir_code(client))
    payload = jose_jwt.decode(tokens["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "alice"
    assert payload["type"] == "access"


def test_code_usage_unique_deuxieme_appel_rejete(client):
    code = obtenir_code(client)
    obtenir_tokens(client, code)
    r = client.post("/oauth/token", json={"code": code, "client_id": "client_app_1"})
    assert r.status_code == 400


def test_token_code_invalide(client):
    r = client.post("/oauth/token", json={"code": "code_bidon", "client_id": "client_app_1"})
    assert r.status_code == 400


def test_token_mauvais_client_id(client):
    code = obtenir_code(client)
    r = client.post("/oauth/token", json={"code": code, "client_id": "mauvais_client"})
    assert r.status_code == 400


def test_token_code_expire_rejete(client):
    code = obtenir_code(client)
    codes_autorisation[code]["expire_le"] = datetime.utcnow() - timedelta(minutes=1)
    r = client.post("/oauth/token", json={"code": code, "client_id": "client_app_1"})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Tests — Étape 4 : /oauth/refresh
# ---------------------------------------------------------------------------

def test_refresh_retourne_nouvel_access_token(client):
    tokens = obtenir_tokens(client, obtenir_code(client))
    r = client.post("/oauth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    data = r.get_json()
    assert "access_token" in data
    assert data["access_token"] != tokens["access_token"]


def test_refresh_token_invalide_rejete(client):
    r = client.post("/oauth/refresh", json={"refresh_token": "bidon"})
    assert r.status_code == 401


def test_refresh_token_expire_rejete(client):
    tokens = obtenir_tokens(client, obtenir_code(client))
    rt = tokens["refresh_token"]
    refresh_tokens_db[rt]["expire_le"] = datetime.utcnow() - timedelta(days=1)
    r = client.post("/oauth/refresh", json={"refresh_token": rt})
    assert r.status_code == 401
    assert rt not in refresh_tokens_db


# ---------------------------------------------------------------------------
# Tests — Ressource protégée /profil
# ---------------------------------------------------------------------------

def test_profil_avec_access_token_valide(client):
    tokens = obtenir_tokens(client, obtenir_code(client))
    r = client.get("/profil", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 200
    assert r.get_json()["utilisateur"] == "alice"


def test_profil_sans_token_rejete(client):
    r = client.get("/profil")
    assert r.status_code == 401


def test_profil_avec_refresh_token_rejete(client):
    """Un refresh token opaque ne doit pas être accepté comme access token."""
    tokens = obtenir_tokens(client, obtenir_code(client))
    r = client.get("/profil", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert r.status_code == 401


def test_profil_access_token_expire_rejete(client):
    payload = {"sub": "alice", "exp": datetime.utcnow() - timedelta(minutes=1), "type": "access"}
    expired = jose_jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    r = client.get("/profil", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Test bout-en-bout — flux OAuth2 complet
# ---------------------------------------------------------------------------

def test_flux_oauth2_complet(client):
    """Simule le flux entier : authorize → token → profil → refresh → profil."""
    # 1. Obtenir le code
    code = obtenir_code(client, "bob", "secret456")
    assert code in codes_autorisation

    # 2. Échanger contre des tokens
    r_token = client.post("/oauth/token", json={"code": code, "client_id": "client_app_1"})
    assert r_token.status_code == 200
    tokens = r_token.get_json()

    # 3. Accéder à la ressource protégée
    r_profil = client.get("/profil", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r_profil.status_code == 200
    assert r_profil.get_json()["utilisateur"] == "bob"

    # 4. Rafraîchir l'access token
    r_refresh = client.post("/oauth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r_refresh.status_code == 200
    new_access = r_refresh.get_json()["access_token"]

    # 5. Utiliser le nouvel access token
    r_profil2 = client.get("/profil", headers={"Authorization": f"Bearer {new_access}"})
    assert r_profil2.status_code == 200
    assert r_profil2.get_json()["utilisateur"] == "bob"
