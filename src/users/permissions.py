# Permissions DRF personnalisées. Utilisées par les ViewSets de reclamations
# et chatbot pour restreindre l'accès selon le rôle de l'utilisateur.

from rest_framework.permissions import BasePermission

from .models import User


class IsAdmin(BasePermission):
    """Réservé aux utilisateurs habilités à administrer l'application.

    Accepte aussi bien :
    - les superusers / staff (Django superadmin créés via createsuperuser)
    - les utilisateurs avec role='admin' (administrateurs de l'université
      créés via /admin/ par un superadmin)

    Cohérent avec _est_admin_univ() côté frontend.
    """

    # Message renvoyé dans la réponse 403 si la permission échoue.
    message = "Accès réservé à l'administration."

    def has_permission(self, request, view):
        user = request.user
        # Premier filtre : il faut être connecté. AnonymousUser n'a pas
        # d'attribut role, donc on coupe court.
        if not (user and user.is_authenticated):
            return False
        # On accepte trois cas : superuser, staff, ou rôle métier "admin".
        # Cette combinaison est volontaire pour que les superadmins Django
        # gardent toujours accès à l'application, même sans rôle métier.
        return bool(user.is_staff or user.is_superuser or user.role == User.ROLE_ADMIN)


class IsEtudiant(BasePermission):
    """Réservé aux utilisateurs avec le rôle étudiant.

    Un staff/superuser est explicitement exclu — son espace est
    /administration/, pas /etudiant/.
    """

    message = 'Accès réservé aux étudiants.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        # Exclusion stricte du staff : éviter qu'un admin se retrouve par
        # erreur dans le flux étudiant et perturbe ses propres réclamations.
        if user.is_staff or user.is_superuser:
            return False
        return user.role == User.ROLE_ETUDIANT
