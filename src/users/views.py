# Vues d'authentification basées sur Django REST Framework.
# Elles exposent l'API JSON consommée par le frontend (templates HTML +
# fetch) pour l'inscription, la connexion, la déconnexion et la récupération
# du profil de l'utilisateur courant.

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


class RegisterView(APIView):
    """Inscription d'un étudiant. Renvoie un token directement utilisable."""

    # Accès libre : pas besoin d'être authentifié pour s'inscrire.
    permission_classes = [AllowAny]

    def post(self, request):
        # Validation des données reçues (username, mot de passe, etc.).
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # On génère immédiatement un token pour éviter à l'utilisateur de
        # devoir refaire un appel de login juste après son inscription.
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {'token': token.key, 'user': UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Connexion par username + mot de passe → renvoie le token et le rôle."""

    permission_classes = [AllowAny]

    def post(self, request):
        # Le serializer délègue l'authentification à django.contrib.auth, ce
        # qui garantit la prise en compte du hashage de mot de passe et des
        # éventuels backends configurés.
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        # get_or_create : on réutilise le token existant s'il y en a un, sinon
        # on en crée un nouveau. Ainsi un utilisateur peut rester connecté
        # depuis plusieurs onglets sans invalider sa session ailleurs.
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': UserSerializer(user).data})


class LogoutView(APIView):
    """Révoque le token de l'utilisateur courant."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Supprimer le token côté serveur invalide immédiatement la session
        # API : tout appel ultérieur avec ce token sera refusé en 401.
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Renvoie les infos de l'utilisateur connecté."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Utilisée par le frontend pour vérifier la session et afficher le
        # nom / rôle dans la barre de navigation.
        return Response(UserSerializer(request.user).data)
