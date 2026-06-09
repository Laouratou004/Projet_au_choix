from django.contrib import admin

from .models import Message, Reclamation


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('date',)


@admin.register(Reclamation)
class ReclamationAdmin(admin.ModelAdmin):
    list_display = ('reference', 'categorie', 'statut', 'etudiant', 'date_creation', 'date_maj')
    list_filter = ('statut', 'categorie', 'date_creation')
    search_fields = ('reference', 'description', 'etudiant__username', 'etudiant__email')
    readonly_fields = ('date_creation', 'date_maj')
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('reclamation', 'auteur', 'date')
    list_filter = ('date',)
    search_fields = ('contenu', 'reclamation__reference')
    readonly_fields = ('date',)
