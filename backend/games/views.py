import logging
import random
import uuid

from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from db.repository import get_repository
from .broadcast import post_write_broadcast
from .engine import PhaseState
from .engine_builder import build_game_engine
from .models import (
    Alignment,
    AbilityTemplate,
    GameAction,
    GameParticipant,
    GameSession,
    GameTemplate,
    PhaseTemplate,
    RoleTemplate,
    WinConditionTemplate,
)
from .serializers import (
    AlignmentSerializer,
    AbilityTemplateSerializer,
    CreateSessionSerializer,
    GameTemplateSerializer,
    JoinSessionSerializer,
    LoginSerializer,
    PhaseTemplateSerializer,
    RoleTemplateSerializer,
    SessionReadySerializer,
    SignupSerializer,
    SubmitSessionActionSerializer,
    UserSerializer,
    WinConditionTemplateSerializer,
)
from .session_runtime import build_started_session_state, record_vote_progress, resolve_voting_round
from .session_state import (
    broadcast_session_event,
    load_session_snapshot,
)


# --- Auth Views ---

@api_view(["POST"])
@permission_classes([AllowAny])
def signup_view(request):
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {"token": token.key, "user": UserSerializer(user).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = authenticate(
        username=serializer.validated_data["username"],
        password=serializer.validated_data["password"],
    )
    if not user:
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(UserSerializer(request.user).data)


class AbilityTemplateViewSet(viewsets.ModelViewSet):
    queryset = AbilityTemplate.objects.all()
    serializer_class = AbilityTemplateSerializer
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            # Clone instead of update
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_obj = serializer.save(is_default=False)
            return Response(self.get_serializer(new_obj).data, status=status.HTTP_201_CREATED)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            # Combine instance data with partial updates
            data = self.get_serializer(instance).data
            data.update(request.data)
            data.pop('id', None)
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            new_obj = serializer.save(is_default=False)
            return Response(self.get_serializer(new_obj).data, status=status.HTTP_201_CREATED)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            return Response({"error": "Cannot delete default abilities"}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class RoleTemplateViewSet(viewsets.ModelViewSet):
    queryset = RoleTemplate.objects.all()
    serializer_class = RoleTemplateSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            # Clone instead of update
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_obj = serializer.save(is_default=False)
            return Response(self.get_serializer(new_obj).data, status=status.HTTP_201_CREATED)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            # Combine instance data with partial updates
            data = self.get_serializer(instance).data
            data.update(request.data)
            data.pop('id', None)
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            new_obj = serializer.save(is_default=False)
            return Response(self.get_serializer(new_obj).data, status=status.HTTP_201_CREATED)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            return Response({"error": "Cannot delete default roles"}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class AlignmentViewSet(viewsets.ModelViewSet):
    queryset = Alignment.objects.all()
    serializer_class = AlignmentSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            return Response({"error": "Cannot delete default alignments"}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class PhaseTemplateViewSet(viewsets.ModelViewSet):
    queryset = PhaseTemplate.objects.all()
    serializer_class = PhaseTemplateSerializer


class WinConditionTemplateViewSet(viewsets.ModelViewSet):
    queryset = WinConditionTemplate.objects.all()
    serializer_class = WinConditionTemplateSerializer


class GameTemplateViewSet(viewsets.ModelViewSet):
    queryset = GameTemplate.objects.all()
    serializer_class = GameTemplateSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return GameTemplate.objects.filter(Q(is_public=True) | Q(creator=user)).distinct()
        return GameTemplate.objects.filter(is_public=True)

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.creator and instance.creator != request.user:
            return Response({"error": "Not the owner"}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.creator and instance.creator != request.user:
            return Response({"error": "Not the owner"}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


# --- Persistent Multiplayer Session Views ---

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_network_session(request):
    """Create a new multiplayer session.
    
    Refactored to use Repository pattern (Phase 5).
    """
    repo = get_repository()
    serializer = CreateSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    template = _get_accessible_template(
        serializer.validated_data["template_id"],
        request.user,
    )
    if template is None:
        return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

    requested_name = serializer.validated_data.get("display_name", "")

    with transaction.atomic():
        session_doc = repo.create_session(template.id, request.user.id)
        session_id = session_doc["_id"]
        
        display_name = _ensure_unique_display_name_via_repo(
            repo,
            session_id,
            requested_name,
            request.user.username,
        )
        repo.create_participant(session_id, request.user.id, display_name, 0)

    post_write_broadcast(session_id, "session.created")

    return Response(
        load_session_snapshot(session_id, viewer_user_id=request.user.id),
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_network_session(request):
    """Join an existing session by join code.
    
    Example of refactored view using the Repository abstraction instead of
    direct ORM calls. See Phase 3 doc for remaining view refactors.
    """
    repo = get_repository()
    serializer = JoinSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    join_code = serializer.validated_data["join_code"]
    requested_name = serializer.validated_data.get("display_name", "")

    # Fetch session document via repository
    session_doc = repo.get_session_by_join_code(join_code)
    if session_doc is None:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    session_id = session_doc["_id"]

    # Check for existing participant
    existing = repo.get_participant_by_session_and_user(session_id, request.user.id)
    if existing:
        # Reconnection case: mark as connected again
        repo.update_participant(existing["_id"], is_connected=True, last_seen_at=timezone.now())
        post_write_broadcast(session_id, "participant.rejoined")
        return Response(load_session_snapshot(session_id, viewer_user_id=request.user.id))

    if session_doc["status"] != GameSession.STATUS_LOBBY:
        return Response(
            {"error": "Session is no longer accepting new players"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Count current participants
    participants = repo.get_participants_for_session(session_id)
    # Template data comes from relational store until full Phase 5+ migration
    template = GameTemplate.objects.get(id=session_doc["template_id"])
    if len(participants) >= template.max_players:
        return Response({"error": "Session is full"}, status=status.HTTP_400_BAD_REQUEST)

    display_name = _ensure_unique_display_name_via_repo(
        repo,
        session_id,
        requested_name,
        request.user.username,
    )
    next_seat = _get_next_seat_order_via_repo(repo, session_id)

    with transaction.atomic():
        participant_doc = repo.create_participant(
            session_id,
            request.user.id,
            display_name,
            next_seat,
        )

    post_write_broadcast(session_id, "participant.joined")

    return Response(
        load_session_snapshot(session_id, viewer_user_id=request.user.id),
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def network_session_snapshot(request, session_id):
    repo = get_repository()
    session_doc = repo.get_session_by_id(session_id)
    if session_doc is None:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    is_host = session_doc["host_user_id"] == request.user.id
    if not is_host and repo.get_participant_by_session_and_user(session_id, request.user.id) is None:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response(load_session_snapshot(session_id, viewer_user_id=request.user.id))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_network_session_ready(request, session_id):
    """Toggle participant ready state.
    
    Refactored to use Repository pattern (Phase 5).
    """
    repo = get_repository()
    serializer = SessionReadySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Check authorization via session + participant
    session_doc = repo.get_session_by_id(session_id)
    if session_doc is None:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    if session_doc["status"] != GameSession.STATUS_LOBBY:
        return Response(
            {"error": "Ready state can only be changed while the session is in the lobby"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    participant_doc = repo.get_participant_by_session_and_user(session_id, request.user.id)
    if participant_doc is None:
        return Response({"error": "Not a session participant"}, status=status.HTTP_403_FORBIDDEN)

    new_ready_state = serializer.validated_data.get("is_ready", not participant_doc["is_ready"])
    repo.update_participant(
        participant_doc["_id"],
        is_ready=new_ready_state,
    )
    post_write_broadcast(session_id, "participant.ready_changed")

    return Response(load_session_snapshot(session_id, viewer_user_id=request.user.id))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_network_session(request, session_id):
    repo = get_repository()
    session_doc = repo.get_session_by_id(session_id)
    if session_doc is None:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    if session_doc["host_user_id"] != request.user.id:
        return Response({"error": "Only the host can start the session"}, status=status.HTTP_403_FORBIDDEN)

    if session_doc["status"] != GameSession.STATUS_LOBBY:
        return Response({"error": "Session has already started"}, status=status.HTTP_400_BAD_REQUEST)

    # Fetch template data (configuration — still in ORM)
    template = GameTemplate.objects.prefetch_related("phases", "win_conditions", "role_slots__role__abilities__ability").get(id=session_doc["template_id"])

    # Get participant docs from repo (no separate ORM participant fetch)
    participant_docs = repo.get_participants_for_session(session_id)

    if len(participant_docs) < template.min_players:
        return Response(
            {"error": f"Need at least {template.min_players} players to start"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(participant_docs) > template.max_players:
        return Response(
            {"error": f"Session exceeds max player count of {template.max_players}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if any(not p["is_ready"] for p in participant_docs):
        return Response(
            {"error": "All participants must be ready before the game can start"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        engine = build_game_engine(
            template,
            [p["display_name"] for p in participant_docs],
        )
        engine.start_game()
        started_state = build_started_session_state(engine, participant_docs)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    players_by_name = {player.name: player for player in engine.players}

    with transaction.atomic():
        # Update each participant with their assigned role
        for participant_doc in participant_docs:
            player = players_by_name.get(participant_doc["display_name"])
            if player is None:
                continue
            repo.update_participant(
                participant_doc["_id"],
                role_name=player.role.name,
                role_alignment=player.role.alignment.value,
                is_alive=player.is_alive,
                is_ready=False,
            )

        # Update session status and state
        repo.update_session(
            session_id,
            status=GameSession.STATUS_IN_PROGRESS,
            current_phase=started_state["phase"],
            turn_number=started_state["turn_number"],
            started_at=timezone.now(),
            state_json=started_state,
        )

    post_write_broadcast(session_id, "session.started")

    return Response(load_session_snapshot(session_id, viewer_user_id=request.user.id))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_network_session_action(request, session_id):
    serializer = SubmitSessionActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    repo = get_repository()
    session_doc = repo.get_session_by_id(session_id)
    if session_doc is None:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    participant_doc = repo.get_participant_by_session_and_user(session_id, request.user.id)
    if participant_doc is None:
        return Response({"error": "Not a session participant"}, status=status.HTTP_403_FORBIDDEN)

    if session_doc["status"] != GameSession.STATUS_IN_PROGRESS:
        return Response(
            {"error": "The session is not currently in progress"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if session_doc["current_phase"] != GameSession.PHASE_VOTING:
        return Response(
            {"error": "Votes can only be submitted during the voting phase"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not participant_doc["is_alive"]:
        return Response(
            {"error": "Eliminated participants cannot vote"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    target_participant_doc = repo.get_participant_by_id(serializer.validated_data["target_participant_id"])
    if target_participant_doc is None or target_participant_doc["session_id"] != session_id:
        return Response({"error": "Vote target not found"}, status=status.HTTP_404_NOT_FOUND)

    if not target_participant_doc["is_alive"]:
        return Response(
            {"error": "You can only vote for living participants"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        # Re-fetch the participant and target inside the transaction with a lock
        # for ORM-based race condition prevention
        participant_doc = repo.get_participant_with_lock(session_id, request.user.id)
        if participant_doc is None or not participant_doc["is_alive"]:
            return Response(
                {"error": "Participant no longer eligible to vote"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_participant_doc = repo.get_participant_by_id(serializer.validated_data["target_participant_id"])
        if target_participant_doc is None or not target_participant_doc["is_alive"]:
            return Response(
                {"error": "Vote target is no longer a valid living participant"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_vote = repo.check_existing_vote(
            session_id,
            participant_doc["_id"],
            session_doc["turn_number"],
        )
        if existing_vote is not None:
            return Response(
                {"error": "You have already locked in your vote for this round"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            repo.create_action(
                session_id,
                participant_doc["_id"],
                turn_number=session_doc["turn_number"],
                phase=GameSession.PHASE_VOTING,
                action_type="VOTE",
                payload={
                    "target_participant_id": target_participant_doc["_id"],
                    "target_display_name": target_participant_doc["display_name"],
                },
            )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        state = dict(session_doc.get("state_json") or {})
        vote_state = dict(state.get("vote_state") or {})
        submitted_participant_ids = list(vote_state.get("submitted_participant_ids") or [])
        if participant_doc["_id"] not in submitted_participant_ids:
            submitted_participant_ids.append(participant_doc["_id"])
        state = record_vote_progress(state, submitted_participant_ids)

        # Count alive participants
        all_participants = repo.get_participants_for_session(session_id)
        alive_participant_count = sum(1 for p in all_participants if p["is_alive"])
        all_votes_submitted = len(submitted_participant_ids) >= alive_participant_count

        broadcast_reason = "vote.submitted"

        if all_votes_submitted:
            # Load win conditions from template config (ORM — template data, not runtime)
            from games.models import WinConditionTemplate
            win_conditions = list(
                WinConditionTemplate.objects
                .filter(game_template_id=session_doc["template_id"])
                .order_by("order")
            )

            next_state, eliminated_participant_id, winner_alignment = resolve_voting_round(
                repo, session_doc, all_participants, win_conditions
            )

            if eliminated_participant_id is not None:
                repo.update_participant(
                    eliminated_participant_id,
                    is_alive=False,
                    eliminated_at=timezone.now(),
                )

            if winner_alignment:
                repo.update_session(
                    session_id,
                    status=GameSession.STATUS_COMPLETED,
                    current_phase=next_state["phase"],
                    turn_number=next_state["turn_number"],
                    state_json=next_state,
                    ended_at=timezone.now(),
                )
            else:
                repo.update_session(
                    session_id,
                    current_phase=next_state["phase"],
                    turn_number=next_state["turn_number"],
                    state_json=next_state,
                )
            broadcast_reason = "vote.resolved"
        else:
            repo.update_session(
                session_id,
                state_json=state,
            )

    post_write_broadcast(session_id, broadcast_reason)

    return Response(load_session_snapshot(session_id, viewer_user_id=request.user.id))


# --- Existing Single-Player Demo Session Views ---

# In-memory store for active demo game sessions
# NOTE: State is NOT persisted - games will be lost on server restart
# This is acceptable for the solo/demo mode but would need Redis/database
# persistence for production deployment with multiple server instances.
# For the multiplayer mode, state IS persisted in GameSession.state_json.
ACTIVE_GAMES = {}


def serialize_game_state(session_id, engine, user_name):
    user_player = engine.get_player(user_name)

    players = []
    for player in engine.players:
        # In the solo demo, roles stay hidden mid-game unless you're viewing your own.
        reveal_role = player.name == user_name or engine.phase_state == PhaseState.GAME_OVER
        players.append(
            {
                "name": player.name,
                "is_alive": player.is_alive,
                "role": player.role.name if reveal_role else "Unknown",
                "alignment": player.role.alignment if reveal_role else "Unknown",
            }
        )

    abilities = []
    if user_player and user_player.is_alive and user_player.role.abilities:
        for index, ability in enumerate(user_player.role.abilities):
            abilities.append({"index": index, "name": ability.name, "phase": ability.phase})

    return {
        "session_id": session_id,
        "phase": engine.phase_state.value,
        "turn": engine.turn_number,
        "players": players,
        "me": {
            "name": user_name,
            "is_alive": user_player.is_alive if user_player else False,
            "role": user_player.role.name if user_player else "Observer",
            "alignment": user_player.role.alignment if user_player else "Unknown",
            "abilities": abilities,
        },
        "logs": [
            {"type": e["type"], "message": e["message"], "turn": e["turn"]}
            for e in engine.events
            if e["visible_to"] == "all" or user_name in e["visible_to"]
        ],
    }


@api_view(["POST"])
def start_game_session(request):
    template_id = request.data.get("template_id")
    user_name = request.data.get("user_name", "You")

    template = _get_accessible_template(template_id, request.user)
    if template is None:
        return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)

    total_slots = sum(slot.count for slot in template.role_slots.all())
    if total_slots < 1:
        return Response({"error": "Template has no roles"}, status=status.HTTP_400_BAD_REQUEST)

    player_names = [user_name] + [f"Bot {index}" for index in range(1, total_slots)]

    engine = build_game_engine(template, player_names)
    engine.start_game()

    session_id = str(uuid.uuid4())
    ACTIVE_GAMES[session_id] = engine

    return Response(serialize_game_state(session_id, engine, user_name))


def _get_bot_target(bot, engine, available_players, ability=None, is_vote=False):
    known_mafia = set()
    known_town = set()

    if bot.role.alignment == "MAFIA":
        for p in engine.players:
            if p.role.alignment == "MAFIA":
                known_mafia.add(p.name)

    for event in engine.events:
        visible = event.get("visible_to")
        if visible == "all" or (isinstance(visible, list) and bot.name in visible):
            if event.get("type") == "investigate":
                msg = event.get("message", "")
                if "investigated" in msg and ":" in msg:
                    try:
                        target_name = msg.split("investigated ")[1].split(":")[0].strip()
                        alignment_str = msg.split(":")[1].strip()
                        if alignment_str == "MAFIA":
                            known_mafia.add(target_name)
                        elif alignment_str == "TOWN":
                            known_town.add(target_name)
                    except (IndexError, ValueError, AttributeError) as e:
                        # Failed to parse investigation result from log message
                        # This is not critical - bot will just lack this intel
                        logging.getLogger(__name__).debug(f"Bot intel parsing failed: {e}")
    
    alive_targets = [p for p in available_players if p.name != bot.name]
    if not alive_targets:
        return bot

    is_hostile = False
    is_helpful = False

    if is_vote:
        is_hostile = True
    elif ability:
        name_lower = ability.name.lower()
        ability_type = type(ability).__name__
        if ability_type in ("KillAbility", "BlockAbility", "TrapAbility", "VoteStealAbility"):
            is_hostile = True
        elif ability_type in ("ProtectAbility", "DoubleVoteAbility"):
            is_helpful = True
        elif "investigate" in name_lower:
            valid = [p for p in alive_targets if p.name not in known_town and p.name not in known_mafia]
            if valid:
                return random.choice(valid)

    if bot.role.alignment == "MAFIA":
        if is_hostile:
            valid = [p for p in alive_targets if p.name not in known_mafia]
            if valid:
                return random.choice(valid)
        elif is_helpful:
            valid = [p for p in available_players if p.name in known_mafia]
            if valid:
                return random.choice(valid)
        else:
            valid = [p for p in alive_targets if p.name not in known_mafia]
            if valid:
                return random.choice(valid)
    else:
        if is_hostile:
            valid = [p for p in alive_targets if p.name in known_mafia]
            if valid:
                return random.choice(valid)
            valid_unknown = [p for p in alive_targets if p.name not in known_town]
            if valid_unknown:
                return random.choice(valid_unknown)
        elif is_helpful:
            valid = [p for p in alive_targets if p.name in known_town]
            if valid:
                return random.choice(valid)
            valid_unknown = [p for p in alive_targets if p.name not in known_mafia]
            if valid_unknown:
                return random.choice(valid_unknown)

    return random.choice(alive_targets)


def _simulate_bots_for_phase(engine):
    alive_players = engine.get_alive_players()
    current_phase = engine.phase_state

    for bot in alive_players:
        if not bot.name.startswith("Bot "):
            continue

        if current_phase == PhaseState.NIGHT:
            night_abilities = [
                (index, ability)
                for index, ability in enumerate(bot.role.abilities)
                if ability.phase == "NIGHT"
            ]
            if night_abilities:
                ability_index, ability = night_abilities[0]
                target = _get_bot_target(bot, engine, alive_players, ability=ability, is_vote=False)
                engine.handle_input(
                    bot.name,
                    {"ability_index": ability_index, "target": target.name},
                )
        elif current_phase == PhaseState.VOTING:
            voting_abilities = [
                (index, ability)
                for index, ability in enumerate(bot.role.abilities)
                if ability.phase == "VOTING"
            ]
            if voting_abilities:
                ability_index, ability = voting_abilities[0]
                target = _get_bot_target(bot, engine, alive_players, ability=ability, is_vote=False)
                engine.handle_input(
                    bot.name,
                    {"ability_index": ability_index, "target": target.name},
                )

            target = _get_bot_target(bot, engine, alive_players, ability=None, is_vote=True)
            engine.handle_input(
                bot.name,
                {"action": "vote", "target": target.name},
            )


@api_view(["POST"])
def game_session_action(request, session_id):
    if session_id not in ACTIVE_GAMES:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    engine = ACTIVE_GAMES[session_id]
    user_name = request.data.get("user_name", "You")
    action_data = request.data.get("action", {})
    current_phase = engine.phase_state

    if current_phase == PhaseState.GAME_OVER:
        return Response(serialize_game_state(session_id, engine, user_name))

    user_player = engine.get_player(user_name)
    user_performed_vote = False

    if user_player and user_player.is_alive:
        if action_data:
            if current_phase == PhaseState.VOTING and action_data.get("action") == "vote":
                user_performed_vote = True
            engine.handle_input(user_player.name, action_data)
        elif action_data is None and current_phase == PhaseState.VOTING:
            user_performed_vote = True

    should_advance = True

    if current_phase == PhaseState.VOTING:
        if action_data and action_data.get("ability_index") is not None and not user_performed_vote:
            should_advance = False

    if should_advance:
        _simulate_bots_for_phase(engine)
        engine.advance_phase()

        while engine.phase_state != PhaseState.GAME_OVER:
            alive_now = engine.get_alive_players()
            human_alive = any(not p.name.startswith("Bot ") for p in alive_now)
            if human_alive:
                break
                
            _simulate_bots_for_phase(engine)
            engine.advance_phase()

    return Response(serialize_game_state(session_id, engine, user_name))


def _get_accessible_template(template_id, user):
    try:
        template = GameTemplate.objects.get(id=template_id)
    except GameTemplate.DoesNotExist:
        return None

    if template.is_public:
        return template

    if user.is_authenticated and template.creator_id == user.id:
        return template

    return None


def _ensure_unique_display_name(session, requested_name, fallback_name):
    base_name = (requested_name or fallback_name or "Player").strip()[:100]
    base_name = base_name or "Player"

    existing_names = set(
        session.participants.values_list("display_name", flat=True)
    )
    if base_name not in existing_names:
        return base_name

    suffix = 2
    while True:
        candidate = f"{base_name[:96]}-{suffix}"
        if candidate not in existing_names:
            return candidate
        suffix += 1


def _get_next_seat_order(session):
    max_value = session.participants.aggregate(max_value=Max("seat_order"))["max_value"]
    return 0 if max_value is None else max_value + 1


def _ensure_unique_display_name_via_repo(repo, session_id, requested_name, fallback_name):
    """Repository-based version of _ensure_unique_display_name for refactored views."""
    base_name = (requested_name or fallback_name or "Player").strip()[:100]
    base_name = base_name or "Player"

    if repo.check_unique_display_name(session_id, base_name):
        return base_name

    suffix = 2
    while True:
        candidate = f"{base_name[:96]}-{suffix}"
        if repo.check_unique_display_name(session_id, candidate):
            return candidate
        suffix += 1


def _get_next_seat_order_via_repo(repo, session_id):
    """Repository-based version of _get_next_seat_order for refactored views."""
    participants = repo.get_participants_for_session(session_id)
    if not participants:
        return 0
    max_seat = max(p["seat_order"] for p in participants)
    return max_seat + 1
