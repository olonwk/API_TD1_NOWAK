"""
Application FastAPI + GraphQL (Strawberry)
Module ECHE834 - Exercice 2B
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Header
from strawberry.fastapi import GraphQLRouter
from schema import schema

# Chargement des variables d'environnement
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN", "mon_token_secret_123")

# ---------------------------------------------------------------------------
# Initialisation FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title="API GraphQL - Événements",
    description="API GraphQL de gestion d'événements - TD ECHE834",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Dépendance d'authentification : vérification du token Bearer
# Injectée dans le routeur GraphQL via FastAPI Depends
# ---------------------------------------------------------------------------
def verifier_token(authorization: str = Header(...)):
    """Vérifie que le header Authorization contient un token Bearer valide."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Format attendu: Bearer <token>")
    token = authorization.split(" ")[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Token invalide ou expiré")


# ---------------------------------------------------------------------------
# Routeur GraphQL — exposé sur /graphql avec protection par token
# L'interface interactive GraphiQL est disponible sur /graphql (navigateur)
# ---------------------------------------------------------------------------
graphql_router = GraphQLRouter(
    schema,
    dependencies=[Depends(verifier_token)],
)
app.include_router(graphql_router, prefix="/graphql")


@app.get("/")
async def root():
    return {"message": "API GraphQL Événements opérationnelle", "endpoint": "/graphql"}


if __name__ == "__main__":
    import uvicorn
    print("=== API GraphQL Événements démarrée sur http://localhost:8000 ===")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
