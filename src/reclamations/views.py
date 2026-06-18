# Vues API du module réclamations.
# Deux familles d'endpoints :
#   - Espace étudiant : consulter / modifier / supprimer SES réclamations.
#   - Espace administration : lister toutes les réclamations, changer leur
#     statut, y répondre, consulter le tableau de bord global.
# Les filtres de permission IsEtudiant / IsAdmin (users/permissions.py)
# verrouillent l'accès au bon rôle.

# pyrefly: ignore [missing-import]
from django.db.models import Count

# pyrefly: ignore [missing-import]
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdmin, IsEtudiant

from .models import Message, Reclamation
from .serializers import (
    ReclamationDetailSerializer,
    ReclamationListSerializer,
    ReponseSerializer,
    StatutUpdateSerializer,
)


class MesReclamationsView(APIView):
    """Liste les réclamations déposées par l'étudiant connecté.

    Utilisée par l'onglet « Mes réclamations » de l'espace étudiant
    pour suivre l'état d'avancement de chaque dossier.
    """

    permission_classes = [IsAuthenticated, IsEtudiant]

    def get(self, request):
        # prefetch_related : on charge en une seule requête tous les messages
        # et leurs auteurs (évite le problème N+1 quand on sérialise la liste).
        qs = (
            Reclamation.objects
            .filter(etudiant=request.user)
            .prefetch_related('messages__auteur')
            .order_by('-date_creation')
        )
        return Response(ReclamationDetailSerializer(qs, many=True).data)


