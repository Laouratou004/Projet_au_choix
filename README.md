# Projet au choix — Chatbot de réclamations académiques

Application web / chatbot permettant aux étudiants de déposer et suivre leurs réclamations académiques (notes, scolarité, examens, bourse) et à l'administration de les traiter.

> Projet n°14 — Voir `cahier-des-charges-chatbot-reclamations-v2.docx` pour le détail.

## Équipe

- **Laouratou** — Module Étudiant (E2, E3)
- **Sadjo** — Module Administration (E4)

## Stack

- Backend : Django 6 + Django REST Framework
- Base de données : SQLite (dev)
- Frontend : à définir (chatbot web)

## Structure

```
Projet_au_choix/
├── backend/                  # Projet Django
│   ├── backend/              # Settings / urls / wsgi
│   ├── users/                # Authentification + rôles étudiant/admin
│   ├── reclamations/         # Modèles Reclamation + Message
│   ├── chatbot/              # Logique du chatbot (parcours guidé)
│   └── manage.py
├── requirements.txt
└── README.md
```

## Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/Laouratou004/Projet_au_choix.git
cd Projet_au_choix

# 2. Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Appliquer les migrations
cd backend
python manage.py migrate

# 5. Créer un superutilisateur (admin)
python manage.py createsuperuser

# 6. Lancer le serveur de développement
python manage.py runserver
```

Le serveur est accessible sur http://127.0.0.1:8000/ et l'admin Django sur http://127.0.0.1:8000/admin/.
