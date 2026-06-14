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
    path('', accueil, name='accueil'),
    path('connexion/', ConnexionView.as_view(), name='connexion'),
    path('deconnexion/', DeconnexionView.as_view(), name='deconnexion'),
    path('etudiant/', etudiant, name='etudiant'),
    path('administration/', administration, name='administration'),
    path('administration/creer-etudiant/', creer_etudiant, name='creer_etudiant'),
]
