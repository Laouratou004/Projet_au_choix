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
    return {
        'conversation': ConversationSerializer(conversation).data,
        'bot': reponse,
    }


class StartConversationView(APIView):
    """Démarre une nouvelle conversation et renvoie le message d'accueil."""

    permission_classes = [IsAuthenticated, IsEtudiant]

    def post(self, request):
        conversation = Conversation.objects.create(etudiant=request.user)
        return Response(_payload(conversation, reponse_pour(conversation)), status=201)


class MessageView(APIView):
    """Envoie un message (action ou texte) à une conversation existante."""

    permission_classes = [IsAuthenticated, IsEtudiant]

    def post(self, request, pk):
        conversation = get_object_or_404(
            Conversation, pk=pk, etudiant=request.user,
        )
        serializer = MessageEntrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reponse = traiter_message(
            conversation,
            action=serializer.validated_data.get('action', ''),
            texte=serializer.validated_data.get('texte', ''),
        )
        return Response(_payload(conversation, reponse))
