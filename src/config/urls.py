"""URL configuration for the Projet_au_choix project."""
# pyrefly: ignore [missing-import]
from django.contrib import admin
# pyrefly: ignore [missing-import]
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/reclamations/', include('reclamations.urls')),
    path('api/chatbot/', include('chatbot.urls')),
    path('', include('frontend.urls')),
]
