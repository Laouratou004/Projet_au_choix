# Modèle utilisateur personnalisé.
# On hérite d'AbstractUser pour conserver toutes les fonctionnalités natives
# de Django (mot de passe hashé, gestion de session, permissions...) tout en
# ajoutant un champ "role" qui distingue étudiants et administration.

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Utilisateur du système — étudiant ou administration."""

    # Constantes des rôles : on les expose comme attributs de classe pour
    # éviter les chaînes magiques ("etudiant", "admin") dispersées dans le code.
    ROLE_ETUDIANT = 'etudiant'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_ETUDIANT, 'Étudiant'),
        (ROLE_ADMIN, 'Administration'),
    ]

    # Le rôle par défaut est "etudiant" : c'est le rôle attribué à toute
    # personne qui s'inscrit via le formulaire public (/inscription/).
    # Les comptes "admin" sont créés manuellement par un superuser.
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_ETUDIANT,
    )

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        # Affichage lisible dans l'admin Django et les logs : nom complet si
        # disponible, sinon le username, suivi du rôle entre parenthèses.
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def est_etudiant(self):
        # Raccourci utilisé dans les templates et les vues pour éviter
        # d'écrire `user.role == 'etudiant'` partout.
        return self.role == self.ROLE_ETUDIANT

    @property
    def est_admin(self):
        # Idem pour le rôle administration.
        return self.role == self.ROLE_ADMIN
