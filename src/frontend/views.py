from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import CreationEtudiantForm


def _est_admin_univ(user):
    """Admin métier (rôle 'admin' OU is_staff)."""
    return user.is_staff or getattr(user, 'est_admin', False)


class ConnexionView(LoginView):
    """Page de connexion : redirige les étudiants vers le chatbot,
    les admins vers le tableau de bord."""

    template_name = 'frontend/connexion.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        if _est_admin_univ(self.request.user):
            return '/administration/'
        return '/etudiant/'


class DeconnexionView(LogoutView):
    next_page = reverse_lazy('frontend:accueil')


def accueil(request):
    """Page d'accueil publique. Redirige si déjà connecté."""
    if request.user.is_authenticated:
        if _est_admin_univ(request.user):
            return redirect('/administration/')
        return redirect('/etudiant/')
    return render(request, 'frontend/accueil.html')


@login_required
def etudiant(request):
    """Page chatbot étudiant. Redirige les non-étudiants vers leur espace."""
    if _est_admin_univ(request.user):
        return redirect('/administration/')
    return render(request, 'frontend/etudiant.html')


@login_required
def administration(request):
    """Tableau de bord administration. Réservé aux admins."""
    if not _est_admin_univ(request.user):
        return redirect('/etudiant/')
    return render(request, 'frontend/administration.html')


@login_required
def creer_etudiant(request):
    """Création d'un compte étudiant par un administrateur."""
    if not _est_admin_univ(request.user):
        return redirect('/etudiant/')
    if request.method == 'POST':
        form = CreationEtudiantForm(request.POST)
        if form.is_valid():
            etudiant_cree = form.save()
            messages.success(
                request,
                f"Compte étudiant créé : {etudiant_cree.username} "
                f"({etudiant_cree.get_full_name() or etudiant_cree.email})."
            )
            return redirect('frontend:creer_etudiant')
    else:
        form = CreationEtudiantForm()
    return render(request, 'frontend/creer_etudiant.html', {'form': form})
