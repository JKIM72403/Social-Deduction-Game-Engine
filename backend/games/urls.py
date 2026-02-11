from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoleTemplateViewSet, AbilityTemplateViewSet, GameTemplateViewSet

router = DefaultRouter()
router.register(r'roles', RoleTemplateViewSet)
router.register(r'abilities', AbilityTemplateViewSet)
router.register(r'game-templates', GameTemplateViewSet)

urlpatterns = [
    path('', include(router.urls)),
]


