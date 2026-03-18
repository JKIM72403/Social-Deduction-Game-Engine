from django.shortcuts import render
from django.contrib.auth import authenticate
import uuid
import random
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .models import RoleTemplate, AbilityTemplate, GameTemplate, PhaseTemplate, WinConditionTemplate
from .serializers import (
    RoleTemplateSerializer, AbilityTemplateSerializer, GameTemplateSerializer,
    PhaseTemplateSerializer, WinConditionTemplateSerializer,
    UserSerializer, SignupSerializer, LoginSerializer,
)
from .engine_builder import build_game_engine
from .engine import PhaseState, GameEngine, Alignment

# --- Auth Views ---

@api_view(['POST'])
@permission_classes([AllowAny])
def signup_view(request):
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = authenticate(username=serializer.validated_data['username'], password=serializer.validated_data['password'])
    if not user:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': UserSerializer(user).data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)

class AbilityTemplateViewSet(viewsets.ModelViewSet):
    queryset = AbilityTemplate.objects.all()
    serializer_class = AbilityTemplateSerializer

class RoleTemplateViewSet(viewsets.ModelViewSet):
    queryset = RoleTemplate.objects.all()
    serializer_class = RoleTemplateSerializer

from django.db.models import Q

class GameTemplateViewSet(viewsets.ModelViewSet):
    queryset = GameTemplate.objects.all()
    serializer_class = GameTemplateSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return GameTemplate.objects.filter(Q(is_public=True) | Q(creator=user)).distinct()
        return GameTemplate.objects.filter(is_public=True)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(creator=self.request.user)
        else:
            serializer.save()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.creator and instance.creator != request.user:
            return Response({'error': 'Not the owner'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.creator and instance.creator != request.user:
            return Response({'error': 'Not the owner'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

# In-memory store for active game sessions
ACTIVE_GAMES = {}

def serialize_game_state(session_id, engine, user_name):
    user_player = engine.get_player(user_name)

    players = []
    for p in engine.players:
        # Hide roles for other alive players
        reveal_role = not p.is_alive or p.name == user_name
        players.append({
            "name": p.name,
            "is_alive": p.is_alive,
            "role": p.role.name if reveal_role else "Unknown",
            "alignment": p.role.alignment.value if reveal_role else "Unknown"
        })

    abilities = []
    if user_player and user_player.is_alive and user_player.role.abilities:
        for i, ab in enumerate(user_player.role.abilities):
            abilities.append({"index": i, "name": ab.name})

    return {
        "session_id": session_id,
        "phase": engine.phase_state.value,
        "turn": engine.turn_number,
        "players": players,
        "me": {
            "name": user_name,
            "is_alive": user_player.is_alive if user_player else False,
            "role": user_player.role.name if user_player else "Observer",
            "alignment": user_player.role.alignment.value if user_player else "Unknown",
            "abilities": abilities
        },
        "logs": list(engine.events)
    }

@api_view(['POST'])
def start_game_session(request):
    template_id = request.data.get('template_id')
    user_name = request.data.get('user_name', 'You')

    try:
        template = GameTemplate.objects.get(id=template_id)
        if not template.is_public:
            if not request.user.is_authenticated or template.creator != request.user:
                return Response({"error": "Template not found or private"}, status=404)
    except GameTemplate.DoesNotExist:
        return Response({"error": "Template not found"}, status=404)

    slots = template.role_slots.all()
    # Ensure there's a human user among the slots? The demo says "bots as other players"
    # To assign the human user, we randomly pick one of the roles for them.
    # The build_game_engine assigns roles deterministically if zip is used.
    total_slots = sum(slot.count for slot in slots)

    if total_slots < 1:
        return Response({"error": "Template has no roles"}, status=400)

    # Generate player names
    player_names = [user_name]
    for i in range(1, total_slots):
        player_names.append(f"Bot {i}")

    # Build engine
    engine = build_game_engine(template, player_names)
    engine.start_game() # Transitions to NIGHT

    session_id = str(uuid.uuid4())
    ACTIVE_GAMES[session_id] = engine

    return Response(serialize_game_state(session_id, engine, user_name))

@api_view(['POST'])
def game_session_action(request, session_id):
    if session_id not in ACTIVE_GAMES:
        return Response({"error": "Session not found"}, status=404)

    engine = ACTIVE_GAMES[session_id]
    user_name = request.data.get('user_name', 'You')
    action_data = request.data.get('action', {})

    # Check if the game is already over
    if engine.phase_state == PhaseState.GAME_OVER:
        return Response(serialize_game_state(session_id, engine, user_name))

    # Process user action if alive
    user_player = engine.get_player(user_name)
    if user_player and user_player.is_alive and action_data:
        engine.handle_input(user_player.name, action_data)

    # Process bot actions based on current phase
    alive_players = engine.get_alive_players()
    current_phase = engine.phase_state

    for bot in alive_players:
        if bot.name == user_name:
            continue

        if current_phase == PhaseState.NIGHT:
            if bot.role.abilities:
                target = random.choice(alive_players)
                engine.handle_input(bot.name, {
                    "ability_index": 0,
                    "target": target.name
                })
        elif current_phase == PhaseState.VOTING:
            target = random.choice(alive_players)
            engine.handle_input(bot.name, {
                "action": "vote",
                "target": target.name
            })

    # Transition phase
    if current_phase == PhaseState.NIGHT:
        engine.transition_to(PhaseState.DAY)
        engine.transition_to(PhaseState.VOTING)
    elif current_phase == PhaseState.VOTING:
        engine.transition_to(PhaseState.NIGHT)

    return Response(serialize_game_state(session_id, engine, user_name))
