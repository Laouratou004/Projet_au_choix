# Documentation — Chatbot de Réclamations Académiques

## 📋 Table des matières

1. [Aperçu](#aperçu)
2. [Architecture](#architecture)
3. [API Endpoints](#api-endpoints)
4. [Guide de Démarrage](#guide-de-démarrage)
5. [Scénario de Démonstration](#scénario-de-démonstration)
6. [Modèles de Données](#modèles-de-données)

---

## Aperçu

**Chatbot de réclamations académiques** : application Django + REST API permettant aux étudiants de déposer et suivre des réclamations (Notes, Scolarité, Examens, Bourse) et à l'administration de les traiter.

**Fonctionnalités principales :**
- 👤 **Authentification** : rôles Étudiant / Administration
- 📝 **Dépôt de réclamation** : parcours guidé avec chatbot
- 📊 **Suivi** : consultation du statut via référence unique
- 🛠️ **Administration** : liste, filtrage, mise à jour, réponse aux réclamations
- 📈 **Tableau de bord** : statistiques (par statut, catégorie)

---

## Architecture

```
Projet_au_choix/
├── src/
│   ├── config/                    # Paramètres Django
│   │   ├── settings.py            # Configuration (BD SQLite, apps, middleware)
│   │   ├── urls.py                # Routeur principal
│   │   ├── asgi.py                # ASGI (production)
│   │   └── wsgi.py                # WSGI (production)
│   │
│   ├── users/                     # Module Authentification
│   │   ├── models.py              # User (extends AbstractUser, rôle)
│   │   ├── views.py               # Endpoints (login, register, profile)
│   │   ├── serializers.py         # Sérialisation User
│   │   ├── permissions.py         # IsAdmin, IsStudent
│   │   └── urls.py                # /api/users/
│   │
│   ├── reclamations/              # Module Administration (Sadjo)
│   │   ├── models.py              # Reclamation, Message
│   │   ├── views.py               # [S4.1-S4.5] Admin API
│   │   ├── serializers.py         # Sérialisation Reclamation
│   │   ├── tests.py               # [S6.1] Tests d'acceptation
│   │   ├── urls.py                # /api/reclamations/
│   │   └── migrations/
│   │
│   ├── chatbot/                   # Module Étudiant (Laouratou)
│   │   ├── models.py              # Chatbot conversations
│   │   ├── views.py               # [S2.1-S2.4] Étudiant API
│   │   ├── serializers.py
│   │   ├── urls.py                # /api/chatbot/
│   │   └── migrations/
│   │
│   └── manage.py
│
├── requirements.txt               # asgiref, Django, djangorestframework, django-cors-headers, sqlparse
├── db.sqlite3                     # Base de données SQLite (générée après migrate)
├── README.md
├── DOCUMENTATION.md               # Cette doc
└── cahier-des-charges-chatbot-reclamations-v2.docx
```

**Stack Technique :**
- Python 3.12+
- Django 6.0.4
- Django REST Framework 3.17.1
- SQLite 3
- Token Authentication (DRF)
- CORS enabled

---

## API Endpoints

### 1️⃣ Authentification (Module Users)

#### Créer un compte
```
POST /api/users/register/
Content-Type: application/json

{
  "username": "etudiant123",
  "email": "etudiant@example.com",
  "password": "SecurePass2026!",
  "first_name": "Jean",
  "last_name": "Dupont",
  "role": "etudiant"  # ou "admin"
}

Response 201:
{
  "id": 1,
  "username": "etudiant123",
  "email": "etudiant@example.com",
  "role": "etudiant",
  "token": "abc123def456..."
}
```

#### Authentification
```
POST /api/users/login/
Content-Type: application/json

{
  "username": "etudiant123",
  "password": "SecurePass2026!"
}

Response 200:
{
  "token": "abc123def456...",
  "user": {
    "id": 1,
    "username": "etudiant123",
    "role": "etudiant"
  }
}
```

#### Profil utilisateur
```
GET /api/users/profile/
Authorization: Token abc123def456...

Response 200:
{
  "id": 1,
  "username": "etudiant123",
  "email": "etudiant@example.com",
  "first_name": "Jean",
  "last_name": "Dupont",
  "role": "etudiant"
}
```

---

### 2️⃣ Module Chatbot Étudiant (Dépôt) [S2.1-S2.4]

#### [S2.1] Démarrer une conversation
```
POST /api/chatbot/conversation/
Authorization: Token <student-token>
Content-Type: application/json

{
  "action": "start"
}

Response 201:
{
  "conversation_id": 42,
  "message": "Bienvenue ! 👋 Que souhaitez-vous faire ?\n1. Déposer une nouvelle réclamation\n2. Suivre une réclamation",
  "options": ["deposit", "track"]
}
```

#### [S2.2] Choisir une catégorie
```
POST /api/chatbot/conversation/42/respond/
Authorization: Token <student-token>
Content-Type: application/json

{
  "user_input": "deposit",
  "action": "select_category"
}

Response 200:
{
  "conversation_id": 42,
  "message": "Quelle est la catégorie de votre réclamation ?\n1. Notes\n2. Scolarité\n3. Examens\n4. Bourse",
  "categories": ["notes", "scolarite", "examens", "bourse"]
}
```

#### [S2.3] Décrire la réclamation et soumettre
```
POST /api/chatbot/conversation/42/respond/
Authorization: Token <student-token>
Content-Type: application/json

{
  "user_input": "notes",
  "action": "describe_issue"
}

# Puis l'étudiant fournit la description
POST /api/chatbot/conversation/42/respond/
Authorization: Token <student-token>
Content-Type: application/json

{
  "user_input": "Ma note du contrôle continu de Programmation semble erronée. Je pense avoir eu au moins 15/20.",
  "action": "submit"
}

Response 201:
{
  "conversation_id": 42,
  "reclamation_id": 5,
  "reference": "REC-2026-001",
  "message": "✅ Réclamation soumise avec succès !"
}
```

#### [S2.4] Obtenir la référence
```
GET /api/chatbot/conversation/42/reference/
Authorization: Token <student-token>

Response 200:
{
  "reference": "REC-2026-001",
  "categorie": "notes",
  "statut": "soumise",
  "date_creation": "2026-06-09T10:30:00Z"
}
```

---

### 3️⃣ Module Suivi Étudiant [S3.1]

#### Consulter le statut d'une réclamation
```
POST /api/chatbot/track/
Authorization: Token <student-token> (optionnel)
Content-Type: application/json

{
  "reference": "REC-2026-001"
}

Response 200:
{
  "reference": "REC-2026-001",
  "categorie": "notes",
  "categorie_display": "Notes",
  "statut": "en_cours",
  "statut_display": "En cours",
  "date_creation": "2026-06-09T10:30:00Z",
  "date_maj": "2026-06-09T14:45:00Z",
  "messages": [
    {
      "id": 1,
      "auteur_role": "admin",
      "contenu": "Nous avons reçu votre réclamation.",
      "date": "2026-06-09T14:45:00Z"
    }
  ]
}
```

---

### 4️⃣ Module Administration [S4.1-S4.5]

**Prérequis :** Authentification admin (`role: "admin"`)

#### [S4.1] Lister les réclamations
```
GET /api/reclamations/
Authorization: Token <admin-token>

Response 200:
[
  {
    "id": 1,
    "reference": "REC-2026-001",
    "categorie": "notes",
    "categorie_display": "Notes",
    "statut": "soumise",
    "statut_display": "Soumise",
    "etudiant_username": "etudiant123",
    "etudiant_email": "etudiant@example.com",
    "date_creation": "2026-06-09T10:30:00Z",
    "date_maj": "2026-06-09T10:30:00Z"
  }
]
```

#### [S4.2] Filtrer par catégorie et/ou statut
```
GET /api/reclamations/?categorie=notes&statut=soumise
Authorization: Token <admin-token>

GET /api/reclamations/?categorie=examens
GET /api/reclamations/?statut=en_cours
```

#### [S4.3] Détail d'une réclamation
```
GET /api/reclamations/1/
Authorization: Token <admin-token>

Response 200:
{
  "id": 1,
  "reference": "REC-2026-001",
  "categorie": "notes",
  "etudiant_username": "etudiant123",
  "description": "Ma note du contrôle continu...",
  "statut": "soumise",
  "date_creation": "2026-06-09T10:30:00Z",
  "messages": []
}
```

#### Mettre à jour le statut
```
PATCH /api/reclamations/1/statut/
Authorization: Token <admin-token>
Content-Type: application/json

{
  "statut": "en_cours"  # soumise | en_cours | attente_info | resolue | cloturee
}

Response 200:
{
  "detail": "Statut mis à jour.",
  "statut": "en_cours",
  "statut_display": "En cours",
  "date_maj": "2026-06-09T14:45:00Z"
}
```

#### [S4.4] Ajouter une réponse
```
POST /api/reclamations/1/reponse/
Authorization: Token <admin-token>
Content-Type: application/json

{
  "contenu": "Nous avons vérifié votre dossier. Votre note était correcte. Réclamation rejetée."
}

Response 201:
{
  "detail": "Réponse ajoutée.",
  "message_id": 1,
  "date": "2026-06-09T14:45:00Z"
}
```

#### [S4.5] Tableau de bord
```
GET /api/reclamations/dashboard/
Authorization: Token <admin-token>

Response 200:
{
  "total": 42,
  "par_statut": [
    {"statut": "soumise", "label": "Soumise", "count": 15},
    {"statut": "en_cours", "label": "En cours", "count": 18},
    {"statut": "resolue", "label": "Résolue", "count": 8},
    {"statut": "cloturee", "label": "Clôturée", "count": 1}
  ],
  "par_categorie": [
    {"categorie": "notes", "label": "Notes", "count": 20},
    {"categorie": "examens", "label": "Examens", "count": 12},
    {"categorie": "scolarite", "label": "Scolarité", "count": 7},
    {"categorie": "bourse", "label": "Bourse", "count": 3}
  ]
}
```

---

## Guide de Démarrage

### Installation complète

```bash
# 1. Cloner le dépôt
git clone https://github.com/Laouratou004/Projet_au_choix.git
cd Projet_au_choix

# 2. Créer et activer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate          # Linux/Mac
# ou
venv\Scripts\activate             # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Appliquer les migrations
cd src
python manage.py migrate

# 5. Créer un superutilisateur (pour l'interface admin Django)
python manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: ...

# 6. Créer des utilisateurs de test
python manage.py shell
>>> from users.models import User
>>> User.objects.create_user(username='etudiant1', password='test123', role='etudiant', email='etudiant1@example.com')
>>> User.objects.create_user(username='admin1', password='test123', role='admin', email='admin1@example.com')
>>> exit()

# 7. Lancer le serveur
python manage.py runserver
```

Le serveur démarre sur **http://127.0.0.1:8000/**
- API : http://127.0.0.1:8000/api/
- Admin Django : http://127.0.0.1:8000/admin/

---

## Scénario de Démonstration

### 🎬 Partie 1 : Parcours Étudiant

#### Étape 1 : Inscription
```bash
curl -X POST http://127.0.0.1:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "marie_dupont",
    "email": "marie@example.com",
    "password": "SecurePass2026!",
    "first_name": "Marie",
    "last_name": "Dupont",
    "role": "etudiant"
  }'
```
**Résultat :** Token retourné (ex. `abc123...`). Marie est enregistrée.

#### Étape 2 : Démarrer une conversation
```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/conversation/ \
  -H "Authorization: Token abc123..." \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'
```
**Résultat :** Conversation créée, affichage du menu principal.

#### Étape 3 : Choisir une action (Dépôt)
```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/conversation/1/respond/ \
  -H "Authorization: Token abc123..." \
  -H "Content-Type: application/json" \
  -d '{"user_input": "deposit", "action": "select_category"}'
```
**Résultat :** Liste des 4 catégories affichées.

#### Étape 4 : Choisir une catégorie
```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/conversation/1/respond/ \
  -H "Authorization: Token abc123..." \
  -H "Content-Type: application/json" \
  -d '{"user_input": "notes", "action": "describe_issue"}'
```
**Résultat :** Invite pour décrire le problème.

#### Étape 5 : Décrire et soumettre
```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/conversation/1/respond/ \
  -H "Authorization: Token abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "J'\''ai obtenu 12/20 au contrôle continu mais je mérite au minimum 15/20. Mes travaux précédents étaient meilleurs.",
    "action": "submit"
  }'
```
**Résultat :** Réclamation soumise, **référence unique générée** (ex. `REC-2026-001`).

#### Étape 6 : Suivre le statut (Consultation)
```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/track/ \
  -H "Content-Type: application/json" \
  -d '{"reference": "REC-2026-001"}'
```
**Résultat :** Status = "Soumise", date de création affichée.

---

### 🛠️ Partie 2 : Parcours Administration

#### Étape 1 : Connexion administrateur
```bash
curl -X POST http://127.0.0.1:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin1",
    "password": "test123"
  }'
```
**Résultat :** Token admin retourné (ex. `xyz789...`).

#### Étape 2 : Voir toutes les réclamations [S4.1]
```bash
curl -X GET http://127.0.0.1:8000/api/reclamations/ \
  -H "Authorization: Token xyz789..."
```
**Résultat :** Liste affichée, triée par date décroissante. Affiche `REC-2026-001` (Marie).

#### Étape 3 : Filtrer par catégorie [S4.2]
```bash
curl -X GET "http://127.0.0.1:8000/api/reclamations/?categorie=notes" \
  -H "Authorization: Token xyz789..."
```
**Résultat :** Affiche uniquement les réclamations "Notes".

#### Étape 4 : Voir le détail [S4.1]
```bash
curl -X GET http://127.0.0.1:8000/api/reclamations/1/ \
  -H "Authorization: Token xyz789..."
```
**Résultat :** Description complète, statut = "Soumise", pas encore de réponse.

#### Étape 5 : Passer en "En cours" [S4.3]
```bash
curl -X PATCH http://127.0.0.1:8000/api/reclamations/1/statut/ \
  -H "Authorization: Token xyz789..." \
  -H "Content-Type: application/json" \
  -d '{"statut": "en_cours"}'
```
**Résultat :** Statut passé à "En cours", `date_maj` mise à jour.

#### Étape 6 : Ajouter une réponse [S4.4]
```bash
curl -X POST http://127.0.0.1:8000/api/reclamations/1/reponse/ \
  -H "Authorization: Token xyz789..." \
  -H "Content-Type: application/json" \
  -d '{"contenu": "Nous avons examiné votre dossier. Après révision, votre note était correcte. Réclamation rejetée."}'
```
**Résultat :** Message ajouté, visible lors du suivi étudiant.

#### Étape 7 : Passer à "Résolue" [S4.3]
```bash
curl -X PATCH http://127.0.0.1:8000/api/reclamations/1/statut/ \
  -H "Authorization: Token xyz789..." \
  -H "Content-Type: application/json" \
  -d '{"statut": "resolue"}'
```
**Résultat :** Statut = "Résolue", date mise à jour.

#### Étape 8 : Tableau de bord [S4.5]
```bash
curl -X GET http://127.0.0.1:8000/api/reclamations/dashboard/ \
  -H "Authorization: Token xyz789..."
```
**Résultat :** Statistiques :
- Total : 1
- Par statut : 1 × Résolue
- Par catégorie : 1 × Notes

---

### 👤 Étape finale : Étudiant vérifie la réponse

#### Suivi mis à jour
```bash
curl -X POST http://127.0.0.1:8000/api/chatbot/track/ \
  -H "Content-Type: application/json" \
  -d '{"reference": "REC-2026-001"}'
```
**Résultat :**
```json
{
  "reference": "REC-2026-001",
  "categorie": "notes",
  "statut": "resolue",
  "messages": [
    {
      "auteur_role": "admin",
      "contenu": "Nous avons examiné votre dossier...",
      "date": "2026-06-09T14:45:00Z"
    }
  ]
}
```

✅ **L'étudiant voit que sa réclamation a été traitée et a reçu une réponse.**

---

## Modèles de Données

### User (users/models.py)
```python
class User(AbstractUser):
    ROLE_ETUDIANT = 'etudiant'
    ROLE_ADMIN = 'admin'
    
    username: str (unique)
    email: str
    first_name: str
    last_name: str
    password: str (hashed)
    role: str (etudiant | admin)
```

### Reclamation (reclamations/models.py)
```python
class Reclamation(models.Model):
    reference: str (unique, ex. REC-2026-001) [S2.4]
    etudiant: ForeignKey(User)
    categorie: str (notes | scolarite | examens | bourse) [S2.2]
    description: str [S2.3]
    statut: str (soumise | en_cours | attente_info | resolue | cloturee) [S4.3]
    date_creation: datetime (auto)
    date_maj: datetime (auto)
```

### Message (reclamations/models.py)
```python
class Message(models.Model):
    reclamation: ForeignKey(Reclamation)
    auteur: ForeignKey(User)  # étudiant ou admin
    contenu: str
    date: datetime (auto)
```

---

## ✅ Critères d'Acceptation — [S6.1] & [S6.2]

- ✅ Parcours complet de dépôt d'étudiant (S2.1-S2.4)
- ✅ Parcours complet d'administration (S4.1-S4.5)
- ✅ Authentification et contrôle d'accès (S5.1)
- ✅ Modèles de données versionnés
- ✅ Tests d'acceptation (reclamations/tests.py)
- ✅ Documentation API (cette doc)
- ✅ Scénario de démonstration (section ci-dessus)
- ✅ Code source en Git, déployable

---

**Dernier commit :** [S6.2] Documentation et scénario de démonstration
**Date :** 2026-06-09
**Auteur :** Sadjo (Module Administration)
