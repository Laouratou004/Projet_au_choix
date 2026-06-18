# API REST du chatbot. Réservée aux étudiants.
# Le frontend communique avec ces endpoints en envoyant l'action de
# l'étudiant (clic sur un bouton) ou son texte libre ; le serveur calcule
# la nouvelle réponse du bot via le moteur de dialogue (engine.py).

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsEtudiant

from .engine import reponse_pour, traiter_message
from .models import Conversation
from .serializers import ConversationSerializer, MessageEntrantSerializer


def _payload(conversation, reponse):
    """Assemble la réponse JSON renvoyée à l'étudiant."""
    # Format unique partagé par toutes les vues : on renvoie à la fois
    # l'état brut de la conversation (pour suivi côté client) et la
    # réponse calculée du bot (message + options).
    return {
        'conversation': ConversationSerializer(conversation).data,
        'bot': reponse,
    }


class StartConversationView(APIView):
    """Démarre une nouvelle conversation et renvoie le message d'accueil."""

    permission_classes = [IsAuthenticated, IsEtudiant]

    def post(self, request):
        # On laisse la valeur par défaut ETAT_ACCUEIL : reponse_pour()
        # renverra automatiquement le message de bienvenue.
        conversation = Conversation.objects.create(etudiant=request.user)
        return Response(_payload(conversation, reponse_pour(conversation)), status=201)


class MessageView(APIView):
    """Envoie un message (action ou texte) à une conversation existante."""

    permission_classes = [IsAuthenticated, IsEtudiant]

    def post(self, request, pk):
        # Filtre etudiant=request.user : empêche l'accès aux conversations
        # d'un autre utilisateur même en devinant un id.
        conversation = get_object_or_404(
            Conversation, pk=pk, etudiant=request.user,
        )
        serializer = MessageEntrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # action = clic sur un bouton (ex: 'deposer', 'confirmer')
        # texte  = saisie libre (description, précision, référence...)
        reponse = traiter_message(
            conversation,
            action=serializer.validated_data.get('action', ''),
            texte=serializer.validated_data.get('texte', ''),
        )
        return Response(_payload(conversation, reponse))


class MesConversationsView(APIView):
    """Liste les conversations passées de l'étudiant connecté.

    Renvoie un résumé : id, état courant, dates, et la référence
    éventuelle de la réclamation déposée.
    """

    permission_classes = [IsAuthenticated, IsEtudiant]

    def get(self, request):
        conversations = Conversation.objects.filter(etudiant=request.user)
        # Sérialisation manuelle pour ne renvoyer qu'un résumé léger
        # (le contenu complet du contexte n'est pas utile dans la liste).
        data = [
            {
                'id': c.pk,
                'etat': c.etat,
                'etat_display': c.get_etat_display(),
                'date_creation': c.date_creation.isoformat(),
                'date_maj': c.date_maj.isoformat(),
                'reference': c.contexte.get('reference'),
                'categorie': c.contexte.get('categorie'),
            }
            for c in conversations
        ]
        return Response(data)


class ConversationDetailView(APIView):
    """Renvoie l'état courant d'une conversation pour reprise ou consultation.

    Permet aussi à l'étudiant de supprimer sa conversation (DELETE).
    La suppression de la conversation n'affecte PAS la réclamation
    éventuellement déjà créée — c'est uniquement l'historique de chat.
    """

    permission_classes = [IsAuthenticated, IsEtudiant]

    def get(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk, etudiant=request.user)
        return Response(_payload(conversation, reponse_pour(conversation)))

    def delete(self, request, pk):
        # Pas de CASCADE vers Reclamation : la réclamation déjà créée est
        # conservée car elle suit son propre cycle de vie côté admin.
        conversation = get_object_or_404(Conversation, pk=pk, etudiant=request.user)
        conversation.delete()
        return Response(status=204)
