"""Tests TD3 — Palier 2 : JWT signé HS256

Tests unitaires sur la structure et la validation du JWT,
tests d'intégration via les routes Flask.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError
from app import app, creer_jwt, SECRET_KEY, ALGORITHM


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Tests unitaires — structure et validation du JWT
# ---------------------------------------------------------------------------

def test_jwt_contient_trois_parties_separees_par_des_points():
    token = creer_jwt("alice")
    assert token.count(".") == 2


def test_payload_claim_sub_correct():
    token = creer_jwt("alice")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "alice"


def test_payload_claim_exp_dans_le_futur():
    token = creer_jwt("alice")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["exp"] > datetime.utcnow().timestamp()


def test_payload_claim_iat_present():
    token = creer_jwt("alice")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "iat" in payload


def test_mauvaise_cle_de_signature_leve_jwterror():
    token = creer_jwt("alice")
    with pytest.raises(JWTError):
        jwt.decode(token, "mauvaise-cle", algorithms=[ALGORITHM])


def test_token_expire_leve_jwterror():
    payload = {"sub": "alice", "exp": datetime.utcnow() - timedelta(minutes=1)}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(JWTError):
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def test_signature_falsifiee_leve_jwterror():
    token = creer_jwt("alice")
    parties = token.split(".")
    parties[2] = "signaturecorrompu"
    with pytest.raises(JWTError):
        jwt.decode(".".join(parties), SECRET_KEY, algorithms=[ALGORITHM])


def test_payload_falsifie_leve_jwterror():
    """Si on modifie le payload manuellement, la signature ne correspond plus."""
    import base64, json
    token = creer_jwt("alice")
    header, _, signature = token.split(".")
    faux_payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "admin", "exp": 9999999999}).encode()
    ).rstrip(b"=").decode()
    token_falsifie = f"{header}.{faux_payload}.{signature}"
    with pytest.raises(JWTError):
        jwt.decode(token_falsifie, SECRET_KEY, algorithms=[ALGORITHM])


# ---------------------------------------------------------------------------
# Tests d'intégration — routes HTTP
# ---------------------------------------------------------------------------

def test_login_retourne_access_token_et_type(client):
    r = client.post("/auth/login", json={"username": "alice", "password": "motdepasse123"})
    assert r.status_code == 200
    data = r.get_json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_mauvais_mot_de_passe(client):
    r = client.post("/auth/login", json={"username": "alice", "password": "faux"})
    assert r.status_code == 401


def test_profil_avec_jwt_valide(client):
    login = client.post("/auth/login", json={"username": "alice", "password": "motdepasse123"})
    token = login.get_json()["access_token"]
    r = client.get("/profil", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.get_json()["utilisateur"] == "alice"


def test_profil_sans_token_renvoie_401(client):
    r = client.get("/profil")
    assert r.status_code == 401


def test_profil_jwt_bidon_renvoie_401(client):
    r = client.get("/profil", headers={"Authorization": "Bearer token.bidon.ici"})
    assert r.status_code == 401


def test_profil_jwt_expire_renvoie_401(client):
    payload = {"sub": "alice", "exp": datetime.utcnow() - timedelta(minutes=1)}
    token_expire = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    r = client.get("/profil", headers={"Authorization": f"Bearer {token_expire}"})
    assert r.status_code == 401
