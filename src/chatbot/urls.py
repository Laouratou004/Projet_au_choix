from django.urls import path

from .views import (
    ConversationDetailView,
    MesConversationsView,
    MessageView,
    StartConversationView,
)

app_name = 'chatbot'

urlpatterns = [
    path('start/', StartConversationView.as_view(), name='start'),
    path('conversations/', MesConversationsView.as_view(), name='mes_conversations'),
    path('<int:pk>/', ConversationDetailView.as_view(), name='detail'),
    path('<int:pk>/message/', MessageView.as_view(), name='message'),
]
