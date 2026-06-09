from django.urls import path

from .views import MessageView, StartConversationView

app_name = 'chatbot'

urlpatterns = [
    path('start/', StartConversationView.as_view(), name='start'),
    path('<int:pk>/message/', MessageView.as_view(), name='message'),
]
