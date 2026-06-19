#!/usr/bin/env python3
"""TD3 — Palier 2 : Authentification JWT avec python-jose (Flask)

Structure d'un JWT : header.payload.signature (base64url encodé)
  - header  : {"alg": "HS256", "typ": "JWT"}
  - payload : {"sub": "alice", "exp": <timestamp>, "iat": <timestamp>}
  - signature : HMAC-SHA256(header + "." + payload, SECRET_KEY)

Avantage sur palier 1 : aucun stockage serveur, scalable.
Limite : révocation avant expiration impossible sans liste noire.
"""

from datetime import datetime, timedelta
from flask import Flask, jsonify, request, abort
from jose import jwt, JWTError

app = Flask(__name__)

SECRET_KEY = "cle-secrete-a-changer-en-production"
ALGORITHM = "HS256"
DUREE_TOKEN_MINUTES = 30

utilisateurs_db = {
    "alice": "motdepasse123",
    "bob": "secret456",
}


def creer_jwt(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(minutes=DUREE_TOKEN_MINUTES),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verifier_jwt() -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        abort(401, description="Token JWT manquant")
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        abort(401, description="Token JWT invalide ou expiré")


@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"erreur": str(e.description)}), 401


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if not username or utilisateurs_db.get(username) != password:
        abort(401, description="Identifiants invalides")
    return jsonify({
        "access_token": creer_jwt(username),
        "token_type": "bearer",
    }), 200


@app.route("/profil", methods=["GET"])
def profil():
    username = verifier_jwt()
    return jsonify({"utilisateur": username}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5002)
