from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Utilisateur du système — étudiant ou administration."""

    ROLE_ETUDIANT = 'etudiant'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_ETUDIANT, 'Étudiant'),
        (ROLE_ADMIN, 'Administration'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_ETUDIANT,
    )

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def est_etudiant(self):
        return self.role == self.ROLE_ETUDIANT

    @property
    def est_admin(self):
        return self.role == self.ROLE_ADMIN
