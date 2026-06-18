# Modèles métier du module "réclamations".
# Une Reclamation représente le dossier déposé par un étudiant ; un Message
# représente chaque échange (description initiale, réponse admin, demande
# d'info complémentaire...) attaché à ce dossier.

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class Reclamation(models.Model):
    """Réclamation académique déposée par un étudiant."""

    # Catégories métier — alignées avec le cahier des charges (section 2).
    # On définit les valeurs en constantes pour éviter les chaînes magiques
    # et faciliter d'éventuelles renommages futurs.
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

    # Workflow d'une réclamation : soumise → en_cours → (attente_info) →
    # résolue → clôturée. Les transitions ne sont pas verrouillées au niveau
    # modèle (un admin peut choisir n'importe quel statut), mais l'UI guide
    # l'utilisateur.
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

    # Préfixe utilisé pour générer les références humaines (REC-AAAA-NNN).
    REFERENCE_PREFIXE = 'REC'

    # Référence affichée à l'étudiant (ex : REC-2026-001). Générée à la
    # sauvegarde si vide — voir save() plus bas. blank=True car le champ
    # n'est pas demandé dans le formulaire de création.
    reference = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text='Référence lisible, ex. REC-2026-001 (générée automatiquement).',
    )
    # Auteur de la réclamation. CASCADE : si l'étudiant est supprimé, ses
    # réclamations le sont aussi (conformité RGPD / droit à l'oubli).
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
    # auto_now_add : la date de création est fixée à la création et n'est
    # plus jamais modifiée. auto_now : mise à jour à chaque save().
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Réclamation'
        verbose_name_plural = 'Réclamations'
        # Tri par défaut : les plus récentes en premier (utilisé partout
        # dans les listes côté admin et étudiant).
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
        # On cherche la plus grande référence existante pour cette année.
        # Comme le format est zero-padded, l'ordre lexicographique
        # coïncide avec l'ordre numérique sur 3 chiffres.
        derniere = (
            cls.objects.filter(reference__startswith=prefixe)
            .order_by('-reference')
            .first()
        )
        if derniere is None:
            prochain = 1
        else:
            try:
                # Extraction du numéro et incrément.
                prochain = int(derniere.reference.removeprefix(prefixe)) + 1
            except ValueError:
                # Garde-fou : si la dernière référence a un format inattendu
                # (import, données corrompues), on retombe sur un comptage
                # brut pour ne pas crasher la création.
                prochain = cls.objects.filter(reference__startswith=prefixe).count() + 1
        # Padding à 3 chiffres : 001, 002, ..., 999, 1000 (au-delà,
        # l'ordre lexicographique casse, mais peu probable en pratique).
        return f"{prefixe}{prochain:03d}"

    def save(self, *args, **kwargs):
        """Assigne automatiquement une référence si elle est vide ou temporaire."""
        # Le préfixe TMP- est utilisé par certains flux (chatbot) pour créer
        # une réclamation provisoire avant validation finale.
        if not self.reference or self.reference.startswith('TMP-'):
            # Transaction atomique : on protège contre une race condition
            # où deux créations simultanées attribueraient le même numéro.
            with transaction.atomic():
                self.reference = type(self).generer_reference()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


class Message(models.Model):
    """Message ou réponse échangé sur une réclamation."""

    # related_name='messages' : on peut écrire reclamation.messages.all().
    reclamation = models.ForeignKey(
        Reclamation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    # Auteur du message : étudiant qui complète son dossier ou admin qui
    # répond. Le rôle se déduit de user.role au moment de l'affichage.
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
        # Ordre chronologique pour afficher la conversation dans l'ordre.
        ordering = ['date']

    def __str__(self):
        return f"Message de {self.auteur} le {self.date:%Y-%m-%d %H:%M}"
