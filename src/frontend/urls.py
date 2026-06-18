# Routes HTML servies par l'app frontend.
# Toutes ces URLs renvoient des pages HTML (pas du JSON) ; le JavaScript
# embarqué dans les templates consomme ensuite les APIs /api/*.

from django.urls import path

from .views import (
    ConnexionView,
    DeconnexionView,
    accueil,
    administration,
    creer_etudiant,
    etudiant,
)

app_name = 'frontend'

urlpatterns = [
    path('', accueil, name='accueil'),                                                # accueil public
    path('connexion/', ConnexionView.as_view(), name='connexion'),                    # formulaire de login
    path('deconnexion/', DeconnexionView.as_view(), name='deconnexion'),              # POST logout
    path('etudiant/', etudiant, name='etudiant'),                                      # espace étudiant
    path('administration/', administration, name='administration'),                    # espace admin
    path('administration/creer-etudiant/', creer_etudiant, name='creer_etudiant'),    # création de compte par l'admin
]
