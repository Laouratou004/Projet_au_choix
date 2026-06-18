# Formulaires Django (utilisés par les vues HTML du frontend).

from django import forms

from users.models import User


class CreationEtudiantForm(forms.ModelForm):
    """Formulaire utilisé par les admins de l'université pour créer un étudiant.

    Plus accessible publiquement : l'inscription libre a été retirée pour
    n'autoriser que les comptes créés par l'administration.
    """

    # Deux champs hors-modèle pour saisir et confirmer le mot de passe.
    # On ne peut pas réutiliser le champ "password" du modèle User car il
    # stocke un hash, pas un texte clair.
    password = forms.CharField(
        label='Mot de passe initial',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=6,
    )
    password2 = forms.CharField(
        label='Confirmer le mot de passe',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email')
        # Widgets : on attache "form-control" pour le style Bootstrap des
        # templates.
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        # Libellés en français (ceux générés par défaut sont en anglais).
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'username': "Nom d'utilisateur",
            'email': 'Adresse e-mail',
        }

    def clean(self):
        # Validation croisée : on vérifie ici car la confirmation ne
        # concerne pas un champ unique.
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password2'):
            raise forms.ValidationError('Les mots de passe ne correspondent pas.')
        return cleaned

    def save(self, commit=True):
        # commit=False : on récupère l'objet sans l'écrire pour appliquer
        # le hashage du mot de passe et forcer le rôle "étudiant" avant
        # le vrai save().
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        # Sécurité : on force le rôle, on ne fait pas confiance à un
        # éventuel champ caché injecté dans le formulaire.
        user.role = User.ROLE_ETUDIANT
        if commit:
            user.save()
        return user
