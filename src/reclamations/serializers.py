from rest_framework import serializers

from .models import Message, Reclamation


class MessageSerializer(serializers.ModelSerializer):
    """Sérialisation d'un message / réponse sur une réclamation."""

    auteur_username = serializers.ReadOnlyField(source='auteur.username')

    class Meta:
        model = Message
        fields = ['id', 'auteur_username', 'contenu', 'date']
        read_only_fields = ['id', 'auteur_username', 'date']


class ReclamationListSerializer(serializers.ModelSerializer):
    """Sérialisation légère pour la liste — [S4.1]."""

    etudiant_username = serializers.ReadOnlyField(source='etudiant.username')
    etudiant_email = serializers.ReadOnlyField(source='etudiant.email')
    statut_display = serializers.ReadOnlyField(source='get_statut_display')
    categorie_display = serializers.ReadOnlyField(source='get_categorie_display')

    class Meta:
        model = Reclamation
        fields = [
            'id',
            'reference',
            'categorie',
            'categorie_display',
            'statut',
            'statut_display',
            'etudiant_username',
            'etudiant_email',
            'date_creation',
            'date_maj',
        ]


class ReclamationDetailSerializer(serializers.ModelSerializer):
    """Sérialisation complète avec messages — [S4.3] [S4.4]."""

    etudiant_username = serializers.ReadOnlyField(source='etudiant.username')
    etudiant_email = serializers.ReadOnlyField(source='etudiant.email')
    statut_display = serializers.ReadOnlyField(source='get_statut_display')
    categorie_display = serializers.ReadOnlyField(source='get_categorie_display')
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Reclamation
        fields = [
            'id',
            'reference',
            'categorie',
            'categorie_display',
            'description',
            'statut',
            'statut_display',
            'etudiant_username',
            'etudiant_email',
            'messages',
            'date_creation',
            'date_maj',
        ]
        read_only_fields = [
            'id', 'reference', 'categorie', 'description',
            'etudiant_username', 'etudiant_email', 'messages',
            'date_creation', 'date_maj',
        ]


class StatutUpdateSerializer(serializers.Serializer):
    """Mise à jour du statut uniquement — [S4.3]."""

    STATUTS_VALIDES = [s for s, _ in Reclamation.STATUT_CHOICES]

    statut = serializers.ChoiceField(choices=Reclamation.STATUT_CHOICES)


class ReponseSerializer(serializers.Serializer):
    """Ajout d'une réponse de l'administrateur — [S4.4]."""

    contenu = serializers.CharField(min_length=1, max_length=2000)
