#!/usr/bin/env python3
"""TD3 — Palier 3 : Flux OAuth2 Authorization Code simplifié (Flask)

Flux complet :
  1. GET  /oauth/authorize?client_id=X&redirect_uri=Y&state=Z  → formulaire login
  2. POST /oauth/authorize  (identifiants JSON)                 → code usage unique (5 min)
  3. POST /oauth/token      {code, client_id}                   → access_token (15 min JWT)
                                                                   + refresh_token (7 j, opaque)
  4. POST /oauth/refresh    {refresh_token}                     → nouvel access_token
  5. GET  /profil           Bearer access_token                 → données utilisateur

Séparation access / refresh :
  - access_token court (15 min) : limite la fenêtre d'attaque si intercepté.
  - refresh_token long (7 j), stocké serveur : révocation possible (logout forcé, vol de device).
"""

import secrets
from datetime import datetime, timedelta
from uuid import uuid4
from flask import Flask, jsonify, request, abort
from jose import jwt, JWTError

app = Flask(__name__)

SECRET_KEY = "cle-secrete-oauth2-a-changer"
ALGORITHM = "HS256"
ACCES_TOKEN_MINUTES = 15
REFRESH_TOKEN_JOURS = 7

clients_autorises = {
    "client_app_1": {
        "redirect_uris": ["http://localhost:8080/callback"],
        "nom": "Application Bibliothèque",
    }
}

utilisateurs_db = {
    "alice": "motdepasse123",
    "bob": "secret456",
}

# Codes d'autorisation : code → {user, client_id, redirect_uri, expire_le}
codes_autorisation: dict = {}

# Refresh tokens : token → {user, expire_le}
refresh_tokens_db: dict = {}


def creer_access_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(minutes=ACCES_TOKEN_MINUTES),
        "type": "access",
        "jti": str(uuid4()),  # identifiant unique pour permettre la révocation future
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verifier_access_token() -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        abort(401, description="Access token manquant")
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError("Type de token incorrect")
        return payload["sub"]
    except JWTError:
        abort(401, description="Access token invalide ou expiré")


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"erreur": str(e.description)}), 400


@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"erreur": str(e.description)}), 401


# ---------------------------------------------------------------------------
# Étape 1 & 2 : Autorisation
# ---------------------------------------------------------------------------

@app.route("/oauth/authorize", methods=["GET", "POST"])
def authorize():
    client_id = request.args.get("client_id")
    redirect_uri = request.args.get("redirect_uri")
    state = request.args.get("state", "")

    if client_id not in clients_autorises:
        abort(400, description=f"Client inconnu : {client_id}")
    if redirect_uri not in clients_autorises[client_id]["redirect_uris"]:
        abort(400, description="redirect_uri non autorisé")

    if request.method == "GET":
        return jsonify({
            "message": "Envoyez vos identifiants en POST sur cet endpoint",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }), 200

    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if utilisateurs_db.get(username) != password:
        abort(401, description="Identifiants invalides")

    code = secrets.token_urlsafe(32)
    codes_autorisation[code] = {
        "user": username,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "expire_le": datetime.utcnow() + timedelta(minutes=5),
    }
    return jsonify({
        "code": code,
        "state": state,
        "redirect_uri": f"{redirect_uri}?code={code}&state={state}",
    }), 200


# ---------------------------------------------------------------------------
# Étape 3 : Échange du code contre les tokens
# ---------------------------------------------------------------------------

@app.route("/oauth/token", methods=["POST"])
def token():
    data = request.get_json() or {}
    code = data.get("code")
    client_id = data.get("client_id")

    if not code or code not in codes_autorisation:
        abort(400, description="Code d'autorisation invalide ou déjà utilisé")

    info = codes_autorisation.pop(code)  # usage unique

    if info["expire_le"] < datetime.utcnow():
        abort(400, description="Code d'autorisation expiré")
    if info["client_id"] != client_id:
        abort(400, description="client_id ne correspond pas au code")

    username = info["user"]
    access_token = creer_access_token(username)
    refresh_token = secrets.token_urlsafe(48)
    refresh_tokens_db[refresh_token] = {
        "user": username,
        "expire_le": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_JOURS),
    }

    return jsonify({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCES_TOKEN_MINUTES * 60,
        "refresh_token": refresh_token,
    }), 200


# ---------------------------------------------------------------------------
# Étape 4 : Renouvellement de l'access token
# ---------------------------------------------------------------------------

@app.route("/oauth/refresh", methods=["POST"])
def refresh():
    data = request.get_json() or {}
    refresh_token = data.get("refresh_token")

    if not refresh_token or refresh_token not in refresh_tokens_db:
        abort(401, description="Refresh token invalide ou révoqué")

    info = refresh_tokens_db[refresh_token]
    if info["expire_le"] < datetime.utcnow():
        del refresh_tokens_db[refresh_token]
        abort(401, description="Refresh token expiré")

    return jsonify({
        "access_token": creer_access_token(info["user"]),
        "token_type": "bearer",
        "expires_in": ACCES_TOKEN_MINUTES * 60,
    }), 200


# ---------------------------------------------------------------------------
# Ressource protégée
# ---------------------------------------------------------------------------

@app.route("/profil", methods=["GET"])
def profil():
    username = verifier_access_token()
    return jsonify({"utilisateur": username}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5003)
