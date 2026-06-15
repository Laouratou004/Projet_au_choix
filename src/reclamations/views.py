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
        return Reclamation.objects.filter(pk=pk, etudiant=request.user).first()

    def patch(self, request, pk):
        reclamation = self._get(request, pk)
        if reclamation is None:
            return Response({'detail': 'Réclamation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if reclamation.statut != Reclamation.STATUT_SOUMISE:
            return Response(
                {'detail': "Modification impossible : votre réclamation est déjà en cours de traitement."},
                status=status.HTTP_409_CONFLICT,
            )
        description = (request.data.get('description') or '').strip()
        if len(description) < 5:
            return Response(
                {'detail': 'La description doit contenir au moins 5 caractères.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reclamation.description = description
        reclamation.save(update_fields=['description', 'date_maj'])
        return Response({'detail': 'Réclamation mise à jour.'})

    def delete(self, request, pk):
        reclamation = self._get(request, pk)
        if reclamation is None:
            return Response({'detail': 'Réclamation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
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
        qs = Reclamation.objects.select_related('etudiant').order_by('-date_creation')

        # --- Filtres [S4.2] ---
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

        serializer = StatutUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reclamation.statut = serializer.validated_data['statut']
        reclamation.save(update_fields=['statut', 'date_maj'])

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

        # Enrichissement avec les libellés lisibles
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
