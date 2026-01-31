from django.shortcuts import render

from rest_framework import viewsets
from .models import RoleTemplate, AbilityTemplate, GameTemplate
from .serializers import RoleTemplateSerializer, AbilityTemplateSerializer, GameTemplateSerializer


class AbilityTemplateViewSet(viewsets.ModelViewSet):
    queryset = AbilityTemplate.objects.all()
    serializer_class = AbilityTemplateSerializer


class RoleTemplateViewSet(viewsets.ModelViewSet):
    queryset = RoleTemplate.objects.all()
    serializer_class = RoleTemplateSerializer


class GameTemplateViewSet(viewsets.ModelViewSet):
    queryset = GameTemplate.objects.all()
    serializer_class = GameTemplateSerializer
