#!/usr/bin/env python3
"""API REST - Réservations de salles — Médiathèque municipale

Exercice 2 TD2 — Étape 3 : Implémentation (squelette des routes)
Framework retenu : FastAPI (cf. td2_benchmark pour la comparaison)
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List

security = HTTPBearer()

app = FastAPI(
    title="API Médiathèque — Réservations de salles",
    description="Gestion des salles et créneaux de réservation",
    version="1.0.0",
)

API_TOKEN = "mon_token_secret_123"
MSG_SALLE_INTROUVABLE = "Aucune salle avec cet id"
MSG_RESA_INTROUVABLE = "Aucune réservation avec cet id"


# ---------------------------------------------------------------------------
# MODÈLES Pydantic
# ---------------------------------------------------------------------------

class ReservationInput(BaseModel):
    usager: str
    date: str
    heure_debut: str
    heure_fin: str


class Reservation(ReservationInput):
    id: int
    salle_id: int


class Salle(BaseModel):
    id: int
    nom: str
    capacite: int
    equipement: List[str]


# ---------------------------------------------------------------------------
# BASES DE DONNÉES en mémoire
# ---------------------------------------------------------------------------

salles_db: List[dict] = [
    {"id": 1, "nom": "Salle Voltaire", "capacite": 12, "equipement": ["vidéoprojecteur", "tableau blanc"]},
    {"id": 2, "nom": "Salle Curie",    "capacite": 6,  "equipement": ["écran TV"]},
    {"id": 3, "nom": "Salle Hugo",     "capacite": 20, "equipement": ["vidéoprojecteur", "système audio", "tableau blanc"]},
]

reservations_db: List[dict] = [
    {"id": 1, "salle_id": 1, "usager": "M. Dupont", "date": "2026-06-20", "heure_debut": "14:00", "heure_fin": "15:30"},
]

next_reservation_id = 2


# ---------------------------------------------------------------------------
# AUTHENTIFICATION
# ---------------------------------------------------------------------------

def verifier_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=403, detail="Token invalide")


# ---------------------------------------------------------------------------
# ROUTES — Salles
# ---------------------------------------------------------------------------

@app.get("/salles", response_model=List[Salle])
def get_salles(credentials: HTTPAuthorizationCredentials = Depends(security)):
    verifier_token(credentials)
    return salles_db


@app.get("/salles/{salle_id}", response_model=Salle)
def get_salle(salle_id: int, credentials: HTTPAuthorizationCredentials = Depends(security)):
    verifier_token(credentials)
    salle = next((s for s in salles_db if s["id"] == salle_id), None)
    if salle is None:
        raise HTTPException(status_code=404, detail=MSG_SALLE_INTROUVABLE)
    return salle


# ---------------------------------------------------------------------------
# ROUTES — Réservations
# ---------------------------------------------------------------------------

@app.get("/salles/{salle_id}/reservations", response_model=List[Reservation])
def get_reservations_salle(salle_id: int, credentials: HTTPAuthorizationCredentials = Depends(security)):
    verifier_token(credentials)
    salle = next((s for s in salles_db if s["id"] == salle_id), None)
    if salle is None:
        raise HTTPException(status_code=404, detail=MSG_SALLE_INTROUVABLE)
    return [r for r in reservations_db if r["salle_id"] == salle_id]


@app.post("/salles/{salle_id}/reservations", response_model=Reservation, status_code=201)
def create_reservation(salle_id: int, resa_input: ReservationInput,
                       credentials: HTTPAuthorizationCredentials = Depends(security)):
    global next_reservation_id
    verifier_token(credentials)
    salle = next((s for s in salles_db if s["id"] == salle_id), None)
    if salle is None:
        raise HTTPException(status_code=404, detail=MSG_SALLE_INTROUVABLE)
    nouvelle_resa = {"id": next_reservation_id, "salle_id": salle_id, **resa_input.model_dump()}
    reservations_db.append(nouvelle_resa)
    next_reservation_id += 1
    return nouvelle_resa


@app.delete("/reservations/{reservation_id}", status_code=204)
def delete_reservation(reservation_id: int,
                       credentials: HTTPAuthorizationCredentials = Depends(security)):
    verifier_token(credentials)
    resa = next((r for r in reservations_db if r["id"] == reservation_id), None)
    if resa is None:
        raise HTTPException(status_code=404, detail=MSG_RESA_INTROUVABLE)
    reservations_db[:] = [r for r in reservations_db if r["id"] != reservation_id]
