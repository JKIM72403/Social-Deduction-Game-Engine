from django.urls import path

from .consumers import GameSessionConsumer


websocket_urlpatterns = [
    path("ws/sessions/<int:session_id>/", GameSessionConsumer.as_asgi()),
]
