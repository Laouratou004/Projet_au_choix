# Routes de l'API chatbot. Préfixées par /api/chatbot/ dans config/urls.py.

from django.urls import path

from .views import (
    ConversationDetailView,
    MesConversationsView,
    MessageView,
    StartConversationView,
)

app_name = 'chatbot'

urlpatterns = [
    # POST → ouvre une nouvelle conversation, renvoie le message d'accueil.
    path('start/', StartConversationView.as_view(), name='start'),
    # GET → liste des conversations passées de l'étudiant.
    path('conversations/', MesConversationsView.as_view(), name='mes_conversations'),
    # GET/DELETE → consulter / supprimer une conversation.
    path('<int:pk>/', ConversationDetailView.as_view(), name='detail'),
    # POST → envoyer un message (action ou texte) au bot.
    path('<int:pk>/message/', MessageView.as_view(), name='message'),
]
