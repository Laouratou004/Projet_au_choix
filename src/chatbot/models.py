from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """Session de conversation entre un étudiant et le chatbot.

    Le chatbot fonctionne en parcours guidé (machine à états).
    `etat` indique l'étape courante du dialogue ; `contexte` accumule
    les données saisies par l'étudiant tout au long de la conversation.
    """

    ETAT_ACCUEIL = 'accueil'
    ETAT_CHOIX_ACTION = 'choix_action'
    ETAT_CATEGORIE_DEMANDEE = 'categorie_demandee'
    ETAT_DESCRIPTION_POUR_SUGGESTION = 'description_pour_suggestion'
    ETAT_SUGGESTION_PROPOSEE = 'suggestion_proposee'
    ETAT_DESCRIPTION_DEMANDEE = 'description_demandee'
    ETAT_DETAILS_DEMANDES = 'details_demandes'
    ETAT_RECAPITULATIF = 'recapitulatif'
    ETAT_SUIVI_REF_DEMANDEE = 'suivi_ref_demandee'
    ETAT_TERMINEE = 'terminee'
    ETAT_CHOICES = [
        (ETAT_ACCUEIL, 'Accueil'),
        (ETAT_CHOIX_ACTION, "Choix de l'action"),
        (ETAT_CATEGORIE_DEMANDEE, 'Catégorie demandée'),
        (ETAT_DESCRIPTION_POUR_SUGGESTION, 'Description pour suggestion'),
        (ETAT_SUGGESTION_PROPOSEE, 'Suggestion proposée'),
        (ETAT_DESCRIPTION_DEMANDEE, 'Description demandée'),
        (ETAT_DETAILS_DEMANDES, 'Précisions demandées'),
        (ETAT_RECAPITULATIF, 'Récapitulatif'),
        (ETAT_SUIVI_REF_DEMANDEE, 'Référence de suivi demandée'),
        (ETAT_TERMINEE, 'Terminée'),
    ]

    etudiant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations',
    )
    etat = models.CharField(max_length=30, choices=ETAT_CHOICES, default=ETAT_ACCUEIL)
    contexte = models.JSONField(default=dict, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        ordering = ['-date_creation']

    def __str__(self):
        return f"Conv #{self.pk} — {self.etudiant} — {self.get_etat_display()}"
