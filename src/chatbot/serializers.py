# Serializers DRF du module chatbot.

from rest_framework import serializers

from .models import Conversation


class ConversationSerializer(serializers.ModelSerializer):
    # Toujours en lecture seule via l'API : la conversation n'évolue
    # qu'à travers les vues dédiées (start, message) qui appellent le
    # moteur de dialogue.
    class Meta:
        model = Conversation
        fields = ('id', 'etat', 'contexte', 'date_creation', 'date_maj')
        read_only_fields = fields


class MessageEntrantSerializer(serializers.Serializer):
    """Message envoyé par l'étudiant au chatbot."""

    # Les deux champs sont optionnels : un message contient soit une
    # action (clic sur bouton), soit un texte libre, jamais les deux à
    # la fois en pratique.
    action = serializers.CharField(required=False, allow_blank=True)
    texte = serializers.CharField(required=False, allow_blank=True)
