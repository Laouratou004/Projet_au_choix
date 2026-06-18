# Configuration de l'admin Django pour les modèles du module réclamations.
# Permet à un superadmin de consulter et modifier directement les dossiers
# sans passer par l'interface étudiant/admin métier.

from django.contrib import admin

from .models import Message, Reclamation


class MessageInline(admin.TabularInline):
    # Affiche les messages d'une réclamation directement dans sa page admin,
    # sous forme de tableau (plutôt que sur une page séparée).
    model = Message
    extra = 0  # pas de lignes vides "ajouter un message" par défaut
    readonly_fields = ('date',)


@admin.register(Reclamation)
class ReclamationAdmin(admin.ModelAdmin):
    list_display = ('reference', 'categorie', 'statut', 'etudiant', 'date_creation', 'date_maj')
    list_filter = ('statut', 'categorie', 'date_creation')
    # Recherche multi-champs, y compris dans les attributs de l'étudiant
    # (double underscore = jointure FK).
    search_fields = ('reference', 'description', 'etudiant__username', 'etudiant__email')
    readonly_fields = ('date_creation', 'date_maj')
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('reclamation', 'auteur', 'date')
    list_filter = ('date',)
    search_fields = ('contenu', 'reclamation__reference')
    readonly_fields = ('date',)
