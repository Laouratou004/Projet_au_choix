# Serializers DRF : transformation Reclamation/Message <-> JSON.
# On distingue volontairement plusieurs serializers :
#   - liste légère pour les écrans tableau (ReclamationListSerializer)
#   - détail complet avec fil de messages (ReclamationDetailSerializer)
#   - formulaires dédiés (StatutUpdateSerializer, ReponseSerializer)
# Ce découpage évite de surcharger l'API avec des champs inutiles selon
# le contexte.

from rest_framework import serializers

from .models import Message, Reclamation


class MessageSerializer(serializers.ModelSerializer):
    """Sérialisation d'un message / réponse sur une réclamation."""

    # On expose le username de l'auteur sans inclure tout l'objet User
    # (évite d'exposer email, rôle, etc. dans les listes publiques).
    auteur_username = serializers.ReadOnlyField(source='auteur.username')

    class Meta:
        model = Message
        fields = ['id', 'auteur_username', 'contenu', 'date']
        read_only_fields = ['id', 'auteur_username', 'date']


class ReclamationListSerializer(serializers.ModelSerializer):
    """Sérialisation légère pour la liste — [S4.1]."""

    # Champs dérivés : on duplique les libellés lisibles côté API pour
    # que le frontend n'ait pas besoin de maintenir un mapping clé→libellé.
    etudiant_username = serializers.ReadOnlyField(source='etudiant.username')
    etudiant_email = serializers.ReadOnlyField(source='etudiant.email')
    statut_display = serializers.ReadOnlyField(source='get_statut_display')
    categorie_display = serializers.ReadOnlyField(source='get_categorie_display')

    class Meta:
        model = Reclamation
        # Pas de description ici : la liste n'affiche que les métadonnées,
        # on ouvre le détail pour lire le contenu.
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
    # Nested : tous les messages du fil sont inclus dans la réponse.
    # Triés par date (cf. Meta.ordering du modèle Message).
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
        # Tout est en lecture seule via ce serializer : les modifications
        # passent par des endpoints dédiés (StatutUpdate, Reponse...).
        read_only_fields = [
            'id', 'reference', 'categorie', 'description',
            'etudiant_username', 'etudiant_email', 'messages',
            'date_creation', 'date_maj',
        ]


class StatutUpdateSerializer(serializers.Serializer):
    """Mise à jour du statut uniquement — [S4.3]."""

    # Liste des valeurs autorisées, dérivée du modèle pour rester
    # synchronisée si on ajoute un nouveau statut.
    STATUTS_VALIDES = [s for s, _ in Reclamation.STATUT_CHOICES]

    # ChoiceField rejette automatiquement toute valeur hors de la liste.
    statut = serializers.ChoiceField(choices=Reclamation.STATUT_CHOICES)


class ReponseSerializer(serializers.Serializer):
    """Ajout d'une réponse de l'administrateur — [S4.4]."""

    # min_length=1 : on rejette les messages vides. max_length=2000 :
    # garde-fou pour éviter qu'un admin colle un texte démesuré.
    contenu = serializers.CharField(min_length=1, max_length=2000)
