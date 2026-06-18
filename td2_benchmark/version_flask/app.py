#!/usr/bin/env python3
"""Benchmark Flask — API réservation de salles (version simplifiée pour comparaison)

Étape 2 TD2 : comparaison Flask vs FastAPI
Critères évalués :
  - Syntaxe et lisibilité
  - Validation des données (manuelle avec Flask)
  - Documentation automatique (absente par défaut avec Flask)
  - Gestion des erreurs HTTP
"""

from flask import Flask, request, jsonify
from datetime import date, time
from functools import wraps

app = Flask(__name__)

API_TOKEN = "mon_token_secret_123"

# --- Données en mémoire ---
salles_db = [
    {"id": 1, "nom": "Salle Voltaire", "capacite": 12, "equipement": ["vidéoprojecteur"]},
    {"id": 2, "nom": "Salle Curie",    "capacite": 6,  "equipement": ["écran TV"]},
]
reservations_db = [
    {"id": 1, "salle_id": 1, "usager": "M. Dupont",
     "date": "2026-06-20", "heure_debut": "14:00", "heure_fin": "15:30"},
]
next_id = 2


# --- Auth manuelle (Flask n'a pas de système intégré) ---
def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "")
        if token != API_TOKEN:
            return jsonify({"erreur": "Accès refusé", "detail": "Token invalide"}), 403
        return f(*args, **kwargs)
    return decorated


# --- Validation manuelle (Flask n'a pas Pydantic) ---
def valider_reservation(data):
    erreurs = []
    for champ in ("usager", "date", "heure_debut", "heure_fin"):
        if champ not in data:
            erreurs.append(f"Champ manquant : {champ}")
    if erreurs:
        return erreurs
    try:
        date.fromisoformat(data["date"])
    except ValueError:
        erreurs.append("date doit être au format YYYY-MM-DD")
    for champ in ("heure_debut", "heure_fin"):
        try:
            time.fromisoformat(data[champ])
        except ValueError:
            erreurs.append(f"{champ} doit être au format HH:MM")
    if not data.get("usager", "").strip():
        erreurs.append("usager ne peut pas être vide")
    if not erreurs and data["heure_fin"] <= data["heure_debut"]:
        erreurs.append("heure_fin doit être postérieure à heure_debut")
    return erreurs


def creneaux_se_chevauchent(d1, f1, d2, f2):
    return d1 < f2 and f1 > d2


# --- Routes ---
@app.get("/salles")
@require_token
def get_salles():
    return jsonify(salles_db)


@app.get("/salles/<int:salle_id>")
@require_token
def get_salle(salle_id):
    salle = next((s for s in salles_db if s["id"] == salle_id), None)
    if not salle:
        return jsonify({"erreur": "Ressource introuvable"}), 404
    return jsonify(salle)


@app.get("/salles/<int:salle_id>/reservations")
@require_token
def get_reservations(salle_id):
    salle = next((s for s in salles_db if s["id"] == salle_id), None)
    if not salle:
        return jsonify({"erreur": "Ressource introuvable"}), 404
    return jsonify([r for r in reservations_db if r["salle_id"] == salle_id])


@app.post("/salles/<int:salle_id>/reservations")
@require_token
def create_reservation(salle_id):
    global next_id
    salle = next((s for s in salles_db if s["id"] == salle_id), None)
    if not salle:
        return jsonify({"erreur": "Ressource introuvable"}), 404
    data = request.get_json()
    erreurs = valider_reservation(data)
    if erreurs:
        return jsonify({"erreur": "Données invalides", "detail": erreurs}), 422
    for r in reservations_db:
        if r["salle_id"] == salle_id and r["date"] == data["date"]:
            if creneaux_se_chevauchent(data["heure_debut"], data["heure_fin"],
                                       r["heure_debut"], r["heure_fin"]):
                return jsonify({"erreur": "Conflit de réservation"}), 409
    nouvelle = {"id": next_id, "salle_id": salle_id, **data}
    reservations_db.append(nouvelle)
    next_id += 1
    return jsonify(nouvelle), 201


@app.delete("/reservations/<int:reservation_id>")
@require_token
def delete_reservation(reservation_id):
    resa = next((r for r in reservations_db if r["id"] == reservation_id), None)
    if not resa:
        return jsonify({"erreur": "Ressource introuvable"}), 404
    reservations_db[:] = [r for r in reservations_db if r["id"] != reservation_id]
    return "", 204


if __name__ == "__main__":
    app.run(debug=True, port=5000)
