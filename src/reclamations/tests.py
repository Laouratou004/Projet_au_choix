"""
[S6.1] Tests et corrections — module réclamations (admin).

Parcours testés :
  - Liste des réclamations ([S4.1])
  - Filtres catégorie / statut ([S4.2])
  - Mise à jour du statut ([S4.3])
  - Réponse de l'administrateur ([S4.4])
  - Tableau de bord ([S4.5])
  - Contrôle d'accès (étudiant ne peut pas accéder aux endpoints admin)
"""

from django.urls import reverse

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from users.models import User

from .models import Message, Reclamation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_user(username, role=User.ROLE_ETUDIANT, password='testpass123'):
    user = User.objects.create_user(username=username, password=password, role=role)
    return user


def auth_client(client, user):
    token, _ = Token.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


def create_reclamation(etudiant, categorie='notes', statut='soumise', description='Test description'):
    return Reclamation.objects.create(
        etudiant=etudiant,
        categorie=categorie,
        statut=statut,
        description=description,
        reference=f'REC-TEST-{Reclamation.objects.count() + 1:03d}',
    )


# ---------------------------------------------------------------------------
# [S4.1] Liste des réclamations
# ---------------------------------------------------------------------------

class ReclamationListViewTests(APITestCase):
    """[S4.1] L'admin voit toutes les réclamations, triées par date décroissante."""

    def setUp(self):
        self.admin = create_user('admin_user', role=User.ROLE_ADMIN)
        self.etudiant = create_user('etudiant_user', role=User.ROLE_ETUDIANT)
        self.rec1 = create_reclamation(self.etudiant, categorie='notes')
        self.rec2 = create_reclamation(self.etudiant, categorie='bourse')
        self.url = reverse('reclamation-list')

    def test_admin_voit_toutes_les_reclamations(self):
        auth_client(self.client, self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_etudiant_ne_peut_pas_acceder(self):
        """Contrôle d'accès : un étudiant ne doit pas voir la liste admin."""
        auth_client(self.client, self.etudiant)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_authentifie_ne_peut_pas_acceder(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_champs_retournes(self):
        auth_client(self.client, self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        champs_attendus = {'id', 'reference', 'categorie', 'categorie_display',
                           'statut', 'statut_display', 'etudiant_username',
                           'etudiant_email', 'date_creation', 'date_maj'}
        self.assertTrue(champs_attendus.issubset(set(response.data[0].keys())))


# ---------------------------------------------------------------------------
# [S4.2] Filtres
# ---------------------------------------------------------------------------

class ReclamationFiltresTests(APITestCase):
    """[S4.2] Filtres par catégorie et statut, combinables."""

    def setUp(self):
        self.admin = create_user('admin2', role=User.ROLE_ADMIN)
        self.etudiant = create_user('etudiant2')
        create_reclamation(self.etudiant, categorie='notes', statut='soumise')
        create_reclamation(self.etudiant, categorie='notes', statut='en_cours')
        create_reclamation(self.etudiant, categorie='bourse', statut='soumise')
        self.url = reverse('reclamation-list')
        auth_client(self.client, self.admin)

    def test_filtre_par_categorie(self):
        response = self.client.get(self.url, {'categorie': 'notes'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        for rec in response.data:
            self.assertEqual(rec['categorie'], 'notes')

    def test_filtre_par_statut(self):
        response = self.client.get(self.url, {'statut': 'soumise'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        for rec in response.data:
            self.assertEqual(rec['statut'], 'soumise')

    def test_filtres_combines(self):
        response = self.client.get(self.url, {'categorie': 'notes', 'statut': 'soumise'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filtre_sans_resultat(self):
        response = self.client.get(self.url, {'categorie': 'examens'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


# ---------------------------------------------------------------------------
# [S4.3] Mise à jour du statut
# ---------------------------------------------------------------------------

class ReclamationStatutTests(APITestCase):
    """[S4.3] L'admin peut faire évoluer le statut d'une réclamation."""

    def setUp(self):
        self.admin = create_user('admin3', role=User.ROLE_ADMIN)
        self.etudiant = create_user('etudiant3')
        self.rec = create_reclamation(self.etudiant)
        self.url = reverse('reclamation-statut', kwargs={'pk': self.rec.pk})
        auth_client(self.client, self.admin)

    def test_mise_a_jour_statut(self):
        response = self.client.patch(self.url, {'statut': 'en_cours'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.rec.refresh_from_db()
        self.assertEqual(self.rec.statut, 'en_cours')

    def test_statut_invalide_retourne_400(self):
        response = self.client.patch(self.url, {'statut': 'inexistant'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reclamation_inexistante_retourne_404(self):
        url = reverse('reclamation-statut', kwargs={'pk': 9999})
        response = self.client.patch(url, {'statut': 'resolue'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_etudiant_ne_peut_pas_modifier_statut(self):
        auth_client(self.client, self.etudiant)
        response = self.client.patch(self.url, {'statut': 'resolue'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# [S4.4] Réponse de l'administrateur
# ---------------------------------------------------------------------------

class ReclamationReponseTests(APITestCase):
    """[S4.4] L'admin peut ajouter un message de réponse à une réclamation."""

    def setUp(self):
        self.admin = create_user('admin4', role=User.ROLE_ADMIN)
        self.etudiant = create_user('etudiant4')
        self.rec = create_reclamation(self.etudiant)
        self.url = reverse('reclamation-reponse', kwargs={'pk': self.rec.pk})
        auth_client(self.client, self.admin)

    def test_admin_peut_repondre(self):
        response = self.client.post(self.url, {'contenu': 'Votre dossier a été traité.'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.filter(reclamation=self.rec).count(), 1)
        msg = Message.objects.get(reclamation=self.rec)
        self.assertEqual(msg.auteur, self.admin)

    def test_contenu_vide_retourne_400(self):
        response = self.client.post(self.url, {'contenu': ''}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reclamation_inexistante_retourne_404(self):
        url = reverse('reclamation-reponse', kwargs={'pk': 9999})
        response = self.client.post(url, {'contenu': 'Test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_etudiant_ne_peut_pas_repondre(self):
        auth_client(self.client, self.etudiant)
        response = self.client.post(self.url, {'contenu': 'Test'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# [S4.5] Tableau de bord
# ---------------------------------------------------------------------------

class DashboardTests(APITestCase):
    """[S4.5] Le tableau de bord renvoie les statistiques correctes."""

    def setUp(self):
        self.admin = create_user('admin5', role=User.ROLE_ADMIN)
        self.etudiant = create_user('etudiant5')
        create_reclamation(self.etudiant, categorie='notes', statut='soumise')
        create_reclamation(self.etudiant, categorie='notes', statut='en_cours')
        create_reclamation(self.etudiant, categorie='bourse', statut='resolue')
        self.url = reverse('reclamation-dashboard')
        auth_client(self.client, self.admin)

    def test_total_correct(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 3)

    def test_structure_reponse(self):
        response = self.client.get(self.url)
        self.assertIn('total', response.data)
        self.assertIn('par_statut', response.data)
        self.assertIn('par_categorie', response.data)

    def test_repartition_par_statut(self):
        response = self.client.get(self.url)
        statuts = {item['statut']: item['count'] for item in response.data['par_statut']}
        self.assertEqual(statuts.get('soumise'), 1)
        self.assertEqual(statuts.get('en_cours'), 1)
        self.assertEqual(statuts.get('resolue'), 1)

    def test_repartition_par_categorie(self):
        response = self.client.get(self.url)
        categories = {item['categorie']: item['count'] for item in response.data['par_categorie']}
        self.assertEqual(categories.get('notes'), 2)
        self.assertEqual(categories.get('bourse'), 1)

    def test_etudiant_ne_peut_pas_acceder_dashboard(self):
        auth_client(self.client, self.etudiant)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
