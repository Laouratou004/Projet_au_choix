"""URLs du module réclamations (administration)."""
# pyrefly: ignore [missing-import]
from django.urls import path

from .views import (
    DashboardView,
    ReclamationDetailView,
    ReclamationListView,
    ReclamationReponseView,
    ReclamationStatutView,
)

urlpatterns = [
    # [S4.1] + [S4.2] Liste + filtres
    path('', ReclamationListView.as_view(), name='reclamation-list'),
    # [S4.3] Détail
    path('<int:pk>/', ReclamationDetailView.as_view(), name='reclamation-detail'),
    # [S4.3] Mise à jour du statut
    path('<int:pk>/statut/', ReclamationStatutView.as_view(), name='reclamation-statut'),
    # [S4.4] Réponse admin
    path('<int:pk>/reponse/', ReclamationReponseView.as_view(), name='reclamation-reponse'),
    # [S4.5] Tableau de bord
    path('dashboard/', DashboardView.as_view(), name='reclamation-dashboard'),
]
