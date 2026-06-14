from django.urls import path

from .views import (
    ConnexionView,
    DeconnexionView,
    accueil,
    administration,
    etudiant,
    inscription,
)

app_name = 'frontend'

urlpatterns = [
    path('', accueil, name='accueil'),
    path('connexion/', ConnexionView.as_view(), name='connexion'),
    path('deconnexion/', DeconnexionView.as_view(), name='deconnexion'),
    path('inscription/', inscription, name='inscription'),
    path('etudiant/', etudiant, name='etudiant'),
    path('administration/', administration, name='administration'),
]
