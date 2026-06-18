"""URLs du module réclamations (administration)."""
# Préfixées par /api/reclamations/ dans config/urls.py.
# Deux espaces se côtoient :
#   - /mes-reclamations/...  : actions de l'étudiant sur SES dossiers
#   - /, /<pk>/...            : actions de l'administration sur tous les dossiers

# pyrefly: ignore [missing-import]
from django.urls import path

from .views import (
    DashboardView,
    MaReclamationDetailView,
    MesReclamationsView,
    ReclamationDetailView,
    ReclamationListView,
    ReclamationReponseView,
    ReclamationStatutView,
)

urlpatterns = [
    # Espace étudiant : liste de mes réclamations
    path('mes-reclamations/', MesReclamationsView.as_view(), name='mes-reclamations'),
    # Espace étudiant : modifier / supprimer une de mes réclamations
    path('mes-reclamations/<int:pk>/', MaReclamationDetailView.as_view(), name='ma-reclamation-detail'),
    # [S4.1] + [S4.2] Liste + filtres (admin)
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
