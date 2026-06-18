# Admin Django pour le module chatbot.
# Utile pour inspecter une conversation en cours de debug (état courant,
# contenu du contexte JSON, etc.).

from django.contrib import admin

from .models import Conversation


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'etudiant', 'etat', 'date_creation', 'date_maj')
    list_filter = ('etat', 'date_creation')
    search_fields = ('etudiant__username', 'etudiant__email')
    readonly_fields = ('date_creation', 'date_maj')
