from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RoleTemplateViewSet, AbilityTemplateViewSet, GameTemplateViewSet,
    start_game_session, game_session_action,
    signup_view, login_view, me_view,
)

router = DefaultRouter()
router.register(r'roles', RoleTemplateViewSet)
router.register(r'abilities', AbilityTemplateViewSet)
router.register(r'game-templates', GameTemplateViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('game-sessions/', start_game_session, name='start_game_session'),
    path('game-sessions/<str:session_id>/act/', game_session_action, name='game_session_action'),
    path('auth/signup/', signup_view, name='signup'),
    path('auth/login/', login_view, name='login'),
    path('auth/me/', me_view, name='me'),
]
