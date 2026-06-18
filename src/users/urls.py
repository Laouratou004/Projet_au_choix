# Routes de l'API d'authentification. Préfixées par /api/users/ dans
# config/urls.py (ex : POST /api/users/login/).

from django.urls import path

from .views import LoginView, LogoutView, MeView, RegisterView

# Namespace : permet de référencer les URLs via "users:login" dans les
# templates ou les reverse() côté Python.
app_name = 'users'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),  # inscription étudiant
    path('login/', LoginView.as_view(), name='login'),           # connexion → token
    path('logout/', LogoutView.as_view(), name='logout'),        # révocation du token
    path('me/', MeView.as_view(), name='me'),                    # profil courant
]
