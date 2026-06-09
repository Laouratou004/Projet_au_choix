# 🚀 Guide de Démarrage Rapide — Chatbot Réclamations

## ⚡ Setup en 5 minutes

### Prérequis
- Python 3.10+ 
- Git
- Terminal (PowerShell, CMD, Bash)

### Étape 1 : Cloner et accéder au repo

```bash
git clone https://github.com/Laouratou004/Projet_au_choix.git
cd Projet_au_choix
```

### Étape 2 : Créer un environnement virtuel

**Sur Windows :**
```bash
python -m venv venv
venv\Scripts\activate
```

**Sur Linux/Mac :**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Étape 3 : Installer les dépendances

```bash
pip install -r requirements.txt
```

### Étape 4 : Préparer la base de données

```bash
cd src
python manage.py migrate
```

### Étape 5 : Démarrer le serveur

```bash
python manage.py runserver
```

✅ **Le serveur est maintenant actif** sur `http://127.0.0.1:8000/`

---

## 🧪 Lancer les Tests

```bash
# Tous les tests
python manage.py test --verbosity=2

# Tests admin uniquement
python manage.py test reclamations.tests --verbosity=2

# Avec un nom de test spécifique
python manage.py test reclamations.tests.ReclamationListViewTests --verbosity=2
```

**Résultat attendu :** ✅ `OK — 18 tests`

---

## 📊 Création des Utilisateurs de Test

### Option 1 : Via Django Shell

```bash
python manage.py shell
```

```python
from users.models import User
from rest_framework.authtoken.models import Token

# Créer un étudiant
etudiant = User.objects.create_user(
    username='marie',
    password='test123',
    email='marie@example.com',
    first_name='Marie',
    last_name='Dupont',
    role='etudiant'
)

# Créer un admin
admin = User.objects.create_user(
    username='admin',
    password='test123',
    email='admin@example.com',
    role='admin'
)

# Obtenir les tokens
print(f"Token étudiant : {Token.objects.get_or_create(user=etudiant)[0].key}")
print(f"Token admin : {Token.objects.get_or_create(user=admin)[0].key}")

exit()
```

### Option 2 : Via Admin Django

```bash
# Créer un superutilisateur
python manage.py createsuperuser
# (Suivre les prompts)

# Accéder à http://127.0.0.1:8000/admin/
# Créer des users manuellement avec les rôles
```

---

## 🎯 Premier Test — Flux Complet

### 1️⃣ Étudiant : Déposer une réclamation

```bash
# S'inscrire
curl -X POST http://127.0.0.1:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_student",
    "password": "SecurePass123!",
    "email": "student@test.com",
    "first_name": "Test",
    "last_name": "Student",
    "role": "etudiant"
  }'

# Note : Copier le token retourné
```

**Réponse :**
```json
{
  "id": 1,
  "username": "test_student",
  "token": "abc123def456xyz789..."
}
```

### 2️⃣ Étudiant : Démarrer une conversation

```bash
export TOKEN="abc123def456xyz789..."

curl -X POST http://127.0.0.1:8000/api/chatbot/conversation/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'
```

### 3️⃣ Admin : Voir la réclamation

```bash
# S'inscrire comme admin
curl -X POST http://127.0.0.1:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_admin",
    "password": "SecurePass123!",
    "email": "admin@test.com",
    "role": "admin"
  }'

# Note : Copier le token admin
```

```bash
export ADMIN_TOKEN="xyz789abc123..."

curl -X GET http://127.0.0.1:8000/api/reclamations/ \
  -H "Authorization: Token $ADMIN_TOKEN"
```

---

## 🔗 URLs Importantes

| Ressource | URL |
|-----------|-----|
| API de base | http://127.0.0.1:8000/api/ |
| Admin Django | http://127.0.0.1:8000/admin/ |
| Utilisateurs | /api/users/ |
| Chatbot | /api/chatbot/ |
| Réclamations (admin) | /api/reclamations/ |

---

## 📚 Documentation Complète

Voir les fichiers suivants pour plus de détails :

- **[DOCUMENTATION.md](DOCUMENTATION.md)** — API complète avec tous les endpoints
- **[TEST_REPORT.md](TEST_REPORT.md)** — Résumé des tests et qualité
- **[README.md](README.md)** — Vue d'ensemble du projet

---

## ⚠️ Dépannage

### Module 'rest_framework' non trouvé

```bash
# Réinstaller les dépendances
pip install -r requirements.txt
```

### Port 8000 déjà utilisé

```bash
# Utiliser un autre port
python manage.py runserver 8001
```

### Base de données corrompue

```bash
# Réinitialiser complètement
rm src/db.sqlite3
python manage.py migrate
```

---

## 🎬 Démonstration Préparée

Un scénario de démonstration complet existe dans **DOCUMENTATION.md** avec :
- ✅ Création de compte étudiant
- ✅ Dépôt de réclamation
- ✅ Suivi du statut
- ✅ Traitement administrateur
- ✅ Réponse et mise à jour
- ✅ Tableau de bord

**Durée estimée :** 15 minutes pour tout le flux

---

**✅ Vous êtes prêt !** Lancez le serveur et commencez à tester 🚀
