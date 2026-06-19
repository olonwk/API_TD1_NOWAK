#!/usr/bin/env python3
"""TD3 — Palier 1 : Token opaque avec expiration et révocation (Flask)

Principe : le serveur génère un token aléatoire (64 hex = 256 bits),
le stocke côté serveur avec une TTL. La révocation est immédiate
(suppression du dict) mais ne fonctionne qu'avec un seul processus.
"""

import secrets
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, abort

app = Flask(__name__)

utilisateurs_db = {
    "alice": "motdepasse123",
    "bob": "secret456",
}

# Dict en mémoire : token → {user, expire_le}
tokens_actifs: dict = {}

DUREE_TOKEN_MINUTES = 30


def generer_token(username: str) -> str:
    token = secrets.token_hex(32)
    tokens_actifs[token] = {
        "user": username,
        "expire_le": datetime.utcnow() + timedelta(minutes=DUREE_TOKEN_MINUTES),
    }
    return token


def verifier_token() -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        abort(401, description="Token manquant ou mal formé")
    token = auth_header.split(" ", 1)[1]
    if token not in tokens_actifs:
        abort(403, description="Token invalide ou révoqué")
    info = tokens_actifs[token]
    if info["expire_le"] < datetime.utcnow():
        del tokens_actifs[token]
        abort(401, description="Token expiré")
    return info["user"]


@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"erreur": str(e.description)}), 401


@app.errorhandler(403)
def forbidden(e):
    return jsonify({"erreur": str(e.description)}), 403


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"erreur": "Identifiants manquants"}), 400
    if utilisateurs_db.get(username) != password:
        abort(401, description="Identifiants invalides")
    token = generer_token(username)
    return jsonify({
        "token": token,
        "expire_dans_minutes": DUREE_TOKEN_MINUTES,
    }), 200


@app.route("/auth/logout", methods=["POST"])
def logout():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        tokens_actifs.pop(token, None)
    return "", 204


@app.route("/profil", methods=["GET"])
def profil():
    username = verifier_token()
    return jsonify({"utilisateur": username}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5001)
