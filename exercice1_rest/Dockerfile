# Dockerfile - API REST Flask (Exercice 1)

# Image de base : Python 3.11 slim (version légère, sans outils inutiles)
FROM python:3.11-slim

# Répertoire de travail dans le conteneur
WORKDIR /app

# Copier requirements.txt en premier : si le fichier ne change pas,
# Docker réutilise la couche en cache et évite de réinstaller les dépendances
COPY requirements.txt .

# Installer les dépendances sans cache pip pour réduire la taille de l'image
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code source
COPY . .

# Port exposé par Flask
EXPOSE 5000

# Variables d'environnement par défaut (surchargées par docker-compose ou --env-file)
ENV FLASK_ENV=production

# Démarrage de l'application
# En production, remplacer par : gunicorn -w 4 -b 0.0.0.0:5000 app:app
CMD ["python", "app.py"]
