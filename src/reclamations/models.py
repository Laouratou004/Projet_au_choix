from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


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

    REFERENCE_PREFIXE = 'REC'

    reference = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text='Référence lisible, ex. REC-2026-001 (générée automatiquement).',
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

    # ---------- Référence (S2.4) ----------

    @classmethod
    def generer_reference(cls, annee=None):
        """Renvoie la prochaine référence disponible pour l'année donnée.

        Format : REC-AAAA-NNN (compteur réinitialisé chaque année,
        sur 3 chiffres minimum).
        """
        annee = annee or timezone.now().year
        prefixe = f"{cls.REFERENCE_PREFIXE}-{annee}-"
        # Lecture du dernier numéro pour cette année, ordonné par référence.
        derniere = (
            cls.objects.filter(reference__startswith=prefixe)
            .order_by('-reference')
            .first()
        )
        if derniere is None:
            prochain = 1
        else:
            try:
                prochain = int(derniere.reference.removeprefix(prefixe)) + 1
            except ValueError:
                prochain = cls.objects.filter(reference__startswith=prefixe).count() + 1
        return f"{prefixe}{prochain:03d}"

    def save(self, *args, **kwargs):
        """Assigne automatiquement une référence si elle est vide ou temporaire."""
        if not self.reference or self.reference.startswith('TMP-'):
            with transaction.atomic():
                self.reference = type(self).generer_reference()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


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
