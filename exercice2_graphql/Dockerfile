# Dockerfile - API GraphQL FastAPI (Exercice 2)

# Image de base : Python 3.11 slim
FROM python:3.11-slim

# Répertoire de travail dans le conteneur
WORKDIR /app

# Copier requirements.txt en premier (optimisation du cache Docker)
COPY requirements.txt .

# Installer les dépendances sans cache pip
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code source
COPY . .

# Port exposé par Uvicorn/FastAPI
EXPOSE 8000

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1

# Démarrage avec Uvicorn (serveur ASGI pour FastAPI)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
