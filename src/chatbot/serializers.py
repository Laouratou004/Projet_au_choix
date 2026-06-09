from rest_framework import serializers

from .models import Conversation


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ('id', 'etat', 'contexte', 'date_creation', 'date_maj')
        read_only_fields = fields


class MessageEntrantSerializer(serializers.Serializer):
    """Message envoyé par l'étudiant au chatbot."""

    action = serializers.CharField(required=False, allow_blank=True)
    texte = serializers.CharField(required=False, allow_blank=True)
