"""URL configuration for the Projet_au_choix project."""
# Routeur racine : assemble les URLs de toutes les apps du projet.
# Convention :
#   - /admin/                 : admin Django (gestion des données brutes)
#   - /api/*                  : APIs REST consommées par le JavaScript frontend
#   - reste                   : pages HTML (frontend)

# pyrefly: ignore [missing-import]
from django.contrib import admin
# pyrefly: ignore [missing-import]
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),                     # register, login, logout, me
    path('api/reclamations/', include('reclamations.urls')),      # CRUD réclamations + dashboard
    path('api/chatbot/', include('chatbot.urls')),                # conversations + moteur de dialogue
    path('', include('frontend.urls')),                           # pages HTML servies au navigateur
]
