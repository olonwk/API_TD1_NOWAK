#!/usr/bin/env python3
"""Benchmark FastAPI — API réservation de salles (version simplifiée pour comparaison)

Étape 2 TD2 : comparaison Flask vs FastAPI
Avantages FastAPI observés :
  - Validation automatique via Pydantic (moins de code boilerplate)
  - Documentation Swagger générée automatiquement sur /docs
  - Typage strict et retour d'erreurs 422 automatique si payload invalide
  - Gestion native de l'authentification Bearer
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List

security = HTTPBearer()

app = FastAPI(
    title="Benchmark FastAPI — Médiathèque",
    description="Version simplifiée pour comparaison avec Flask",
    version="1.0.0",
)

API_TOKEN = "mon_token_secret_123"


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


salles_db = [
    {"id": 1, "nom": "Salle Voltaire", "capacite": 12, "equipement": ["vidéoprojecteur"]},
    {"id": 2, "nom": "Salle Curie",    "capacite": 6,  "equipement": ["écran TV"]},
]
reservations_db = [
    {"id": 1, "salle_id": 1, "usager": "M. Dupont",
     "date": "2026-06-20", "heure_debut": "14:00", "heure_fin": "15:30"},
]
next_id = 2


def verifier_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=403, detail="Token invalide")


def creneaux_se_chevauchent(d1, f1, d2, f2):
    return d1 < f2 and f1 > d2


@app.get("/salles", response_model=List[Salle])
def get_salles(credentials: HTTPAuthorizationCredentials = Depends(security)):
    verifier_token(credentials)
    return salles_db


@app.get("/salles/{salle_id}", response_model=Salle)
def get_salle(salle_id: int, credentials: HTTPAuthorizationCredentials = Depends(security)):
    verifier_token(credentials)
    salle = next((s for s in salles_db if s["id"] == salle_id), None)
    if not salle:
        raise HTTPException(status_code=404, detail="Ressource introuvable")
    return salle


@app.get("/salles/{salle_id}/reservations", response_model=List[Reservation])
def get_reservations(salle_id: int, credentials: HTTPAuthorizationCredentials = Depends(security)):
    verifier_token(credentials)
    if not any(s["id"] == salle_id for s in salles_db):
        raise HTTPException(status_code=404, detail="Ressource introuvable")
    return [r for r in reservations_db if r["salle_id"] == salle_id]


@app.post("/salles/{salle_id}/reservations", response_model=Reservation, status_code=201)
def create_reservation(salle_id: int, resa: ReservationInput,
                       credentials: HTTPAuthorizationCredentials = Depends(security)):
    global next_id
    verifier_token(credentials)
    if not any(s["id"] == salle_id for s in salles_db):
        raise HTTPException(status_code=404, detail="Ressource introuvable")
    for r in reservations_db:
        if r["salle_id"] == salle_id and r["date"] == resa.date:
            if creneaux_se_chevauchent(resa.heure_debut, resa.heure_fin,
                                       r["heure_debut"], r["heure_fin"]):
                raise HTTPException(status_code=409, detail="Conflit de réservation")
    nouvelle = {"id": next_id, "salle_id": salle_id, **resa.model_dump()}
    reservations_db.append(nouvelle)
    next_id += 1
    return nouvelle


@app.delete("/reservations/{reservation_id}", status_code=204)
def delete_reservation(reservation_id: int,
                       credentials: HTTPAuthorizationCredentials = Depends(security)):
    verifier_token(credentials)
    if not any(r["id"] == reservation_id for r in reservations_db):
        raise HTTPException(status_code=404, detail="Ressource introuvable")
    reservations_db[:] = [r for r in reservations_db if r["id"] != reservation_id]
