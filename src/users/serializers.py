# Serializers DRF : convertissent les objets User en JSON (et inversement),
# avec validation des données entrantes lors des appels API.

from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Représentation publique d'un utilisateur."""

    class Meta:
        model = User
        # Champs exposés au frontend. Volontairement restreint : on n'expose
        # ni le mot de passe (même hashé), ni les permissions internes Django.
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role')
        # id et role ne peuvent pas être modifiés via l'API publique : le
        # rôle est fixé à la création par RegisterSerializer.
        read_only_fields = ('id', 'role')


class RegisterSerializer(serializers.ModelSerializer):
    """Inscription d'un étudiant. Le rôle est forcé à 'etudiant'."""

    # write_only : le mot de passe ne doit jamais être renvoyé dans la
    # réponse JSON. min_length=6 : règle minimale de sécurité.
    password = serializers.CharField(write_only=True, min_length=6, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password')

    def create(self, validated_data):
        # create_user (et non User.objects.create) prend en charge le hashage
        # du mot de passe avant insertion en base.
        return User.objects.create_user(
            role=User.ROLE_ETUDIANT,
            **validated_data,
        )


class LoginSerializer(serializers.Serializer):
    """Authentification par username + mot de passe."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        # authenticate() vérifie le mot de passe via le backend Django
        # configuré et renvoie None en cas d'échec.
        user = authenticate(
            request=self.context.get('request'),
            username=attrs['username'],
            password=attrs['password'],
        )
        if user is None:
            # Message volontairement générique : on ne précise pas si c'est
            # le username ou le mot de passe qui est faux (sécurité).
            raise serializers.ValidationError('Identifiants invalides.')
        if not user.is_active:
            # Un admin peut désactiver un compte sans le supprimer.
            raise serializers.ValidationError('Compte désactivé.')
        # On range l'objet user dans attrs pour que la vue puisse le récupérer
        # via serializer.validated_data['user'].
        attrs['user'] = user
        return attrs
