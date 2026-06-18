#!/usr/bin/env python3
"""API REST - Réservations de salles — Médiathèque municipale

Exercice 2 TD2 — Étape 4 : Validation des données et gestion des erreurs
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from typing import List
from datetime import date, time

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

    @field_validator("date")
    @classmethod
    def valider_date(cls, v):
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("La date doit être au format YYYY-MM-DD")
        return v

    @field_validator("heure_debut", "heure_fin")
    @classmethod
    def valider_heure(cls, v):
        try:
            time.fromisoformat(v)
        except ValueError:
            raise ValueError("L'heure doit être au format HH:MM")
        return v

    @field_validator("heure_fin")
    @classmethod
    def heure_fin_apres_debut(cls, v, info):
        debut = info.data.get("heure_debut")
        if debut and v <= debut:
            raise ValueError("heure_fin doit être postérieure à heure_debut")
        return v

    @field_validator("usager")
    @classmethod
    def usager_non_vide(cls, v):
        if not v.strip():
            raise ValueError("Le champ usager ne peut pas être vide")
        return v.strip()


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
        raise HTTPException(
            status_code=403,
            detail={"erreur": "Accès refusé", "detail": "Token invalide"}
        )


def creneaux_se_chevauchent(debut1: str, fin1: str, debut2: str, fin2: str) -> bool:
    return debut1 < fin2 and fin1 > debut2


def verifier_chevauchement(salle_id: int, date_resa: str, heure_debut: str, heure_fin: str):
    for resa in reservations_db:
        if resa["salle_id"] == salle_id and resa["date"] == date_resa:
            if creneaux_se_chevauchent(heure_debut, heure_fin, resa["heure_debut"], resa["heure_fin"]):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "erreur": "Conflit de réservation",
                        "detail": (
                            f"La salle {salle_id} est déjà réservée le {date_resa} "
                            f"de {resa['heure_debut']} à {resa['heure_fin']} par {resa['usager']}"
                        ),
                    },
                )


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
    verifier_chevauchement(salle_id, resa_input.date, resa_input.heure_debut, resa_input.heure_fin)
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