class MaReclamationDetailView(APIView):
    """Permet à l'étudiant de modifier ou supprimer SA réclamation.

    Pour préserver l'intégrité du traitement, ces actions ne sont
    possibles que tant que le dossier n'a pas été pris en charge
    par l'administration (statut == 'soumise').
    """

    permission_classes = [IsAuthenticated, IsEtudiant]

    def _get(self, request, pk):
        # Filtre crucial sur etudiant=request.user : empêche un étudiant
        # d'accéder à la réclamation d'un autre via une URL devinée.
        return Reclamation.objects.filter(pk=pk, etudiant=request.user).first()

    def patch(self, request, pk):
        reclamation = self._get(request, pk)
        if reclamation is None:
            return Response({'detail': 'Réclamation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        # Règle métier : on ne modifie plus une réclamation prise en charge.
        # 409 (Conflict) indique au frontend que la demande est légitime
        # mais incompatible avec l'état actuel de la ressource.
        if reclamation.statut != Reclamation.STATUT_SOUMISE:
            return Response(
                {'detail': "Modification impossible : votre réclamation est déjà en cours de traitement."},
                status=status.HTTP_409_CONFLICT,
            )
        description = (request.data.get('description') or '').strip()
        # Validation minimale côté serveur (le frontend valide aussi, mais
        # on ne fait jamais confiance au client).
        if len(description) < 5:
            return Response(
                {'detail': 'La description doit contenir au moins 5 caractères.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reclamation.description = description
        # update_fields : on ne met à jour que les colonnes nécessaires,
        # ce qui évite de re-déclencher save() sur tous les champs et
        # garde date_maj cohérente.
        reclamation.save(update_fields=['description', 'date_maj'])
        return Response({'detail': 'Réclamation mise à jour.'})

    def delete(self, request, pk):
        reclamation = self._get(request, pk)
        if reclamation is None:
            return Response({'detail': 'Réclamation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        # Même règle que pour la modification : pas de suppression après
        # prise en charge (traçabilité du dossier côté admin).
        if reclamation.statut != Reclamation.STATUT_SOUMISE:
            return Response(
                {'detail': "Suppression impossible : votre réclamation est déjà en cours de traitement."},
                status=status.HTTP_409_CONFLICT,
            )
        reclamation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReclamationListView(APIView):
    """
    [S4.1] Liste des réclamations reçues — accès administration.
    [S4.2] Filtres par catégorie et/ou statut via query params.

    GET /api/reclamations/
        ?categorie=notes|scolarite|examens|bourse
        ?statut=soumise|en_cours|attente_info|resolue|cloturee
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        # select_related : jointure SQL avec User pour récupérer l'auteur
        # en une seule requête (utilisé par le serializer pour afficher
        # username / email dans la liste).
        qs = Reclamation.objects.select_related('etudiant').order_by('-date_creation')

        # --- Filtres [S4.2] ---
        # Les filtres sont optionnels et cumulables. Aucun filtre = liste
        # complète. Les valeurs invalides retournent simplement une liste vide.
        categorie = request.query_params.get('categorie')
        statut = request.query_params.get('statut')

        if categorie:
            qs = qs.filter(categorie=categorie)
        if statut:
            qs = qs.filter(statut=statut)

        serializer = ReclamationListSerializer(qs, many=True)
        return Response(serializer.data)


class ReclamationDetailView(APIView):
    """
    [S4.3] Détail d'une réclamation + mise à jour du statut.
    [S4.4] Ajout d'une réponse de l'administrateur.

    GET  /api/reclamations/<pk>/
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_reclamation(self, pk):
        try:
            # prefetch des messages pour afficher le fil de discussion
            # complet sans déclencher une requête par message.
            return Reclamation.objects.prefetch_related('messages__auteur').get(pk=pk)
        except Reclamation.DoesNotExist:
            return None

    def get(self, request, pk):
        reclamation = self._get_reclamation(pk)
        if reclamation is None:
            return Response({'detail': 'Réclamation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ReclamationDetailSerializer(reclamation)
        return Response(serializer.data)


class ReclamationStatutView(APIView):
    """
    [S4.3] Mise à jour du statut d'une réclamation.

    PATCH /api/reclamations/<pk>/statut/
    Body : { "statut": "en_cours" }
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        try:
            reclamation = Reclamation.objects.get(pk=pk)
        except Reclamation.DoesNotExist:
            return Response({'detail': 'Réclamation introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        # Le serializer vérifie que le statut envoyé fait bien partie
        # des valeurs autorisées (ChoiceField).
        serializer = StatutUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reclamation.statut = serializer.validated_data['statut']
        reclamation.save(update_fields=['statut', 'date_maj'])

        # On renvoie aussi le libellé lisible pour éviter au frontend de
        # devoir maintenir un mapping clé → libellé en parallèle.
        return Response({
            'detail': 'Statut mis à jour.',
            'statut': reclamation.statut,
            'statut_display': reclamation.get_statut_display(),
            'date_maj': reclamation.date_maj,
        })


class ReclamationReponseView(APIView):
    """
    [S4.4] Ajouter une réponse de l'administrateur à une réclamation.

    POST /api/reclamations/<pk>/reponse/
    Body : { "contenu": "Votre réclamation a été traitée…" }
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            reclamation = Reclamation.objects.get(pk=pk)
        except Reclamation.DoesNotExist:
            return Response({'detail': 'Réclamation introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ReponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # L'auteur du message est forcé à l'utilisateur authentifié : on
        # ne fait pas confiance à un éventuel champ "auteur" envoyé par
        # le client.
        message = Message.objects.create(
            reclamation=reclamation,
            auteur=request.user,
            contenu=serializer.validated_data['contenu'],
        )

        return Response({
            'detail': 'Réponse ajoutée.',
            'message_id': message.id,
            'date': message.date,
        }, status=status.HTTP_201_CREATED)


class DashboardView(APIView):
    """
    [S4.5] Tableau de bord — statistiques globales pour l'administration.

    GET /api/reclamations/dashboard/
    Retourne :
      - total des réclamations
      - répartition par statut
      - répartition par catégorie
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        total = Reclamation.objects.count()

        # Agrégations SQL : on regroupe en base plutôt que de tout charger
        # en mémoire, ce qui passe à l'échelle même avec beaucoup de dossiers.
        par_statut = (
            Reclamation.objects
            .values('statut')
            .annotate(count=Count('id'))
            .order_by('statut')
        )

        par_categorie = (
            Reclamation.objects
            .values('categorie')
            .annotate(count=Count('id'))
            .order_by('categorie')
        )

        # Enrichissement avec les libellés lisibles : le frontend peut
        # afficher "Notes" plutôt que "notes" sans dupliquer le mapping.
        statut_map = dict(Reclamation.STATUT_CHOICES)
        categorie_map = dict(Reclamation.CATEGORIE_CHOICES)

        return Response({
            'total': total,
            'par_statut': [
                {'statut': row['statut'], 'label': statut_map.get(row['statut'], row['statut']), 'count': row['count']}
                for row in par_statut
            ],
            'par_categorie': [
                {'categorie': row['categorie'], 'label': categorie_map.get(row['categorie'], row['categorie']), 'count': row['count']}
                for row in par_categorie
            ],
        })
