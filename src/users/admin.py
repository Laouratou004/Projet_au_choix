# Personnalisation de l'admin Django pour le modèle User.
# On étend UserAdmin (l'admin natif de Django) pour ajouter le champ "role"
# dans la liste, les filtres et les formulaires de création/édition.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Colonnes affichées dans la liste des utilisateurs (/admin/users/user/).
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    # Filtres latéraux pour trier rapidement par rôle ou statut.
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    # On ajoute une section "Rôle" au formulaire d'édition standard.
    fieldsets = UserAdmin.fieldsets + (
        ('Rôle', {'fields': ('role',)}),
    )
    # Idem pour le formulaire de création (sinon le champ est invisible).
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Rôle', {'fields': ('role',)}),
    )
