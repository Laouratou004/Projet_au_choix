from django.conf import settings
from django.db import models


class Reclamation(models.Model):
    """Réclamation académique déposée par un étudiant."""

    CAT_NOTES = 'notes'
    CAT_SCOLARITE = 'scolarite'
    CAT_EXAMENS = 'examens'
    CAT_BOURSE = 'bourse'
    CATEGORIE_CHOICES = [
        (CAT_NOTES, 'Notes'),
        (CAT_SCOLARITE, 'Scolarité'),
        (CAT_EXAMENS, 'Examens'),
        (CAT_BOURSE, 'Bourse'),
    ]

    STATUT_SOUMISE = 'soumise'
    STATUT_EN_COURS = 'en_cours'
    STATUT_ATTENTE_INFO = 'attente_info'
    STATUT_RESOLUE = 'resolue'
    STATUT_CLOTUREE = 'cloturee'
    STATUT_CHOICES = [
        (STATUT_SOUMISE, 'Soumise'),
        (STATUT_EN_COURS, 'En cours'),
        (STATUT_ATTENTE_INFO, "En attente d'info"),
        (STATUT_RESOLUE, 'Résolue'),
        (STATUT_CLOTUREE, 'Clôturée'),
    ]

    reference = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text='Référence lisible, ex. REC-2026-001 (générée en S2.4).',
    )
    etudiant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reclamations',
    )
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES)
    description = models.TextField()
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=STATUT_SOUMISE,
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Réclamation'
        verbose_name_plural = 'Réclamations'
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.reference or '(sans réf)'} — {self.get_categorie_display()}"


class Message(models.Model):
    """Message ou réponse échangé sur une réclamation."""

    reclamation = models.ForeignKey(
        Reclamation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    contenu = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['date']

    def __str__(self):
        return f"Message de {self.auteur} le {self.date:%Y-%m-%d %H:%M}"
