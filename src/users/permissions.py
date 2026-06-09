from rest_framework.permissions import BasePermission

from .models import User


class IsAdmin(BasePermission):
    """Réservé aux utilisateurs avec le rôle administration."""

    message = "Accès réservé à l'administration."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == User.ROLE_ADMIN)


class IsEtudiant(BasePermission):
    """Réservé aux utilisateurs avec le rôle étudiant."""

    message = 'Accès réservé aux étudiants.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == User.ROLE_ETUDIANT)
