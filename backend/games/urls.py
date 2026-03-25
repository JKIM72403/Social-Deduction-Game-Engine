from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RoleTemplateViewSet, AbilityTemplateViewSet, GameTemplateViewSet,
    PhaseTemplateViewSet, WinConditionTemplateViewSet,
    create_network_session, join_network_session,
    network_session_snapshot, set_network_session_ready, start_network_session,
    submit_network_session_action,
    start_game_session, game_session_action,
    signup_view, login_view, me_view,
)

router = DefaultRouter()
router.register(r'roles', RoleTemplateViewSet)
router.register(r'abilities', AbilityTemplateViewSet)
router.register(r'game-templates', GameTemplateViewSet)
router.register(r'phases', PhaseTemplateViewSet)
router.register(r'win-conditions', WinConditionTemplateViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('sessions/', create_network_session, name='create_network_session'),
    path('sessions/join/', join_network_session, name='join_network_session'),
    path('sessions/<int:session_id>/snapshot/', network_session_snapshot, name='network_session_snapshot'),
    path('sessions/<int:session_id>/ready/', set_network_session_ready, name='set_network_session_ready'),
    path('sessions/<int:session_id>/start/', start_network_session, name='start_network_session'),
    path('sessions/<int:session_id>/actions/', submit_network_session_action, name='submit_network_session_action'),
    path('game-sessions/', start_game_session, name='start_game_session'),
    path('game-sessions/<str:session_id>/act/', game_session_action, name='game_session_action'),
    path('auth/signup/', signup_view, name='signup'),
    path('auth/login/', login_view, name='login'),
    path('auth/me/', me_view, name='me'),
]
