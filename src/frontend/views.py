from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import InscriptionForm


class ConnexionView(LoginView):
    """Page de connexion : redirige les étudiants vers le chatbot,
    les admins vers le tableau de bord."""

    template_name = 'frontend/connexion.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if getattr(user, 'est_admin', False) or user.is_staff:
            return '/administration/'
        return '/etudiant/'


class DeconnexionView(LogoutView):
    next_page = reverse_lazy('frontend:accueil')


def accueil(request):
    """Page d'accueil publique. Redirige si déjà connecté."""
    if request.user.is_authenticated:
        if request.user.is_staff or getattr(request.user, 'est_admin', False):
            return redirect('/administration/')
        return redirect('/etudiant/')
    return render(request, 'frontend/accueil.html')


def inscription(request):
    """Inscription d'un étudiant + connexion automatique."""
    if request.user.is_authenticated:
        return redirect('/etudiant/')
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return HttpResponseRedirect('/etudiant/')
    else:
        form = InscriptionForm()
    return render(request, 'frontend/inscription.html', {'form': form})


@login_required
def etudiant(request):
    """Page chatbot étudiant. Redirige les non-étudiants vers leur espace."""
    if request.user.is_staff or getattr(request.user, 'est_admin', False):
        return redirect('/administration/')
    return render(request, 'frontend/etudiant.html')


@login_required
def administration(request):
    """Tableau de bord administration. Réservé aux admins (role=admin ou is_staff)."""
    if not (request.user.is_staff or getattr(request.user, 'est_admin', False)):
        return redirect('/etudiant/')
    return render(request, 'frontend/administration.html')
